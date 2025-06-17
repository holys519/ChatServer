"""
Review Creation Multi-Agent System using LangGraph
Coordinates multiple specialized agents to create comprehensive literature reviews
"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import json

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate

from app.services.agent_base import BaseAgent
from app.services.pubmed_service import pubmed_service, PubMedPaper
from app.models.schemas import TaskStatus

class ReviewState(TypedDict):
    """State for the review creation workflow"""
    topic: str
    review_type: str
    target_audience: str
    length: str
    papers: List[Dict[str, Any]]
    search_strategy: Dict[str, Any]
    analysis_results: Dict[str, Any]
    outline: Dict[str, Any]
    sections: Dict[str, str]
    final_review: str
    current_step: str
    progress: float
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]

class ReviewCreationAgent(BaseAgent):
    """Multi-agent system for creating literature reviews using LangGraph"""
    
    def __init__(self):
        super().__init__(
            name="ReviewCreationAgent",
            description="Creates comprehensive literature reviews using multiple specialized sub-agents",
            model_name="gemini-2.0-flash-001",
            temperature=0.4
        )
        
        self.workflow = self._build_workflow()
    
    def get_prompt_template(self) -> ChatPromptTemplate:
        """Get the review creation prompt template"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are the Review Creation Agent, a sophisticated multi-agent system for creating comprehensive literature reviews.

You coordinate multiple specialized sub-agents:
- Search Strategist: Develops comprehensive search strategies
- Paper Analyst: Analyzes papers for key insights and themes
- Structure Architect: Creates review outlines and organization
- Content Writer: Generates well-written review sections
- Quality Reviewer: Ensures quality and coherence

Your role is to orchestrate these agents to produce high-quality literature reviews that are:
- Comprehensive and systematic
- Well-structured and coherent
- Appropriate for the target audience
- Based on current research evidence"""),
            ("human", "{request}")
        ])
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for review creation"""
        workflow = StateGraph(ReviewState)
        
        # Add nodes (agents/steps)
        workflow.add_node("search_strategist", self._search_strategist_node)
        workflow.add_node("paper_collector", self._paper_collector_node)
        workflow.add_node("paper_analyst", self._paper_analyst_node)
        workflow.add_node("structure_architect", self._structure_architect_node)
        workflow.add_node("content_writer", self._content_writer_node)
        workflow.add_node("quality_reviewer", self._quality_reviewer_node)
        workflow.add_node("finalizer", self._finalizer_node)
        
        # Define the workflow edges
        workflow.set_entry_point("search_strategist")
        
        workflow.add_edge("search_strategist", "paper_collector")
        workflow.add_edge("paper_collector", "paper_analyst")
        workflow.add_edge("paper_analyst", "structure_architect")
        workflow.add_edge("structure_architect", "content_writer")
        workflow.add_edge("content_writer", "quality_reviewer")
        workflow.add_edge("quality_reviewer", "finalizer")
        workflow.add_edge("finalizer", END)
        
        return workflow.compile()
    
    async def execute(
        self, 
        task_id: str, 
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the review creation workflow"""
        try:
            # Initialize state
            initial_state: ReviewState = {
                "topic": input_data.get('topic', ''),
                "review_type": input_data.get('review_type', 'narrative'),
                "target_audience": input_data.get('target_audience', 'academic'),
                "length": input_data.get('length', 'medium'),
                "papers": [],
                "search_strategy": {},
                "analysis_results": {},
                "outline": {},
                "sections": {},
                "final_review": "",
                "current_step": "initializing",
                "progress": 0.0,
                "messages": [HumanMessage(content=f"Create a {input_data.get('review_type', 'narrative')} literature review on: {input_data.get('topic', '')}")]
            }
            
            # Store task_id for progress updates
            self._current_task_id = task_id
            
            await self.update_task_progress(task_id, 5.0, "Initializing review creation workflow")
            
            # Execute the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Prepare output
            output_data = {
                'topic': final_state['topic'],
                'review_type': final_state['review_type'],
                'target_audience': final_state['target_audience'],
                'papers_analyzed': len(final_state['papers']),
                'search_strategy': final_state['search_strategy'],
                'analysis_results': final_state['analysis_results'],
                'outline': final_state['outline'],
                'final_review': final_state['final_review'],
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'word_count': len(final_state['final_review'].split()),
                    'sections_count': len(final_state['sections'])
                }
            }
            
            return output_data
            
        except Exception as e:
            print(f"❌ Review Creation Agent execution error: {str(e)}")
            raise Exception(f"Review Creation Agent execution failed: {str(e)}")
    
    async def _search_strategist_node(self, state: ReviewState) -> ReviewState:
        """Search Strategist Agent: Develops comprehensive search strategy"""
        try:
            await self.update_task_progress(self._current_task_id, 15.0, "Developing search strategy")
            
            strategy_prompt = f"""
As the Search Strategist, develop a comprehensive search strategy for a {state['review_type']} literature review on: "{state['topic']}"

Target audience: {state['target_audience']}
Review length: {state['length']}

Create a search strategy that includes:

1. **Primary Keywords**: Main search terms
2. **Secondary Keywords**: Related and synonym terms
3. **Search Databases**: Recommended databases beyond PubMed
4. **Inclusion Criteria**: What types of papers to include
5. **Exclusion Criteria**: What to exclude
6. **Time Range**: Suggested publication years
7. **Study Types**: Preferred study designs

Format as a structured strategy that other agents can follow.
"""
            
            messages = state["messages"] + [HumanMessage(content=strategy_prompt)]
            response = await self.invoke_llm(messages)
            
            # Parse strategy (simplified)
            search_strategy = {
                "strategy_text": response,
                "primary_keywords": self._extract_keywords_from_strategy(response),
                "time_range": "5 years",  # Default
                "max_papers": 50 if state['length'] == 'long' else 30 if state['length'] == 'medium' else 15
            }
            
            state["search_strategy"] = search_strategy
            state["current_step"] = "search_strategy_complete"
            state["progress"] = 15.0
            state["messages"].append(AIMessage(content=response))
            
            return state
            
        except Exception as e:
            print(f"❌ Search Strategist error: {str(e)}")
            state["current_step"] = "search_strategy_error"
            return state
    
    async def _paper_collector_node(self, state: ReviewState) -> ReviewState:
        """Paper Collector Agent: Searches and collects relevant papers"""
        try:
            await self.update_task_progress(self._current_task_id, 30.0, "Collecting research papers")
            
            # Use search strategy to find papers
            search_strategy = state["search_strategy"]
            
            # Primary search
            primary_query = f"{state['topic']} {' '.join(search_strategy.get('primary_keywords', []))}"
            
            papers = await pubmed_service.search_papers(
                query=primary_query,
                max_results=search_strategy.get('max_papers', 30),
                years_back=5,
                include_abstracts=True
            )
            
            # Convert to dict format
            papers_data = []
            for paper in papers:
                papers_data.append({
                    'pmid': paper.pmid,
                    'title': paper.title,
                    'authors': paper.authors,
                    'abstract': paper.abstract,
                    'journal': paper.journal,
                    'publication_date': paper.publication_date,
                    'doi': paper.doi,
                    'keywords': paper.keywords,
                    'url': paper.url
                })
            
            state["papers"] = papers_data
            state["current_step"] = "papers_collected"
            state["progress"] = 30.0
            
            return state
            
        except Exception as e:
            print(f"❌ Paper Collector error: {str(e)}")
            state["current_step"] = "paper_collection_error"
            return state
    
    async def _paper_analyst_node(self, state: ReviewState) -> ReviewState:
        """Paper Analyst Agent: Analyzes papers for themes and insights"""
        try:
            await self.update_task_progress(self._current_task_id, 50.0, "Analyzing research papers")
            
            if not state["papers"]:
                state["analysis_results"] = {"error": "No papers to analyze"}
                return state
            
            # Prepare papers for analysis
            papers_summary = []
            for paper in state["papers"][:20]:  # Limit for LLM context
                summary = f"""
Title: {paper['title']}
Authors: {', '.join(paper['authors'][:3])}
Journal: {paper['journal']}
Date: {paper['publication_date']}
Abstract: {paper['abstract'][:400]}...
Keywords: {', '.join(paper['keywords'])}
"""
                papers_summary.append(summary)
            
            analysis_prompt = f"""
As the Paper Analyst, analyze these {len(state['papers'])} research papers for a {state['review_type']} review on "{state['topic']}":

{chr(10).join(papers_summary)}

Provide a comprehensive analysis including:

1. **Major Themes**: 5-7 key themes across the papers
2. **Methodological Approaches**: Common research methods
3. **Key Findings**: Most important discoveries/conclusions
4. **Controversies/Debates**: Areas of disagreement or debate
5. **Research Gaps**: What's missing in current research
6. **Temporal Trends**: How research has evolved over time
7. **Quality Assessment**: Overall quality of the evidence

Structure your analysis to guide the creation of a {state['target_audience']} literature review.
"""
            
            messages = [HumanMessage(content=analysis_prompt)]
            analysis_response = await self.invoke_llm(messages)
            
            # Extract themes for structure
            themes = self._extract_themes_from_analysis(analysis_response)
            
            analysis_results = {
                "analysis_text": analysis_response,
                "major_themes": themes,
                "paper_count": len(state["papers"]),
                "quality_score": self._assess_overall_quality(state["papers"])
            }
            
            state["analysis_results"] = analysis_results
            state["current_step"] = "analysis_complete"
            state["progress"] = 50.0
            
            return state
            
        except Exception as e:
            print(f"❌ Paper Analyst error: {str(e)}")
            state["current_step"] = "analysis_error"
            return state
    
    async def _structure_architect_node(self, state: ReviewState) -> ReviewState:
        """Structure Architect Agent: Creates review outline and organization"""
        try:
            await self.update_task_progress(self._current_task_id, 65.0, "Creating review structure")
            
            themes = state["analysis_results"].get("major_themes", [])
            
            structure_prompt = f"""
As the Structure Architect, create a detailed outline for a {state['review_type']} literature review on "{state['topic']}".

Review specifications:
- Type: {state['review_type']}
- Target audience: {state['target_audience']}
- Length: {state['length']}
- Papers analyzed: {len(state['papers'])}

Major themes identified: {', '.join(themes)}

Create a structured outline with:

1. **Introduction Section**
   - Background and context
   - Objectives and scope
   - Review methodology

2. **Main Body Sections** (organize around themes)
   - Section titles and purposes
   - Key papers to cite in each section
   - Logical flow between sections

3. **Discussion/Synthesis Section**
   - Integration of findings
   - Implications
   - Limitations

4. **Conclusion Section**
   - Summary of key findings
   - Future research directions

Provide specific section titles, main points, and the logical flow.
"""
            
            messages = [HumanMessage(content=structure_prompt)]
            structure_response = await self.invoke_llm(messages)
            
            # Parse outline (simplified)
            outline = {
                "outline_text": structure_response,
                "sections": self._extract_sections_from_outline(structure_response),
                "estimated_length": self._estimate_section_lengths(state['length'])
            }
            
            state["outline"] = outline
            state["current_step"] = "structure_complete"
            state["progress"] = 65.0
            
            return state
            
        except Exception as e:
            print(f"❌ Structure Architect error: {str(e)}")
            state["current_step"] = "structure_error"
            return state
    
    async def _content_writer_node(self, state: ReviewState) -> ReviewState:
        """Content Writer Agent: Generates review content"""
        try:
            await self.update_task_progress(self._current_task_id, 80.0, "Writing review content")
            
            outline = state["outline"]
            analysis = state["analysis_results"]
            
            # Generate each section
            sections = {}
            section_names = outline.get("sections", ["Introduction", "Literature Review", "Discussion", "Conclusion"])
            
            for i, section_name in enumerate(section_names):
                section_prompt = f"""
As the Content Writer, write the "{section_name}" section for a {state['review_type']} literature review on "{state['topic']}".

Context:
- Target audience: {state['target_audience']}
- Review length: {state['length']}
- Papers analyzed: {len(state['papers'])}

Available analysis: {analysis.get('analysis_text', '')[:1000]}...

Section requirements:
- Academic writing style appropriate for {state['target_audience']}
- Proper integration of research findings
- Critical analysis, not just summary
- Logical flow and clear arguments

Write a comprehensive {section_name.lower()} section (aim for {self._get_section_length(state['length'], section_name)} words).
"""
                
                messages = [HumanMessage(content=section_prompt)]
                section_content = await self.invoke_llm(messages)
                sections[section_name] = section_content
                
                # Update progress
                section_progress = 80.0 + (i + 1) / len(section_names) * 10
                await self.update_task_progress(self._current_task_id, section_progress, f"Writing {section_name}")
            
            state["sections"] = sections
            state["current_step"] = "content_complete"
            state["progress"] = 90.0
            
            return state
            
        except Exception as e:
            print(f"❌ Content Writer error: {str(e)}")
            state["current_step"] = "content_error"
            return state
    
    async def _quality_reviewer_node(self, state: ReviewState) -> ReviewState:
        """Quality Reviewer Agent: Reviews and improves content quality"""
        try:
            await self.update_task_progress(self._current_task_id, 95.0, "Reviewing and refining content")
            
            # Combine all sections
            full_review = ""
            for section_name, content in state["sections"].items():
                full_review += f"\n\n## {section_name}\n\n{content}"
            
            quality_prompt = f"""
As the Quality Reviewer, review this {state['review_type']} literature review on "{state['topic']}" and provide improvements.

Current review:
{full_review}

Check for:
1. **Coherence**: Logical flow between sections
2. **Completeness**: All important aspects covered
3. **Academic Rigor**: Appropriate depth and analysis
4. **Clarity**: Clear writing for {state['target_audience']}
5. **Balance**: Fair representation of different perspectives

Provide an improved version that maintains the content but enhances quality, flow, and readability.
"""
            
            messages = [HumanMessage(content=quality_prompt)]
            improved_review = await self.invoke_llm(messages)
            
            state["final_review"] = improved_review
            state["current_step"] = "quality_review_complete"
            state["progress"] = 95.0
            
            return state
            
        except Exception as e:
            print(f"❌ Quality Reviewer error: {str(e)}")
            state["final_review"] = "\n\n".join([f"## {name}\n\n{content}" for name, content in state["sections"].items()])
            state["current_step"] = "quality_review_error"
            return state
    
    async def _finalizer_node(self, state: ReviewState) -> ReviewState:
        """Finalizer Agent: Adds final touches and metadata"""
        try:
            await self.update_task_progress(self._current_task_id, 100.0, "Finalizing review")
            
            # Add metadata and final formatting
            final_review = f"""# Literature Review: {state['topic']}

**Review Type**: {state['review_type'].title()}
**Target Audience**: {state['target_audience'].title()}
**Papers Analyzed**: {len(state['papers'])}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{state['final_review']}

---

## References

*This review is based on {len(state['papers'])} research papers retrieved from PubMed and other academic databases. Detailed citations available upon request.*

---

*Generated by CRA-Copilot Review Creation Agent*
"""
            
            state["final_review"] = final_review
            state["current_step"] = "complete"
            state["progress"] = 100.0
            
            return state
            
        except Exception as e:
            print(f"❌ Finalizer error: {str(e)}")
            state["current_step"] = "finalizer_error"
            return state
    
    # Helper methods
    
    def _extract_keywords_from_strategy(self, strategy_text: str) -> List[str]:
        """Extract keywords from strategy text"""
        # Simple keyword extraction - could be enhanced
        import re
        keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', strategy_text)
        return keywords[:10]
    
    def _extract_themes_from_analysis(self, analysis_text: str) -> List[str]:
        """Extract themes from analysis text"""
        # Look for numbered lists or bullet points
        import re
        themes = re.findall(r'(?:\d+\.|\-|\*)\s*([A-Z][^.:\n]+)', analysis_text)
        return themes[:7]
    
    def _extract_sections_from_outline(self, outline_text: str) -> List[str]:
        """Extract section names from outline"""
        import re
        sections = re.findall(r'(?:\d+\.|\#\#)\s*([A-Z][^:\n]+)', outline_text)
        if not sections:
            return ["Introduction", "Literature Review", "Discussion", "Conclusion"]
        return sections[:6]
    
    def _estimate_section_lengths(self, length: str) -> Dict[str, int]:
        """Estimate word counts for sections"""
        base_lengths = {
            "short": 150,
            "medium": 300,
            "long": 500
        }
        return {"per_section": base_lengths.get(length, 300)}
    
    def _get_section_length(self, review_length: str, section_name: str) -> int:
        """Get target word count for a section"""
        base = {"short": 150, "medium": 300, "long": 500}.get(review_length, 300)
        
        # Adjust by section type
        if section_name.lower() in ["introduction", "conclusion"]:
            return int(base * 0.7)
        elif section_name.lower() in ["discussion", "literature review"]:
            return int(base * 1.3)
        return base
    
    def _assess_overall_quality(self, papers: List[Dict[str, Any]]) -> float:
        """Assess overall quality of paper collection"""
        if not papers:
            return 0.0
        
        # Simple quality assessment based on available metadata
        quality_score = 0.0
        for paper in papers:
            if paper.get('doi'):
                quality_score += 0.3
            if paper.get('journal'):
                quality_score += 0.2
            if len(paper.get('abstract', '')) > 200:
                quality_score += 0.3
            if len(paper.get('authors', [])) > 0:
                quality_score += 0.2
        
        return min(quality_score / len(papers), 1.0) * 100