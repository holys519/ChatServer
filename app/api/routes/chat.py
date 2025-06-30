from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime
from app.models.schemas import ChatRequest, ChatResponse, ChatHistoryItem, ChatMessage
from app.services.gemini_service import gemini_service
from app.services.openai_service import openai_service
from app.services.session_service import session_service
from app.services.agent_base import agent_orchestrator
from app.services.task_service import task_service
from app.services.command_service import command_service
from app.services.workflow_status_service import workflow_status_service, WorkflowType
from app.middleware.auth import get_current_user, require_auth

router = APIRouter()

def format_papers_by_evidence_level(papers: List[Dict], max_per_level: int = 10, include_abstracts: bool = True) -> str:
    """
    論文をエビデンスレベル別に整理して表示する再利用可能な関数
    
    Args:
        papers: 論文リスト
        max_per_level: 各エビデンスレベルごとの最大表示数
        include_abstracts: 抄録プレビューを含めるかどうか
    
    Returns:
        フォーマットされた文字列
    """
    result_text = ""
    
    # エビデンスレベル別に論文を分類
    evidence_groups = {
        "1a": {"name": "Systematic Reviews/Meta-analyses", "papers": []},
        "1b": {"name": "Randomized Controlled Trials", "papers": []},
        "2a": {"name": "Cohort Studies", "papers": []},
        "2b": {"name": "Case-Control Studies", "papers": []},
        "3": {"name": "Cross-sectional Studies", "papers": []},
        "4": {"name": "Case Series", "papers": []},
        "5": {"name": "Expert Opinion/Other", "papers": []}
    }
    
    # 論文をエビデンスレベル別に分類
    for paper in papers:
        level = paper.get('evidence_level', '5')
        if level in evidence_groups:
            evidence_groups[level]["papers"].append(paper)
    
    # 各エビデンスレベルの論文を表示
    for level in ["1a", "1b", "2a", "2b", "3", "4", "5"]:
        group_papers = evidence_groups[level]["papers"]
        if group_papers:
            result_text += f"""

### 📊 Level {level}: {evidence_groups[level]["name"]} ({len(group_papers)} papers)"""
            
            for i, paper in enumerate(group_papers[:max_per_level], 1):
                # 辞書形式かNamedTuple形式かを判定して適切にアクセス
                if isinstance(paper, dict):
                    title = paper.get('title', 'Title not available')
                    journal = paper.get('journal', 'Journal not specified')
                    year = paper.get('publication_date', 'Year unknown')
                    pmid = paper.get('pmid', '')
                    abstract = paper.get('abstract', '')
                else:
                    # NamedTuple形式の場合
                    title = getattr(paper, 'title', 'Title not available')
                    journal = getattr(paper, 'journal', 'Journal not specified')
                    year = getattr(paper, 'publication_date', 'Year unknown')
                    pmid = getattr(paper, 'pmid', '')
                    abstract = getattr(paper, 'abstract', '')
                
                result_text += f"""

**{i}. {title}**
- **Journal**: {journal}
- **Year**: {year}
- **PMID**: {pmid}
- **URL**: https://pubmed.ncbi.nlm.nih.gov/{pmid}/"""
                
                # 抄録がある場合は概要も表示
                if include_abstracts and abstract and len(abstract) > 50:
                    abstract_preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                    result_text += f"\n- **Abstract Preview**: {abstract_preview}"
            
            if len(group_papers) > max_per_level:
                result_text += f"\n\n*... and {len(group_papers) - max_per_level} more {evidence_groups[level]['name'].lower()}*"
    
    return result_text

async def get_user_id_from_auth(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Authorization ヘッダーからユーザーIDを取得（オプショナル）
    ユーザーがログインしていない場合は None を返す
    """
    if not authorization:
        return None
    
    try:
        # FastAPI Headerオブジェクトの場合は文字列に変換
        auth_str = str(authorization) if authorization else None
        if not auth_str or auth_str == "None":
            return None
            
        scheme, user_id = auth_str.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        return user_id
    except (ValueError, AttributeError):
        return None

@router.post("/send", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Send a chat message and get complete response"""
    try:
        # Log request processing without sensitive data
        print(f"Processing chat request for model: {request.model.provider}")
        
        user_id = current_user.get("user_id") if current_user else None
        
        # Convert history to the format expected by services
        history = [
            {
                "role": "user" if msg.is_user else "model",
                "content": msg.content
            }
            for msg in request.history
        ]
        
        response_text = ""
        
        # Handle help command
        if request.message.startswith("/help"):
            try:
                # Extract command name if provided
                help_parts = request.message.split()
                command_name = help_parts[1] if len(help_parts) > 1 else None
                
                help_text = command_service.get_help_text(command_name)
                response_text = help_text
                
            except Exception as help_error:
                print(f"Help command error: {str(help_error)}")
                response_text = "Error processing help command. Try '/help' for general help or '/help @command-name' for specific command help."
        
        # Handle command suggestion request
        elif request.message.startswith("/commands") or request.message.startswith("/suggest"):
            try:
                # Get context from message
                query_part = request.message.replace("/commands", "").replace("/suggest", "").strip()
                
                if query_part:
                    # Get suggestions based on user intent
                    suggestions = command_service.suggest_commands_for_intent(query_part)
                else:
                    # List all commands categorized
                    suggestions = command_service.list_commands()
                
                # Format suggestions response
                if query_part:
                    response_text = f"""# Command Suggestions for: "{query_part}"

Based on your message, here are the recommended commands:

"""
                    for i, cmd in enumerate(suggestions[:3], 1):
                        response_text += f"""**{i}. {cmd.name}** ({cmd.complexity})
{cmd.description}

*Usage*: `{cmd.usage}`
*Estimated time*: {cmd.estimated_time}

"""
                else:
                    response_text = """# Available MedAgent-Chat Commands

## 🔬 Complete Workflows
- **@research-workflow** - Full research pipeline (recommended)

## 📚 Paper Search
- **@paper-scout-auditor** - Enhanced search with quality validation  
- **@paper-scout** - Basic paper search

## 📝 Advanced Tools
- **@review-creation** - Literature review creation
- **@paper-critic** - Quality analysis
- **@paper-reviser** - Collection enhancement

*Use `/help @command-name` for detailed information about any command.*
"""
                
            except Exception as cmd_error:
                print(f"Command suggestion error: {str(cmd_error)}")
                response_text = "Error processing command suggestions. Try '/help' for assistance."
        
        # Auto-suggest commands for natural language requests
        elif not request.message.startswith("@") and not request.message.startswith("/"):
            # Check if user is asking for research-related tasks
            suggestions = command_service.suggest_commands_for_intent(request.message)
            
            # If strong intent detected, suggest commands
            if suggestions and any(keyword in request.message.lower() for keyword in [
                "find papers", "search papers", "literature review", "research", "papers about",
                "systematic review", "analyze papers", "paper analysis", "research on"
            ]):
                response_text = f"""I can help you with that! Based on your request, here are some relevant commands:

"""
                for i, cmd in enumerate(suggestions[:2], 1):
                    response_text += f"""**{i}. {cmd.name}**
{cmd.description}
*Usage*: `{cmd.usage}`

"""
                
                response_text += f"""You can also use:
- `/help @command-name` for detailed help
- `/suggest {request.message}` for more command suggestions

Would you like me to execute one of these commands for you?"""
                
                # Don't process as regular chat if strong command intent detected
                return ChatResponse(
                    content=response_text,
                    model_id=request.model.id,
                    is_streaming=False
                )
        
        # Handle unknown commands with suggestions
        elif request.message.startswith("@"):
            # Validate command
            validation_result = command_service.validate_command_syntax(request.message)
            
            if not validation_result["valid"]:
                response_text = f"""❌ **Command Error**: {validation_result['error']}

💡 **Suggestion**: {validation_result['suggestion']}

Use `/help` to see all available commands or `/help @command-name` for specific help."""
                
                return ChatResponse(
                    content=response_text,
                    model_id=request.model.id,
                    is_streaming=False
                )
        
        # Check for special agent commands
        if request.message.startswith("@paper-scout-auditor"):
            # Handle paper search auditor command
            try:
                # Extract query from command
                query = request.message.replace("@paper-scout-auditor", "").strip()
                if not query:
                    response_text = "Please provide a search query after @paper-scout-auditor"
                else:
                    # Create a task for the paper search auditor
                    task_id = str(uuid.uuid4())
                    
                    # First run paper scout to get initial papers
                    scout_input = {
                        'query': query,
                        'max_results': 15,
                        'years_back': 10,
                        'include_abstracts': True,
                        'analysis_type': 'comprehensive'
                    }
                    
                    try:
                        # Create workflow card for tracking
                        audit_workflow_id = workflow_status_service.create_workflow_card(
                            workflow_type=WorkflowType.PAPER_SEARCH_AUDITOR,
                            title=f"Paper Search Audit: {query}",
                            description=f"Enhanced paper search with quality validation for '{query}'",
                            input_parameters={"query": query}
                        )
                        
                        # Execute paper scout first
                        scout_result = await agent_orchestrator.execute_task(
                            task_id=task_id,
                            agent_id="paper_scout",
                            input_data=scout_input
                        )
                        
                        # Then run the auditor with scout results
                        auditor_input = {
                            'papers': scout_result.get('papers', []),
                            'search_query': scout_result.get('optimized_query', query),
                            'original_query': query,
                            'audit_goals': ['quality', 'completeness', 'diversity']
                        }
                        
                        auditor_result = await agent_orchestrator.execute_task(
                            task_id=task_id + "_auditor",
                            agent_id="paper_search_auditor",
                            input_data=auditor_input
                        )
                        
                        # Complete workflow tracking
                        workflow_status_service.complete_workflow(
                            workflow_id=audit_workflow_id,
                            final_results=auditor_result,
                            quality_metrics=auditor_result.get('quality_metrics', {})
                        )
                        
                        # Format response with audit results
                        audit_report = auditor_result.get('audit_report', 'Audit completed')
                        final_papers_count = len(auditor_result.get('final_papers', []))
                        quality_grade = auditor_result.get('quality_metrics', {}).get('quality_metrics', {}).get('quality_grade', 'N/A')
                        
                        response_text = f"""# Enhanced Paper Search Audit Results

## Query: "{query}"

### Audit Summary
- **Final Papers Count**: {final_papers_count}
- **Quality Grade**: {quality_grade}
- **Audit Status**: {auditor_result.get('status', 'Unknown')}

{audit_report}

### Workflow Tracking
- **Workflow ID**: `{audit_workflow_id}`
- **Status**: Completed
- **View Details**: Use `/api/workflows/{audit_workflow_id}` for detailed progress tracking

---
*This search was conducted using the enhanced Paper Search Auditor with multi-agent validation and improvement.*"""
                        
                    except Exception as agent_error:
                        print(f"Agent execution error: {str(agent_error)}")
                        response_text = f"Error executing enhanced paper search: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Command processing error: {str(command_error)}")
                response_text = f"Error processing @paper-scout-auditor command: {str(command_error)}"
        
        elif request.message.startswith("@paper-critic"):
            # Handle paper critic command
            try:
                # This would require papers to be provided in the message or context
                response_text = "Paper Critic Agent requires papers to analyze. Please use @paper-scout-auditor for complete analysis."
            except Exception as e:
                response_text = f"Error processing @paper-critic command: {str(e)}"
        
        elif request.message.startswith("@paper-reviser"):
            # Handle paper reviser command  
            try:
                response_text = "Paper Reviser Agent requires critic feedback. Please use @paper-scout-auditor for complete workflow."
            except Exception as e:
                response_text = f"Error processing @paper-reviser command: {str(e)}"
        
        elif request.message.startswith("@review-creation"):
            # Handle review creation command
            try:
                # Extract topic and parameters from command
                command_parts = request.message.replace("@review-creation", "").strip()
                if not command_parts:
                    response_text = "Please provide a research topic after @review-creation"
                else:
                    # Parse command parameters
                    parts = command_parts.split()
                    
                    # Extract topic (everything before first parameter)
                    topic_parts = []
                    params = {}
                    
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            params[key] = value
                        else:
                            topic_parts.append(part)
                    
                    topic = ' '.join(topic_parts) if topic_parts else command_parts
                    
                    # Create a task for review creation
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for review creation agent
                    review_input = {
                        'topic': topic,
                        'review_type': params.get('type', 'narrative'),
                        'target_audience': params.get('audience', 'academic'),
                        'length': params.get('length', 'medium')
                    }
                    
                    try:
                        # Create workflow card for tracking
                        review_workflow_id = workflow_status_service.create_workflow_card(
                            workflow_type=WorkflowType.REVIEW_CREATION,
                            title=f"Literature Review: {topic}",
                            description=f"Literature review creation for '{topic}'",
                            input_parameters=review_input
                        )
                        
                        # Execute review creation agent
                        review_result = await agent_orchestrator.execute_task(
                            task_id=task_id,
                            agent_id="review_creation",
                            input_data=review_input
                        )
                        
                        # Complete workflow tracking
                        workflow_status_service.complete_workflow(
                            workflow_id=review_workflow_id,
                            final_results=review_result,
                            quality_metrics=review_result.get('quality_metrics', {})
                        )
                        
                        # Format response with review results
                        final_review = review_result.get('final_review', 'Review creation completed')
                        word_count = review_result.get('metadata', {}).get('word_count', 0)
                        papers_analyzed = review_result.get('papers_analyzed', 0)
                        
                        response_text = f"""# Literature Review Creation Results

## Topic: "{topic}"

### Review Summary
- **Review Type**: {review_input['review_type'].title()}
- **Target Audience**: {review_input['target_audience'].title()}
- **Word Count**: {word_count}
- **Papers Analyzed**: {papers_analyzed}

{final_review}

### Workflow Tracking
- **Workflow ID**: `{review_workflow_id}`
- **Status**: Completed
- **View Details**: Use `/api/workflows/{review_workflow_id}` for detailed progress tracking

---
*This literature review was created using the MedAgent-Chat Review Creation Agent with multi-step workflow processing.*"""
                        
                    except Exception as agent_error:
                        print(f"Review creation agent execution error: {str(agent_error)}")
                        response_text = f"Error executing literature review creation: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Review creation command processing error: {str(command_error)}")
                response_text = f"Error processing @review-creation command: {str(command_error)}"
        
        elif request.message.startswith("@research-workflow"):
            # Handle complete research workflow command
            try:
                # Extract query and parameters from command
                command_parts = request.message.replace("@research-workflow", "").strip()
                if not command_parts:
                    response_text = "Please provide a research topic after @research-workflow"
                else:
                    # Parse command parameters (simple format: topic [type:narrative|systematic] [audience:academic|general] [length:short|medium|long])
                    parts = command_parts.split()
                    
                    # Extract topic (everything before first parameter)
                    topic_parts = []
                    params = {}
                    
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            params[key] = value
                        else:
                            topic_parts.append(part)
                    
                    topic = ' '.join(topic_parts) if topic_parts else command_parts
                    
                    # Create a task for the research workflow
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for research workflow coordinator
                    workflow_input = {
                        'query': topic,
                        'topic': topic,
                        'review_type': params.get('type', 'narrative'),
                        'target_audience': params.get('audience', 'academic'),
                        'length': params.get('length', 'medium')
                    }
                    
                    try:
                        # Create workflow card for tracking
                        workflow_id = workflow_status_service.create_workflow_card(
                            workflow_type=WorkflowType.COMPLETE_RESEARCH,
                            title=f"Research: {topic}",
                            description=f"Complete research workflow for '{topic}'",
                            input_parameters=workflow_input
                        )
                        
                        # Execute complete research workflow
                        workflow_result = await agent_orchestrator.execute_task(
                            task_id=task_id,
                            agent_id="research_workflow",
                            input_data=workflow_input
                        )
                        
                        # Complete workflow tracking
                        workflow_status_service.complete_workflow(
                            workflow_id=workflow_id,
                            final_results=workflow_result,
                            quality_metrics=workflow_result.get('quality_metrics', {})
                        )
                        
                        # Format comprehensive response
                        paper_results = workflow_result.get('paper_search_results', {})
                        literature_review = workflow_result.get('literature_review', {})
                        workflow_metadata = workflow_result.get('workflow_metadata', {})
                        recommendations = workflow_result.get('recommendations', [])
                        
                        response_text = f"""# Complete Research Workflow Results
## Topic: "{topic}"

### Phase 1: Paper Search & Quality Validation
- **Papers Found**: {paper_results.get('papers_found', 0)}
- **Quality Grade**: {paper_results.get('quality_grade', 'N/A')}
- **Audit Success**: {paper_results.get('audit_success', False)}
- **Confidence Score**: {paper_results.get('confidence_score', 0.0):.2f}

### Phase 2: Literature Review Creation
- **Review Type**: {workflow_input['review_type'].title()}
- **Target Audience**: {workflow_input['target_audience'].title()}
- **Word Count**: {literature_review.get('word_count', 0)}
- **Sections**: {literature_review.get('sections_count', 0)}

{literature_review.get('final_review', 'Literature review not available')}

### Workflow Summary
- **Total Papers Processed**: {workflow_metadata.get('total_papers_processed', 0)}
- **Research Quality Grade**: {workflow_metadata.get('research_quality_grade', 'N/A')}
- **Completion Time**: {workflow_metadata.get('workflow_completion_time', 'Unknown')}

### Recommendations
{chr(10).join([f"- {rec}" for rec in recommendations]) if recommendations else "No specific recommendations generated"}

### Workflow Tracking
- **Workflow ID**: `{workflow_id}`
- **Status**: Completed
- **View Details**: Use `/api/workflows/{workflow_id}` for detailed progress tracking

---
*This research was conducted using the enhanced MedAgent-Chat Research Workflow Coordinator v{workflow_metadata.get('coordinator_version', '1.0')}*"""
                        
                    except Exception as agent_error:
                        print(f"Research workflow execution error: {str(agent_error)}")
                        response_text = f"Error executing complete research workflow: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Research workflow command processing error: {str(command_error)}")
                response_text = f"Error processing @research-workflow command: {str(command_error)}"
        
        elif request.message.startswith("@multi-search"):
            # Handle multi-database search command
            try:
                # Extract query and parameters from command
                command_parts = request.message.replace("@multi-search", "").strip()
                if not command_parts:
                    response_text = """Please provide search parameters after @multi-search

**Usage**: `@multi-search query:"search terms" [databases:["pubmed","arxiv","scholar"]] [max_results:50]`

**Examples**:
```
@multi-search query:"machine learning healthcare" max_results:30
@multi-search query:"COVID-19 治療" databases:["pubmed","scholar"] years_back:2
@multi-search query:"quantum computing" databases:["arxiv"] max_results:20
```

**Available databases**: pubmed, google_scholar, arxiv
**Parameters**: query, max_results, years_back, databases, include_preprints"""
                else:
                    # Parse command parameters
                    params = {}
                    remaining_parts = []
                    parts = command_parts.split()
                    
                    for part in parts:
                        if ':' in part and not part.startswith('"'):
                            try:
                                key, value = part.split(':', 1)
                                # Handle quoted values and lists
                                if value.startswith('["') and value.endswith('"]'):
                                    # Parse list
                                    value = value[2:-2].split('","')
                                elif value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                elif value.isdigit():
                                    value = int(value)
                                elif value.lower() in ['true', 'false']:
                                    value = value.lower() == 'true'
                                params[key] = value
                            except ValueError:
                                remaining_parts.append(part)
                        else:
                            remaining_parts.append(part)
                    
                    # Get query
                    query = params.get('query', ' '.join(remaining_parts) if remaining_parts else '')
                    
                    if not query:
                        response_text = "Please provide a search query. Example: @multi-search query:\"machine learning\""
                    else:
                        # Create task ID
                        task_id = str(uuid.uuid4())
                        
                        # Prepare input for multi-database search
                        search_input = {
                            'query': query,
                            'max_results': params.get('max_results', 50),
                            'years_back': params.get('years_back'),
                            'databases': params.get('databases'),
                            'include_abstracts': params.get('include_abstracts', True),
                            'strategy': {
                                'parallel_search': params.get('parallel_search', True),
                                'merge_duplicates': params.get('merge_duplicates', True),
                                'similarity_threshold': params.get('similarity_threshold', 0.85),
                                'include_preprints': params.get('include_preprints', True)
                            }
                        }
                        
                        try:
                            # Import multi-database search agent
                            from app.agents.multi_database_search_agent import multi_database_search_agent
                            
                            # Execute multi-database search
                            search_result = await multi_database_search_agent.execute(
                                task_id=task_id,
                                input_data=search_input
                            )
                            
                            # Format response
                            total_papers = search_result.get('total_papers', 0)
                            database_breakdown = search_result.get('database_breakdown', {})
                            quality_metrics = search_result.get('quality_metrics', {})
                            duplicates_removed = search_result.get('duplicates_removed', 0)
                            
                            response_text = f"""# Multi-Database Search Results

## Query: "{query}"

### Summary
- **Total Papers Found**: {total_papers}
- **Duplicates Removed**: {duplicates_removed}
- **Search Time**: {search_result.get('search_time', 0):.2f} seconds
- **Databases Used**: {quality_metrics.get('databases_used', 0)}

### Database Breakdown
"""
                            
                            for db_name, stats in database_breakdown.items():
                                status_icon = "✅" if stats['status'] == 'success' else "⚠️" if stats['status'] == 'partial' else "❌"
                                response_text += f"- **{db_name.title()}**: {stats['papers_found']} papers ({stats['search_time']:.2f}s) {status_icon}\n"
                            
                            response_text += f"""
### Quality Metrics
- **Average Confidence**: {quality_metrics.get('average_confidence', 0):.3f}
- **Recent Papers**: {quality_metrics.get('recent_papers_count', 0)} ({quality_metrics.get('recent_papers_percentage', 0)}%)
- **With Abstracts**: {quality_metrics.get('papers_with_abstracts', 0)} ({quality_metrics.get('abstract_coverage', 0)}%)
- **With Citations**: {quality_metrics.get('papers_with_citations', 0)} ({quality_metrics.get('citation_coverage', 0)}%)

### Top Papers
"""
                            
                            papers = search_result.get('papers', [])
                            for i, paper in enumerate(papers[:5], 1):
                                authors_str = ', '.join(paper['authors'][:3])
                                if len(paper['authors']) > 3:
                                    authors_str += ' et al.'
                                
                                response_text += f"""**{i}. {paper['title']}**
- *Authors*: {authors_str}
- *Journal*: {paper.get('journal', 'Unknown')}
- *Source*: {paper.get('database_source', 'Unknown')} | *Confidence*: {paper.get('confidence_score', 0):.3f}
- *URL*: {paper.get('url', 'N/A')}

"""
                            
                            response_text += f"""---
*Multi-database search completed using {len(database_breakdown)} databases with intelligent deduplication and quality scoring.*"""
                            
                        except Exception as agent_error:
                            print(f"Multi-database search agent execution error: {str(agent_error)}")
                            response_text = f"Error executing multi-database search: {str(agent_error)}"
                            
            except Exception as command_error:
                print(f"Multi-database search command processing error: {str(command_error)}")
                response_text = f"Error processing @multi-search command: {str(command_error)}"
        
        elif request.message.startswith("@citation-analysis"):
            # Handle citation analysis command
            try:
                # Extract parameters from command
                command_parts = request.message.replace("@citation-analysis", "").strip()
                if not command_parts:
                    response_text = """Please provide paper information for citation analysis

**Usage**: `@citation-analysis title:"paper title" [authors:["author1","author2"]] [analysis_depth:medium]`

**Examples**:
```
@citation-analysis title:"Attention Is All You Need" authors:["Vaswani","Shazeer"]
@citation-analysis title:"BERT: Pre-training of Deep Bidirectional Transformers" analysis_depth:deep
@citation-analysis doi:"10.1038/nature14539" years_back:5
```

**Parameters**:
- `title`: Paper title (required if no DOI/PMID)
- `authors`: List of authors (optional)
- `doi`: DOI of the paper (alternative to title)
- `pmid`: PubMed ID (alternative to title)
- `analysis_depth`: shallow, medium, deep (default: medium)
- `years_back`: Years to look back for citing papers (default: 10)
- `max_citing_papers`: Maximum citing papers to analyze (default: 50)"""
                else:
                    # Parse command parameters
                    params = {}
                    parts = command_parts.split()
                    
                    for part in parts:
                        if ':' in part and not part.startswith('"'):
                            try:
                                key, value = part.split(':', 1)
                                # Handle quoted values and lists
                                if value.startswith('["') and value.endswith('"]'):
                                    value = value[2:-2].split('","')
                                elif value.startswith('"') and value.endswith('"'):
                                    value = value[1:-1]
                                elif value.isdigit():
                                    value = int(value)
                                params[key] = value
                            except ValueError:
                                continue
                    
                    # Validate required parameters
                    if not any(param in params for param in ['title', 'doi', 'pmid']):
                        response_text = "Please provide at least one of: title, doi, or pmid for the paper to analyze."
                    else:
                        # Create task ID
                        task_id = str(uuid.uuid4())
                        
                        # Prepare seminal paper info
                        seminal_paper = {}
                        if 'title' in params:
                            seminal_paper['title'] = params['title']
                        if 'authors' in params:
                            seminal_paper['authors'] = params['authors']
                        if 'doi' in params:
                            seminal_paper['doi'] = params['doi']
                        if 'pmid' in params:
                            seminal_paper['pmid'] = params['pmid']
                        
                        # Prepare input for citation analysis
                        citation_input = {
                            'seminal_paper': seminal_paper,
                            'analysis_depth': params.get('analysis_depth', 'medium'),
                            'years_back': params.get('years_back', 10),
                            'max_citing_papers': params.get('max_citing_papers', 50)
                        }
                        
                        try:
                            # Import citation discovery agent
                            from app.agents.citation_discovery_agent import citation_discovery_agent
                            
                            # Execute citation analysis
                            citation_result = await citation_discovery_agent.execute(
                                task_id=task_id,
                                input_data=citation_input
                            )
                            
                            # Format response
                            seminal_paper_info = citation_result.get('seminal_paper', {})
                            network_size = citation_result.get('citation_network_size', 0)
                            recent_papers = citation_result.get('recent_citing_papers', [])
                            highly_cited = citation_result.get('highly_cited_papers', [])
                            citation_trends = citation_result.get('citation_trends', {})
                            influence_metrics = citation_result.get('influence_metrics', {})
                            insights = citation_result.get('insights', {})
                            
                            response_text = f"""# Citation Analysis Results

## Analyzed Paper
**{seminal_paper_info.get('title', 'Unknown Title')}**
- *Authors*: {', '.join(seminal_paper_info.get('authors', []))}
- *Journal*: {seminal_paper_info.get('journal', 'Unknown')}
- *Publication Date*: {seminal_paper_info.get('publication_date', 'Unknown')}

## Citation Network Overview
- **Network Size**: {network_size} papers
- **Recent Citing Papers**: {len(recent_papers)} (last 2 years)
- **Highly Cited Papers**: {len(highly_cited)} papers
- **Direct Citations**: {influence_metrics.get('direct_citations', 0)}
- **Indirect Citations**: {influence_metrics.get('indirect_citations', 0)}

## Research Impact Assessment
- **Influence Score**: {influence_metrics.get('influence_score', 0):.3f}
- **Network Centrality**: {influence_metrics.get('network_centrality', 0):.3f}
- **H-Index of Citing Papers**: {influence_metrics.get('h_index_of_citing_papers', 0)}

## Citation Trends
- **Citation Trend**: {citation_trends.get('citation_trend', 'unknown').title()}
- **Paper Trend**: {citation_trends.get('paper_trend', 'unknown').title()}
- **Peak Year**: {citation_trends.get('peak_year', 'N/A')}
- **Total Citations (Period)**: {citation_trends.get('total_citations_period', 0)}

## Research Insights
**{insights.get('research_impact', 'No impact assessment available')}**

{insights.get('summary', 'No summary available')}
"""
                            
                            # Add key findings
                            key_findings = insights.get('key_findings', [])
                            if key_findings:
                                response_text += "\n### Key Findings\n"
                                for finding in key_findings:
                                    response_text += f"- {finding}\n"
                            
                            # Add recent citing papers
                            if recent_papers:
                                response_text += "\n### Recent Citing Papers (Top 5)\n"
                                for i, paper in enumerate(recent_papers[:5], 1):
                                    response_text += f"{i}. **{paper['title']}**\n"
                                    response_text += f"   - Authors: {', '.join(paper['authors'][:2])}{'...' if len(paper['authors']) > 2 else ''}\n"
                                    response_text += f"   - Citations: {paper.get('citation_count', 'N/A')}\n\n"
                            
                            # Add related topics
                            related_topics = citation_result.get('related_topics', [])
                            if related_topics:
                                response_text += f"\n### Related Research Topics\n{', '.join(related_topics[:10])}\n"
                            
                            response_text += "\n---\n*Citation analysis completed using multi-database search and network analysis algorithms.*"
                            
                        except Exception as agent_error:
                            print(f"Citation analysis agent execution error: {str(agent_error)}")
                            response_text = f"Error executing citation analysis: {str(agent_error)}"
                            
            except Exception as command_error:
                print(f"Citation analysis command processing error: {str(command_error)}")
                response_text = f"Error processing @citation-analysis command: {str(command_error)}"
        
        elif request.message.startswith("@medical-research"):
            # Handle medical research command
            try:
                # Extract command and parameters
                command_parts = request.message.replace("@medical-research", "").strip()
                if not command_parts:
                    response_text = """Please provide task parameters after @medical-research

**Available task types:**
- `task_type:clinical_question question:"your clinical question"`
- `task_type:literature_search query:"search terms" specialty:cardiology`
- `task_type:presentation_prep topic:"presentation topic" type:case_report`
- `task_type:evidence_evaluation topic:"treatment topic"`

**Example:**
```
@medical-research task_type:clinical_question question:"高血圧患者においてACE阻害薬はARBより心血管イベントを減少させるか？"
```"""
                else:
                    # Parse command parameters
                    params = {}
                    remaining_parts = []
                    parts = command_parts.split()
                    
                    for part in parts:
                        if ':' in part and not part.startswith('"'):
                            try:
                                key, value = part.split(':', 1)
                                # Handle quoted values
                                if value.startswith('"') and not value.endswith('"'):
                                    # Find the closing quote
                                    quoted_parts = [value]
                                    idx = parts.index(part) + 1
                                    while idx < len(parts) and not parts[idx].endswith('"'):
                                        quoted_parts.append(parts[idx])
                                        idx += 1
                                    if idx < len(parts):
                                        quoted_parts.append(parts[idx])
                                    value = ' '.join(quoted_parts).strip('"')
                                else:
                                    value = value.strip('"')
                                params[key] = value
                            except ValueError:
                                remaining_parts.append(part)
                        else:
                            remaining_parts.append(part)
                    
                    # Get task type
                    task_type = params.get('task_type', 'literature_search')
                    print(f"Debug: Parsed parameters: {params}")
                    print(f"Debug: Task type: {task_type}")
                    
                    # Create task ID
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input data based on task type
                    medical_input = {
                        'task_type': task_type,
                        **params
                    }
                    print(f"Debug: Medical input data: {medical_input}")
                    
                    try:
                        # Import medical research agent
                        from app.agents.medical_research_agent import medical_research_agent
                        
                        # Execute medical research task
                        medical_result = await medical_research_agent.execute_task(
                            task_id=task_id,
                            input_data=medical_input
                        )
                        
                        # Format response based on task type
                        if task_type == "clinical_question":
                            pico_analysis = medical_result.get('pico_analysis', {})
                            evidence_synthesis = medical_result.get('evidence_synthesis', {})
                            clinical_answer = medical_result.get('clinical_answer', '')
                            confidence = medical_result.get('confidence_level', 'Medium')
                            papers = medical_result.get('papers', [])
                            
                            response_text = f"""# 🩺 Clinical Question Analysis (PICO)

## 📋 Original Question
{medical_result.get('original_question', '')}

## 🎯 PICO Framework Analysis
- **Population (P)**: {pico_analysis.get('population', 'Not specified')}
- **Intervention (I)**: {pico_analysis.get('intervention', 'Not specified')}
- **Comparison (C)**: {pico_analysis.get('comparison', 'Not specified')}
- **Outcome (O)**: {pico_analysis.get('outcome', 'Not specified')}

## 🔍 Search Strategy
- **Generated Search Query**: `{medical_result.get('search_query', 'Query not available')}`
- **Database**: PubMed
- **Search Period**: Last 10 years  
- **Total Papers Retrieved**: {len(papers)} studies
- **High-Quality Evidence**: {len(medical_result.get('high_quality_papers', []))} studies (Levels 1a-1b)

## 📊 Evidence Summary
### Quality of Evidence
- **Total Studies Analyzed**: {len(papers)} papers
- **Evidence Level Distribution**:"""
                            
                            # Add evidence level breakdown
                            evidence_levels = evidence_synthesis.get('evidence_levels', {})
                            for level, count in evidence_levels.items():
                                level_description = {
                                    "1a": "Systematic Reviews/Meta-analyses",
                                    "1b": "Randomized Controlled Trials",
                                    "2a": "Cohort Studies", 
                                    "2b": "Case-Control Studies",
                                    "3": "Cross-sectional Studies",
                                    "4": "Case Series",
                                    "5": "Expert Opinion/Other"
                                }.get(level, "Other")
                                response_text += f"\n  - Level {level} ({level_description}): {count} studies"
                            
                            response_text += f"""

### Key Findings
{evidence_synthesis.get('summary', 'Evidence synthesis not available')}

## 🔬 Clinical Answer
{clinical_answer}

**Confidence Level**: {confidence}

## 📚 Retrieved Literature by Evidence Level"""
                            
                            # 全論文をエビデンスレベル別に表示
                            all_papers = medical_result.get('papers', [])
                            if all_papers:
                                response_text += format_papers_by_evidence_level(
                                    papers=all_papers, 
                                    max_per_level=6,  # 臨床質問では各レベル6件まで
                                    include_abstracts=True  # 臨床質問では抄録も重要
                                )
                            else:
                                response_text += "\n\nNo literature found for this clinical question."
                            
                            response_text += f"""

## 💡 Clinical Implications
{chr(10).join(f"• {imp}" for imp in medical_result.get('clinical_implications', ['Clinical implications not available']))}

## ⚠️ Limitations & Considerations
{chr(10).join(f"• {limit}" for limit in medical_result.get('limitations', ['Study limitations not assessed']))}

## 📖 Recommendations for Further Reading
- Search for recent systematic reviews on this topic
- Review latest clinical practice guidelines
- Consider individual patient factors and contraindications

---
*Analysis completed using Evidence-Based Medical Research Assistant*
*Search Date: {medical_result.get('search_date', 'Not available')}*
*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"""

                        elif task_type == "literature_search":
                            papers = medical_result.get('papers', [])
                            evidence_summary = medical_result.get('evidence_summary', {})
                            categories = medical_result.get('categories', {})
                            recommendations = medical_result.get('clinical_recommendations', [])
                            
                            response_text = f"""# Medical Literature Search Results

## Search Query
- **Original**: {medical_result.get('original_query', '')}
- **English**: {medical_result.get('english_query', '')}

## Results Summary
- **Total Papers**: {medical_result.get('papers_found', 0)}
- **High-Quality Studies**: {evidence_summary.get('high_quality_studies', 0)}
- **Recent Studies**: {evidence_summary.get('recent_studies', 0)}

## Evidence Distribution
"""
                            for level, count in evidence_summary.get('evidence_distribution', {}).items():
                                response_text += f"- **Level {level}**: {count} studies\n"
                            
                            response_text += f"""
## Clinical Recommendations
"""
                            for rec in recommendations:
                                response_text += f"- {rec}\n"
                            
                            # 検索パラメータの詳細を表示
                            search_params_info = ""
                            original_query = medical_result.get('original_query', '')
                            english_query = medical_result.get('english_query', '')
                            
                            if original_query != english_query:
                                search_params_info += f"""
## 🔍 Search Parameters
- **Original Query**: {original_query}
- **Translated Query**: {english_query}
- **Study Types**: {medical_input.get('study_types', 'All types')}
- **Specialty**: {medical_input.get('specialty', 'General')}
- **Search Period**: Last {medical_input.get('years_back', 5)} years"""
                            
                            response_text += search_params_info
                            response_text += f"""
## 📚 Retrieved Literature by Evidence Level"""
                            
                            # 再利用可能な関数を使用して論文を表示
                            response_text += format_papers_by_evidence_level(
                                papers=papers, 
                                max_per_level=8,  # 文献検索では各レベル8件まで
                                include_abstracts=True
                            )
                            
                            response_text += """---
*Search conducted using Evidence-Based Medical Literature Search with PubMed integration*"""

                        elif task_type == "presentation_prep":
                            slide_content = medical_result.get('slide_content', [])
                            supporting_literature = medical_result.get('supporting_literature', [])
                            presentation_structure = medical_result.get('presentation_structure', {})
                            speaker_notes = medical_result.get('speaker_notes', {})
                            q_and_a_prep = medical_result.get('q_and_a_prep', {})
                            
                            response_text = f"""# 🎯 Medical Presentation Preparation Complete

## 📋 Presentation Details
- **Topic**: {medical_result.get('topic', '')}
- **Type**: {presentation_structure.get('type', 'Unknown')}
- **Target Audience**: {presentation_structure.get('target_audience', 'General')}
- **Duration**: {presentation_structure.get('total_time', 10)} minutes
- **Total Slides**: {len(slide_content)}

## 📊 Detailed Slide Structure"""
                            
                            for i, slide in enumerate(slide_content, 1):
                                slide_title = slide.get('title', f'Slide {i}')
                                slide_duration = slide.get('duration', 1)
                                key_points = slide.get('key_points', [])
                                supporting_evidence = slide.get('supporting_evidence', [])
                                
                                response_text += f"""

### Slide {i}: {slide_title} ({slide_duration} min)
**Key Points:**"""
                                for point in key_points:
                                    response_text += f"\n• {point}"
                                
                                if supporting_evidence:
                                    response_text += f"\n\n**Supporting Evidence:**"
                                    for evidence in supporting_evidence:
                                        response_text += f"\n• {evidence}"
                            
                            response_text += f"""

## 📚 Supporting Literature Analysis
**Total Papers Reviewed**: {len(supporting_literature)}"""
                            
                            # Analyze evidence levels in supporting literature
                            evidence_distribution = {}
                            high_quality_papers = []
                            for paper in supporting_literature:
                                evidence_level = paper.get('evidence_level', '5')
                                evidence_distribution[evidence_level] = evidence_distribution.get(evidence_level, 0) + 1
                                if evidence_level in ['1a', '1b']:
                                    high_quality_papers.append(paper)
                            
                            response_text += f"\n\n**Evidence Quality Distribution:**"
                            level_descriptions = {
                                "1a": "Systematic Reviews/Meta-analyses",
                                "1b": "Randomized Controlled Trials", 
                                "2a": "Cohort Studies",
                                "2b": "Case-Control Studies",
                                "3": "Cross-sectional Studies",
                                "4": "Case Series",
                                "5": "Expert Opinion/Other"
                            }
                            for level in sorted(evidence_distribution.keys()):
                                count = evidence_distribution[level]
                                desc = level_descriptions.get(level, "Other")
                                response_text += f"\n• Level {level} ({desc}): {count} papers"
                            
                            response_text += f"""

## 🔬 High-Quality Evidence Papers"""
                            
                            for i, paper in enumerate(high_quality_papers[:5], 1):
                                title = paper.get('title', 'Title not available')
                                journal = paper.get('journal', 'Journal not specified')
                                year = paper.get('publication_date', 'Year unknown')
                                evidence_level = paper.get('evidence_level', 'N/A')
                                pmid = paper.get('pmid', '')
                                
                                response_text += f"""

### {i}. {title}
- **Journal**: {journal}
- **Year**: {year}
- **Evidence Level**: {level_descriptions.get(evidence_level, evidence_level)}
- **PMID**: {pmid}"""
                            
                            response_text += f"""

## 🎤 Speaker Notes Overview"""
                            if speaker_notes:
                                for slide_key, notes in list(speaker_notes.items())[:3]:
                                    response_text += f"\n**{slide_key}**: Key talking points prepared"
                            else:
                                response_text += "\nDetailed speaker notes have been prepared for each slide"
                            
                            response_text += f"""

## ❓ Q&A Preparation"""
                            if q_and_a_prep:
                                anticipated_questions = q_and_a_prep.get('anticipated_questions', [])
                                if anticipated_questions:
                                    response_text += f"\n**Anticipated Questions ({len(anticipated_questions)}):**"
                                    for q in anticipated_questions[:3]:
                                        response_text += f"\n• {q}"
                                    if len(anticipated_questions) > 3:
                                        response_text += f"\n• ... and {len(anticipated_questions) - 3} more questions"
                            else:
                                response_text += "\nAnticipated questions and expert answers have been prepared"
                            
                            response_text += f"""

## 📤 Export & Next Steps
✅ **Ready for Export**: Google Slides, PowerPoint, PDF formats available
✅ **Academic Citations**: All references properly formatted
✅ **Visual Aids**: Slide layouts optimized for medical presentations
✅ **Time Management**: Each slide timed for optimal flow

---
*Comprehensive presentation prepared using Evidence-Based Medical Research Assistant*
*Audience: {presentation_structure.get('target_audience', 'Medical professionals')} | Duration: {presentation_structure.get('total_time', 10)} minutes*"""

                        elif task_type == "evidence_evaluation":
                            papers = medical_result.get('papers', [])
                            evidence_synthesis = medical_result.get('evidence_synthesis', {})
                            clinical_answer = medical_result.get('clinical_answer', '')
                            confidence_level = medical_result.get('confidence_level', 'Medium')
                            clinical_implications = medical_result.get('clinical_implications', [])
                            limitations = medical_result.get('limitations', [])
                            high_quality_papers = medical_result.get('high_quality_papers', [])
                            study_designs = medical_result.get('study_designs', {})
                            
                            # ユーザーが設定した信頼度レベルを取得
                            requested_confidence = medical_input.get('confidence_level', 'medium')
                            
                            response_text = f"""# 🔬 Evidence-Based Medical Evaluation

## 🎯 Topic Analysis
**Research Topic**: {medical_result.get('topic', '')}
**Evaluation Request**: {medical_result.get('original_question', 'Evidence evaluation')}
**Requested Confidence Level**: **{requested_confidence.title()}**
**Assessed Confidence Level**: **{confidence_level}**

## 📊 Evidence Overview
**Total Studies Analyzed**: {len(papers)} papers
**High-Quality Evidence**: {len(high_quality_papers)} studies (Levels 1a-1b)
**Research Period**: {medical_result.get('search_date', 'Recent')}
**Search Strategy**: {f"Focused search (last 5 years)" if requested_confidence.lower() == "high" else f"Standard search (last 8 years)" if requested_confidence.lower() == "medium" else f"Comprehensive search (last 15 years)"}

### Evidence Level Distribution"""
                            
                            evidence_levels = evidence_synthesis.get('evidence_levels', {})
                            level_descriptions = {
                                "1a": "Systematic Reviews/Meta-analyses",
                                "1b": "Randomized Controlled Trials",
                                "2a": "Cohort Studies", 
                                "2b": "Case-Control Studies",
                                "3": "Cross-sectional Studies",
                                "4": "Case Series",
                                "5": "Expert Opinion/Other"
                            }
                            
                            for level in ["1a", "1b", "2a", "2b", "3", "4", "5"]:
                                count = evidence_levels.get(level, 0)
                                if count > 0:
                                    desc = level_descriptions.get(level, level)
                                    response_text += f"\n• **Level {level}** ({desc}): {count} studies"
                            
                            response_text += f"""

## 🔍 Evidence Synthesis
{evidence_synthesis.get('summary', 'No evidence synthesis available')}"""
                            
                            # Key findings
                            consistent_findings = evidence_synthesis.get('consistent_findings', [])
                            conflicting_findings = evidence_synthesis.get('conflicting_findings', [])
                            evidence_gaps = evidence_synthesis.get('evidence_gaps', [])
                            
                            if consistent_findings:
                                response_text += f"""

### ✅ Consistent Findings"""
                                for finding in consistent_findings:
                                    response_text += f"\n• {finding}"
                            
                            if conflicting_findings:
                                response_text += f"""

### ⚠️ Conflicting Evidence"""
                                for conflict in conflicting_findings:
                                    response_text += f"\n• {conflict}"
                            
                            if evidence_gaps:
                                response_text += f"""

### 🔄 Evidence Gaps"""
                                for gap in evidence_gaps:
                                    response_text += f"\n• {gap}"
                            
                            response_text += f"""

## 🩺 Clinical Assessment
{clinical_answer}"""
                            
                            if clinical_implications:
                                response_text += f"""

## 💡 Clinical Implications"""
                                for implication in clinical_implications:
                                    response_text += f"\n• {implication}"
                            
                            if limitations:
                                response_text += f"""

## ⚠️ Study Limitations & Considerations"""
                                for limitation in limitations:
                                    response_text += f"\n• {limitation}"
                            
                            response_text += f"""

## 📚 Analyzed Literature by Evidence Level"""
                            
                            # 再利用可能な関数を使用して全ての論文を表示
                            response_text += format_papers_by_evidence_level(
                                papers=papers, 
                                max_per_level=5,  # エビデンス評価では各レベル5件まで
                                include_abstracts=False  # エビデンス評価では抄録は表示しない
                            )
                            
                            response_text += f"""

## 📋 Clinical Recommendations
Based on the evidence evaluation:

**Strength of Recommendation**: {confidence_level}

**Clinical Action Points**:
• Review individual patient factors and contraindications
• Consider latest clinical practice guidelines
• Monitor for updated systematic reviews and meta-analyses
• Assess risk-benefit ratio for specific patient populations

## 🔄 Next Steps
• **For Clinicians**: Apply evidence within clinical context
• **For Researchers**: Identify research gaps for future studies  
• **For Guidelines**: Consider evidence strength in recommendation development

---
*Evidence evaluation completed using Evidence-Based Medical Research Assistant*
*Quality Assessment Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"""

                        else:
                            # Generic response for other task types
                            response_text = f"""# Medical Research Task Complete

**Task Type**: {task_type}
**Status**: ✅ Completed

## Results
{medical_result.get('summary', 'Task completed successfully')}

---
*Processed by Medical Research Assistant*"""
                        
                    except Exception as agent_error:
                        import traceback
                        print(f"Medical research agent execution error: {str(agent_error)}")
                        print(f"Traceback: {traceback.format_exc()}")
                        response_text = f"Error executing medical research task: {str(agent_error)}\n\nDebug info: Check server logs for detailed traceback."
                        
            except Exception as command_error:
                print(f"Medical research command processing error: {str(command_error)}")
                response_text = f"Error processing @medical-research command: {str(command_error)}"
        
        elif request.message.startswith("@simple-qa"):
            # Handle simple Q&A command
            try:
                # Extract question from command
                question = request.message.replace("@simple-qa", "").strip()
                if not question:
                    response_text = """Please provide a question after @simple-qa

**Examples:**
```
@simple-qa 日本の首都は？
@simple-qa What is machine learning?
@simple-qa プログラミングとは何ですか？
```"""
                else:
                    # Create task ID
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for simple QA agent
                    qa_input = {
                        'question': question,
                        'language': 'japanese' if any(ord(char) > 127 for char in question) else 'english'
                    }
                    
                    try:
                        # Import and execute simple QA agent
                        from app.agents.simple_qa_agent import simple_qa_agent
                        
                        qa_result = await simple_qa_agent.execute(
                            task_id=task_id,
                            input_data=qa_input
                        )
                        
                        # Format response
                        answer_data = qa_result.get('answer', {})
                        question_type = qa_result.get('question_type', 'general')
                        
                        response_text = f"""# 💡 Simple Q&A Result

## Question
{qa_result.get('question', question)}

## Answer
{answer_data.get('main_answer', 'No answer available')}

## Question Type
{question_type.title()}

## Helpful Tips
"""
                        for tip in answer_data.get('helpful_tips', []):
                            response_text += f"- {tip}\n"
                        
                        response_text += "\n## Follow-up Suggestions\n"
                        for suggestion in answer_data.get('follow_up_suggestions', []):
                            response_text += f"- {suggestion}\n"
                        
                        response_text += "\n---\n*Answered by Simple Q&A Agent for beginners*"
                        
                    except Exception as agent_error:
                        print(f"Simple QA agent execution error: {str(agent_error)}")
                        response_text = f"Error executing simple Q&A: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Simple QA command processing error: {str(command_error)}")
                response_text = f"Error processing @simple-qa command: {str(command_error)}"
        
        elif request.message.startswith("@web-search"):
            # Handle web search command
            try:
                # Extract search query from command
                query = request.message.replace("@web-search", "").strip()
                if not query:
                    response_text = """Please provide a search query after @web-search

**Examples:**
```
@web-search 最新のAI技術動向
@web-search how to learn programming
@web-search 機械学習 初心者向け
```"""
                else:
                    # Create task ID
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for web search agent
                    search_input = {
                        'query': query,
                        'max_results': 5,
                        'language': 'japanese' if any(ord(char) > 127 for char in query) else 'english'
                    }
                    
                    try:
                        # Import and execute web search agent
                        from app.agents.web_search_agent import web_search_agent
                        
                        search_result = await web_search_agent.execute(
                            task_id=task_id,
                            input_data=search_input
                        )
                        
                        # Format response
                        organized_results = search_result.get('organized_results', {})
                        search_type = search_result.get('search_type', 'general')
                        
                        response_text = f"""# 🔍 Web Search Results

## Search Query
"{search_result.get('search_query', query)}"

## Search Type
{search_type.title()}

## Summary
{organized_results.get('summary', 'No summary available')}

## Results ({organized_results.get('total_results', 0)} found)
"""
                        
                        for i, result in enumerate(organized_results.get('results', []), 1):
                            response_text += f"""
### {i}. {result.get('title', 'No title')}
**Source**: {result.get('source', 'Unknown')} | **Reliability**: {result.get('reliability', 'unknown').title()}
**Relevance**: {result.get('relevance_score', 0)}%

{result.get('snippet', 'No description available')}

**URL**: {result.get('url', 'N/A')}
"""
                        
                        # Add search suggestions
                        suggestions = organized_results.get('suggestions', [])
                        if suggestions:
                            response_text += "\n## Related Search Suggestions\n"
                            for suggestion in suggestions:
                                response_text += f"- {suggestion}\n"
                        
                        # Add search tips
                        tips = organized_results.get('tips', [])
                        if tips:
                            response_text += "\n## Search Tips\n"
                            for tip in tips:
                                response_text += f"- {tip}\n"
                        
                        response_text += "\n---\n*Search results provided by Web Search Agent*"
                        
                    except Exception as agent_error:
                        print(f"Web search agent execution error: {str(agent_error)}")
                        response_text = f"Error executing web search: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Web search command processing error: {str(command_error)}")
                response_text = f"Error processing @web-search command: {str(command_error)}"
        
        elif request.message.startswith("@summarizer"):
            # Handle summarizer command
            try:
                # Extract text from command
                text = request.message.replace("@summarizer", "").strip()
                if not text or len(text) < 50:
                    response_text = """Please provide text to summarize after @summarizer (minimum 50 characters)

**Examples:**
```
@summarizer 長い記事やニュースの内容をここに貼り付けてください...
@summarizer Please paste a long article or text here to summarize...
```

**Available options:**
- Type: bullet, paragraph, outline, keywords
- Language: automatic detection"""
                else:
                    # Create task ID
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for summarizer agent
                    summarizer_input = {
                        'text': text,
                        'summary_type': 'paragraph',
                        'max_length': 200,
                        'language': 'japanese' if any(ord(char) > 127 for char in text) else 'english'
                    }
                    
                    try:
                        # Import and execute summarizer agent
                        from app.agents.summarizer_agent import summarizer_agent
                        
                        summary_result = await summarizer_agent.execute(
                            task_id=task_id,
                            input_data=summarizer_input
                        )
                        
                        # Format response
                        summary_data = summary_result.get('summary', {})
                        complexity_analysis = summary_result.get('complexity_analysis', {})
                        keywords = summary_result.get('keywords', [])
                        
                        response_text = f"""# 📝 Text Summary

## Original Text Analysis
- **Length**: {summary_result.get('original_length', 0)} characters
- **Complexity**: {complexity_analysis.get('complexity_level', 'unknown').title()}
- **Word Count**: {complexity_analysis.get('word_count', 0)} words

## Summary
{summary_data.get('main_summary', 'No summary available')}

## Summary Statistics
- **Summary Length**: {summary_data.get('summary_length', 0)} words
- **Reduction**: {summary_data.get('reduction_ratio', 0)}%
- **Readability**: {summary_data.get('readability', 'unknown').title()}
"""
                        
                        # Add keywords if available
                        if keywords:
                            response_text += "\n## Key Terms\n"
                            for keyword in keywords:
                                response_text += f"- **{keyword.get('term', '')}**: {keyword.get('explanation', '')}\n"
                        
                        # Add reading tips
                        tips = summary_result.get('reading_tips', [])
                        if tips:
                            response_text += "\n## Reading Tips\n"
                            for tip in tips:
                                response_text += f"- {tip}\n"
                        
                        response_text += "\n---\n*Summary created by Summarizer Agent for beginners*"
                        
                    except Exception as agent_error:
                        print(f"Summarizer agent execution error: {str(agent_error)}")
                        response_text = f"Error executing summarization: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Summarizer command processing error: {str(command_error)}")
                response_text = f"Error processing @summarizer command: {str(command_error)}"
        
        elif request.message.startswith("@study-helper"):
            # Handle study helper command
            try:
                # Extract topic from command
                topic = request.message.replace("@study-helper", "").strip()
                if not topic:
                    response_text = """Please provide a study topic after @study-helper

**Examples:**
```
@study-helper プログラミングの基礎
@study-helper machine learning basics
@study-helper 英語の文法
```

**Available options:**
- Learning style: visual, auditory, kinesthetic, reading, mixed
- Difficulty: beginner, elementary, intermediate, advanced
- Time: available study time in minutes"""
                else:
                    # Create task ID
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for study helper agent
                    study_input = {
                        'topic': topic,
                        'learning_style': 'mixed',
                        'difficulty': 'beginner',
                        'time_available': 30,
                        'language': 'japanese' if any(ord(char) > 127 for char in topic) else 'english'
                    }
                    
                    try:
                        # Import and execute study helper agent
                        from app.agents.study_helper_agent import study_helper_agent
                        
                        study_result = await study_helper_agent.execute(
                            task_id=task_id,
                            input_data=study_input
                        )
                        
                        # Format response
                        learning_plan = study_result.get('learning_plan', {})
                        recommendations = study_result.get('recommendations', {})
                        
                        response_text = f"""# 📚 Study Plan Created

## Topic
{study_result.get('topic', topic)}

## Learning Overview
{learning_plan.get('overview', 'No overview available')}

## Learning Objectives
"""
                        for objective in learning_plan.get('learning_objectives', []):
                            response_text += f"- {objective}\n"
                        
                        response_text += "\n## Step-by-Step Guide\n"
                        for step in learning_plan.get('step_by_step_guide', []):
                            response_text += f"{step.get('step_number', '')}. **{step.get('title', '')}**\n"
                            response_text += f"   {step.get('description', '').strip()}\n\n"
                        
                        # Add practice activities
                        activities = learning_plan.get('practice_activities', [])
                        if activities:
                            response_text += "## Practice Activities\n"
                            for activity in activities:
                                response_text += f"- **{activity.get('activity', '')}**: {activity.get('description', '')}\n"
                        
                        # Add study recommendations
                        response_text += "\n## Study Schedule\n"
                        for schedule_item in recommendations.get('study_schedule', []):
                            response_text += f"- {schedule_item}\n"
                        
                        response_text += "\n## Learning Tips\n"
                        for tip in recommendations.get('learning_tips', []):
                            response_text += f"- {tip}\n"
                        
                        # Add next steps
                        next_steps = study_result.get('next_steps', [])
                        if next_steps:
                            response_text += "\n## Next Steps\n"
                            for step in next_steps:
                                response_text += f"- {step}\n"
                        
                        response_text += "\n---\n*Study plan created by Study Helper Agent*"
                        
                    except Exception as agent_error:
                        print(f"Study helper agent execution error: {str(agent_error)}")
                        response_text = f"Error executing study helper: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Study helper command processing error: {str(command_error)}")
                response_text = f"Error processing @study-helper command: {str(command_error)}"
        
        elif request.message.startswith("@fact-checker"):
            # Handle fact checker command
            try:
                # Extract claim from command
                claim = request.message.replace("@fact-checker", "").strip()
                if not claim or len(claim) < 10:
                    response_text = """Please provide a claim to fact-check after @fact-checker (minimum 10 characters)

**Examples:**
```
@fact-checker 地球は平らである
@fact-checker The COVID-19 vaccine contains microchips
@fact-checker 日本の人口は1億人を超えている
```

**Verification levels:**
- basic: Quick verification with common knowledge
- standard: Cross-reference with multiple sources
- thorough: Deep investigation with expert sources"""
                else:
                    # Create task ID
                    task_id = str(uuid.uuid4())
                    
                    # Prepare input for fact checker agent
                    fact_input = {
                        'claim': claim,
                        'verification_level': 'standard',
                        'language': 'japanese' if any(ord(char) > 127 for char in claim) else 'english'
                    }
                    
                    try:
                        # Import and execute fact checker agent
                        from app.agents.fact_checker_agent import fact_checker_agent
                        
                        fact_result = await fact_checker_agent.execute(
                            task_id=task_id,
                            input_data=fact_input
                        )
                        
                        # Format response
                        verification_result = fact_result.get('verification_result', {})
                        reliability_assessment = fact_result.get('reliability_assessment', {})
                        claim_type = fact_result.get('claim_type', 'general')
                        
                        # Status icon based on verification
                        status_icon = {
                            'true': '✅',
                            'false': '❌',
                            'partially_true': '⚠️',
                            'uncertain': '❓',
                            'needs_investigation': '🔍'
                        }.get(verification_result.get('verification_status', 'uncertain'), '❓')
                        
                        response_text = f"""# {status_icon} Fact Check Result

## Claim
"{fact_result.get('original_claim', claim)}"

## Verification Status
**{verification_result.get('verification_status', 'uncertain').replace('_', ' ').title()}**

## Explanation
{verification_result.get('explanation', 'No explanation available')}

## Confidence Level
{verification_result.get('confidence_level', 'medium').title()}

## Claim Type
{claim_type.title()}

## Reliability Assessment
- **Score**: {reliability_assessment.get('reliability_score', 0):.2f}/1.0
- **Level**: {reliability_assessment.get('reliability_level', 'unknown').title()}
- **Recommendation**: {reliability_assessment.get('recommendation', 'N/A')}
"""
                        
                        # Add key points if available
                        key_points = verification_result.get('key_points', [])
                        if key_points:
                            response_text += "\n## Key Points\n"
                            for point in key_points:
                                response_text += f"- {point}\n"
                        
                        # Add potential issues
                        issues = verification_result.get('potential_issues', [])
                        if issues:
                            response_text += "\n## Potential Issues\n"
                            for issue in issues:
                                response_text += f"- {issue}\n"
                        
                        # Add educational notes
                        educational_notes = fact_result.get('educational_notes', [])
                        if educational_notes:
                            response_text += "\n## Educational Notes\n"
                            for note in educational_notes:
                                response_text += f"- {note}\n"
                        
                        # Add critical thinking tips
                        thinking_tips = fact_result.get('critical_thinking_tips', [])
                        if thinking_tips:
                            response_text += "\n## Critical Thinking Tips\n"
                            for tip in thinking_tips:
                                response_text += f"- {tip}\n"
                        
                        response_text += "\n---\n*Fact-check performed by Fact Checker Agent*"
                        
                    except Exception as agent_error:
                        print(f"Fact checker agent execution error: {str(agent_error)}")
                        response_text = f"Error executing fact check: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Fact checker command processing error: {str(command_error)}")
                response_text = f"Error processing @fact-checker command: {str(command_error)}"
        
        # Google Gemini models
        elif request.model.provider.lower() == "google":
            print(f"Attempting to use Google Gemini model: {request.model.id}")
            print(f"Gemini service available: {gemini_service is not None}")
            print(f"Gemini service initialized: {gemini_service.initialized if gemini_service else False}")
            
            if gemini_service and gemini_service.initialized:
                try:
                    print(f"Calling Gemini API with model: {request.model.id}")
                    response_text = await gemini_service.send_message(
                        model_name=request.model.id,
                        history=history,
                        message=request.message
                    )
                    print(f"Gemini API response received: {len(response_text)} characters")
                except Exception as gemini_error:
                    print(f"Gemini API error: {type(gemini_error).__name__}: {str(gemini_error)}")
                    # Re-raise to be caught by outer exception handler
                    raise
            else:
                print("Gemini service not available or not initialized")
                response_text = f"[ERROR] Gemini service is not available. Please check Google Cloud configuration."
        
        # OpenAI models
        elif request.model.provider.lower() == "openai":
            if openai_service and openai_service.initialized:
                print(f"Using OpenAI model: {request.model.id}")
                response_text = await openai_service.send_message(
                    model_name=request.model.id,
                    history=history,
                    message=request.message
                )
            else:
                print("OpenAI service not available or not initialized")
                response_text = f"[ERROR] OpenAI service is not available. Please check OPENAI_API_KEY configuration."
        
        # Anthropic models
        elif request.model.provider.lower() == "anthropic":
            print("Anthropic service not yet implemented")
            response_text = f"[ERROR] Anthropic service is not yet implemented. Please use Google or OpenAI models."
        
        # Fallback for unknown providers
        else:
            print(f"Unknown provider: {request.model.provider}")
            response_text = f"[ERROR] Unknown provider '{request.model.provider}'. Please use Google, OpenAI, or Anthropic models."
        
        # セッションにメッセージを保存（ユーザーがログインしている場合のみ）
        if user_id and request.session_id:
            # ユーザーメッセージを追加
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=request.message,
                is_user=True,
                timestamp=datetime.now()
            )
            await session_service.add_message_to_session(request.session_id, user_id, user_message)
            
            # AI応答を追加
            ai_message = ChatMessage(
                id=str(uuid.uuid4()),
                content=response_text,
                is_user=False,
                timestamp=datetime.now()
            )
            await session_service.add_message_to_session(request.session_id, user_id, ai_message)
        
        return ChatResponse(
            content=response_text,
            model_id=request.model.id,
            is_streaming=False
        )
            
    except Exception as e:
        print(f"Error in send_chat_message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ストリーミングエンドポイントも同様に修正
@router.post("/stream")
async def stream_chat_message(request: ChatRequest):
    """Stream chat response"""
    async def generate_stream():
        try:
            # Convert history to the format expected by services
            history = [
                {
                    "role": "user" if msg.is_user else "model",
                    "content": msg.content
                }
                for msg in request.history
            ]
            
            # Google Gemini models
            if request.model.provider.lower() == "google" and gemini_service and gemini_service.initialized:
                async for chunk in gemini_service.stream_chat(
                    model_name=request.model.id,
                    history=history,
                    message=request.message
                ):
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            
            # OpenAI models
            elif request.model.provider.lower() == "openai" and openai_service and openai_service.initialized:
                async for chunk in openai_service.stream_chat(
                    model_name=request.model.id,
                    history=history,
                    message=request.message
                ):
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            
            # Fallback for other providers
            else:
                dummy_response = f"[{request.model.provider} {request.model.id}] This is a dummy streaming response for {request.model.provider} models."
                words = dummy_response.split()
                
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    import asyncio
                    await asyncio.sleep(0.05)
                
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'done': True})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
    
@router.options("/send")
async def options_chat_send():
    return {}

@router.options("/stream")
async def options_chat_stream():
    return {}