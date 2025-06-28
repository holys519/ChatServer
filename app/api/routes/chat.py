from fastapi import APIRouter, HTTPException, Header
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

router = APIRouter()

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
    authorization: Optional[str] = Header(None)
):
    """Send a chat message and get complete response"""
    try:
        # デバッグ用ログ
        print(f"Received request: {request.model_dump_json()}")
        print(f"Model provider: {request.model.provider}")
        
        user_id = await get_user_id_from_auth(authorization)
        
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
                    response_text = """# Available CRA-Copilot Commands

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
*This literature review was created using the CRA-Copilot Review Creation Agent with multi-step workflow processing.*"""
                        
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
*This research was conducted using the enhanced CRA-Copilot Research Workflow Coordinator v{workflow_metadata.get('coordinator_version', '1.0')}*"""
                        
                    except Exception as agent_error:
                        print(f"Research workflow execution error: {str(agent_error)}")
                        response_text = f"Error executing complete research workflow: {str(agent_error)}"
                        
            except Exception as command_error:
                print(f"Research workflow command processing error: {str(command_error)}")
                response_text = f"Error processing @research-workflow command: {str(command_error)}"
        
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