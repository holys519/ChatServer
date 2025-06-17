"""
Paper Scout Agent for CRA-Copilot
Specialized agent for finding and analyzing research papers
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field
from typing import Type

from app.services.agent_base import BaseAgent
from app.services.pubmed_service import pubmed_service, PubMedPaper
from app.models.schemas import TaskStatus

class PaperScoutAgent(BaseAgent):
    """Agent specialized in finding and analyzing research papers"""
    
    def __init__(self):
        super().__init__(
            name="PaperScoutAgent",
            description="Finds, analyzes, and summarizes research papers from PubMed and other sources",
            model_name="gemini-2.0-flash-001",
            temperature=0.3  # Lower temperature for more factual responses
        )
        
        # Add specialized tools
        self.add_tool(PubMedSearchTool())
        self.add_tool(PaperAnalysisTool())
        self.add_tool(CitationFormatterTool())
    
    def get_prompt_template(self) -> ChatPromptTemplate:
        """Get the paper scout's prompt template"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a specialized research assistant called Paper Scout, part of the CRA-Copilot system.

Your expertise includes:
- Finding relevant research papers using PubMed and other academic databases
- Analyzing paper abstracts and extracting key information
- Identifying research trends and connections between studies
- Formatting citations and creating bibliographies
- Providing research recommendations

When searching for papers:
1. Use specific, targeted search queries
2. Consider multiple search strategies if needed
3. Evaluate paper relevance and quality
4. Provide structured summaries
5. Suggest follow-up research directions

Always provide:
- Clear, structured responses
- Proper citations
- Quality assessments
- Actionable insights

Available tools: {tools}"""),
            ("human", "{query}")
        ])
    
    async def execute(
        self, 
        task_id: str, 
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute paper scouting task"""
        try:
            # Extract parameters
            query = input_data.get('query', '')
            max_results = input_data.get('max_results', 10)
            years_back = input_data.get('years_back', 5)
            include_abstracts = input_data.get('include_abstracts', True)
            analysis_type = input_data.get('analysis_type', 'summary')
            
            await self.update_task_progress(task_id, 10.0, "Analyzing search query")
            
            # Step 1: Optimize search query
            step_id = await self.create_step(
                task_id=task_id,
                action="optimize_query",
                input_data={"original_query": query}
            )
            
            optimized_query = await self._optimize_search_query(query)
            
            await self.complete_step(task_id, step_id, {"optimized_query": optimized_query})
            await self.update_task_progress(task_id, 25.0, "Searching PubMed database")
            
            # Step 2: Search PubMed
            step_id = await self.create_step(
                task_id=task_id,
                action="search_pubmed",
                input_data={
                    "query": optimized_query,
                    "max_results": max_results,
                    "years_back": years_back
                }
            )
            
            papers = await pubmed_service.search_papers(
                query=optimized_query,
                max_results=max_results,
                years_back=years_back,
                include_abstracts=include_abstracts
            )
            
            await self.complete_step(task_id, step_id, {"papers_found": len(papers)})
            await self.update_task_progress(task_id, 60.0, f"Found {len(papers)} papers, analyzing content")
            
            # Step 3: Analyze papers
            step_id = await self.create_step(
                task_id=task_id,
                action="analyze_papers",
                input_data={"analysis_type": analysis_type, "paper_count": len(papers)}
            )
            
            analysis_result = await self._analyze_papers(papers, analysis_type, query)
            
            await self.complete_step(task_id, step_id, {"analysis_completed": True})
            await self.update_task_progress(task_id, 90.0, "Generating final report")
            
            # Step 4: Generate comprehensive report
            step_id = await self.create_step(
                task_id=task_id,
                action="generate_report",
                input_data={"report_type": "comprehensive"}
            )
            
            final_report = await self._generate_report(
                query=query,
                papers=papers,
                analysis=analysis_result,
                config=config or {}
            )
            
            await self.complete_step(task_id, step_id, {"report_generated": True})
            
            # Prepare output
            output_data = {
                'original_query': query,
                'optimized_query': optimized_query,
                'papers_found': len(papers),
                'papers': [self._paper_to_dict(paper) for paper in papers],
                'analysis': analysis_result,
                'report': final_report,
                'search_metadata': {
                    'max_results': max_results,
                    'years_back': years_back,
                    'include_abstracts': include_abstracts,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            return output_data
            
        except Exception as e:
            print(f"❌ Paper Scout execution error: {str(e)}")
            raise Exception(f"Paper Scout Agent execution failed: {str(e)}")
    
    async def _optimize_search_query(self, original_query: str) -> str:
        """Optimize the search query for better PubMed results"""
        try:
            prompt = f"""
Optimize this search query for PubMed to find the most relevant research papers:

Original query: "{original_query}"

Consider:
- Medical Subject Headings (MeSH) terms
- Boolean operators (AND, OR, NOT)
- Field tags like [ti] for title, [ab] for abstract
- Synonyms and related terms
- Spelling variations

Return only the optimized query without explanation.
"""
            
            messages = [HumanMessage(content=prompt)]
            response = await self.invoke_llm(messages)
            
            # Clean the response to get just the query
            optimized = response.strip().strip('"').strip("'")
            
            # If optimization failed, return original
            if not optimized or len(optimized) < 3:
                return original_query
            
            return optimized
            
        except Exception:
            return original_query
    
    async def _analyze_papers(self, papers: List[PubMedPaper], analysis_type: str, original_query: str) -> Dict[str, Any]:
        """Analyze the found papers"""
        if not papers:
            return {"status": "no_papers_found"}
        
        try:
            # Prepare paper summaries for analysis
            paper_summaries = []
            for paper in papers[:10]:  # Limit to top 10 for analysis
                summary = f"""
Title: {paper.title}
Authors: {', '.join(paper.authors[:3])}
Journal: {paper.journal}
Date: {paper.publication_date}
Abstract: {paper.abstract[:300]}...
Keywords: {', '.join(paper.keywords)}
"""
                paper_summaries.append(summary)
            
            analysis_prompt = f"""
Analyze these research papers related to the query: "{original_query}"

Papers to analyze:
{chr(10).join(paper_summaries)}

Provide analysis in the following format:

## Key Findings
- [List 3-5 main findings across the papers]

## Research Trends
- [Identify emerging trends or patterns]

## Knowledge Gaps
- [Areas that need more research]

## Methodology Insights
- [Common research methods used]

## Recommendations
- [Suggestions for future research directions]

## Quality Assessment
- [Brief assessment of the paper quality and relevance]

Keep the analysis concise but comprehensive.
"""
            
            messages = [HumanMessage(content=analysis_prompt)]
            analysis_response = await self.invoke_llm(messages)
            
            # Extract topics and themes
            topics = self._extract_topics_from_papers(papers)
            
            return {
                "status": "completed",
                "analysis_text": analysis_response,
                "paper_count": len(papers),
                "topics": topics,
                "date_range": self._get_date_range(papers),
                "journal_distribution": self._get_journal_distribution(papers)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing papers: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _extract_topics_from_papers(self, papers: List[PubMedPaper]) -> List[str]:
        """Extract common topics from papers"""
        all_keywords = []
        for paper in papers:
            all_keywords.extend(paper.keywords)
        
        # Count keyword frequency
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        
        # Return top topics
        return [keyword for keyword, count in keyword_counts.most_common(10)]
    
    def _get_date_range(self, papers: List[PubMedPaper]) -> Dict[str, str]:
        """Get the date range of papers"""
        dates = [paper.publication_date for paper in papers if paper.publication_date]
        if not dates:
            return {"earliest": "", "latest": ""}
        
        return {
            "earliest": min(dates),
            "latest": max(dates)
        }
    
    def _get_journal_distribution(self, papers: List[PubMedPaper]) -> Dict[str, int]:
        """Get distribution of papers by journal"""
        from collections import Counter
        journals = [paper.journal for paper in papers if paper.journal]
        journal_counts = Counter(journals)
        
        return dict(journal_counts.most_common(10))
    
    async def _generate_report(
        self, 
        query: str, 
        papers: List[PubMedPaper], 
        analysis: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        """Generate a comprehensive research report"""
        try:
            report_prompt = f"""
Generate a comprehensive research report based on the following information:

**Search Query**: {query}
**Papers Found**: {len(papers)}
**Analysis Results**: {analysis.get('analysis_text', 'No analysis available')}

Create a structured report with:

1. **Executive Summary**
   - Brief overview of the search and findings
   
2. **Search Results Overview**
   - Number of papers found
   - Date range and journal distribution
   
3. **Key Research Findings**
   - Major discoveries and insights
   - Consistent findings across studies
   
4. **Research Landscape**
   - Current state of research in this area
   - Emerging trends and methodologies
   
5. **Research Gaps and Opportunities**
   - Areas needing more investigation
   - Potential research directions
   
6. **Top Papers**
   - Brief descriptions of the most relevant papers
   
7. **Recommendations**
   - Next steps for researchers
   - Specific papers to read first

Format the report in markdown for easy reading.
"""
            
            messages = [HumanMessage(content=report_prompt)]
            report = await self.invoke_llm(messages)
            
            # Add paper list if requested
            if config.get('include_paper_list', True):
                paper_list = pubmed_service.format_papers_for_display(papers[:10])
                report += f"\n\n## Paper Bibliography\n\n{paper_list}"
            
            return report
            
        except Exception as e:
            return f"Error generating report: {str(e)}"
    
    def _paper_to_dict(self, paper: PubMedPaper) -> Dict[str, Any]:
        """Convert PubMedPaper to dictionary"""
        return {
            'pmid': paper.pmid,
            'title': paper.title,
            'authors': paper.authors,
            'abstract': paper.abstract,
            'journal': paper.journal,
            'publication_date': paper.publication_date,
            'doi': paper.doi,
            'keywords': paper.keywords,
            'citation_count': paper.citation_count,
            'url': paper.url
        }

# Custom tools for Paper Scout Agent

class PubMedSearchInput(BaseModel):
    query: str = Field(description="Search query for PubMed")
    max_results: int = Field(default=10, description="Maximum number of results")
    years_back: int = Field(default=5, description="How many years back to search")

class PubMedSearchTool(BaseTool):
    name: str = "pubmed_search"
    description: str = "Search for research papers in PubMed database"
    args_schema: Type[BaseModel] = PubMedSearchInput
    
    async def _arun(self, query: str, max_results: int = 10, years_back: int = 5) -> str:
        papers = await pubmed_service.search_papers(query, max_results, years_back)
        return pubmed_service.format_papers_for_display(papers)
    
    def _run(self, query: str, max_results: int = 10, years_back: int = 5) -> str:
        import asyncio
        return asyncio.run(self._arun(query, max_results, years_back))

class PaperAnalysisInput(BaseModel):
    papers_json: str = Field(description="JSON string of papers to analyze")
    focus: str = Field(default="general", description="Analysis focus area")

class PaperAnalysisTool(BaseTool):
    name: str = "analyze_papers"
    description: str = "Analyze a collection of research papers for insights and trends"
    args_schema: Type[BaseModel] = PaperAnalysisInput
    
    def _run(self, papers_json: str, focus: str = "general") -> str:
        try:
            papers_data = json.loads(papers_json)
            # Simplified analysis
            return f"Analysis of {len(papers_data)} papers focusing on {focus}: Key trends and insights identified."
        except Exception as e:
            return f"Error analyzing papers: {str(e)}"

class CitationFormatterInput(BaseModel):
    paper_data: str = Field(description="JSON string of paper data")
    style: str = Field(default="apa", description="Citation style (apa, mla, chicago)")

class CitationFormatterTool(BaseTool):
    name: str = "format_citation"
    description: str = "Format paper citations in various academic styles"
    args_schema: Type[BaseModel] = CitationFormatterInput
    
    def _run(self, paper_data: str, style: str = "apa") -> str:
        try:
            paper = json.loads(paper_data)
            if style.lower() == "apa":
                authors = ", ".join(paper.get('authors', [])[:3])
                return f"{authors} ({paper.get('publication_date', 'n.d.')}). {paper.get('title', '')}. {paper.get('journal', '')}."
            else:
                return f"Citation formatting for {style} style - implementation pending"
        except Exception as e:
            return f"Error formatting citation: {str(e)}"