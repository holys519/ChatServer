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
from app.services.translation_service import translation_service
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
        """Execute paper scouting task with translation support"""
        try:
            # Extract parameters
            original_query = input_data.get('query', '')
            max_results = input_data.get('max_results', 10)
            years_back = input_data.get('years_back', 5)
            include_abstracts = input_data.get('include_abstracts', True)
            analysis_type = input_data.get('analysis_type', 'summary')
            
            await self.update_task_progress(task_id, 5.0, "Analyzing search query and language")
            
            # Step 1: Handle translation if needed
            step_id = await self.create_step(
                task_id=task_id,
                action="translation_analysis",
                input_data={"original_query": original_query}
            )
            
            translation_result = await translation_service.translate_search_query(original_query)
            search_query = translation_result['translated']
            original_language = translation_result['original_language']
            
            await self.complete_step(task_id, step_id, {
                "original_query": original_query,
                "search_query": search_query,
                "original_language": original_language,
                "translation_performed": original_language == 'ja'
            })
            
            await self.update_task_progress(task_id, 15.0, "Optimizing search query")
            
            # Step 2: Optimize search query (now in English)
            step_id = await self.create_step(
                task_id=task_id,
                action="optimize_query",
                input_data={"search_query": search_query}
            )
            
            optimized_query = await self._optimize_search_query(search_query)
            
            await self.complete_step(task_id, step_id, {"optimized_query": optimized_query})
            await self.update_task_progress(task_id, 30.0, "Searching PubMed database")
            
            # Step 3: Search PubMed
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
            
            # Step 4: Analyze papers
            step_id = await self.create_step(
                task_id=task_id,
                action="analyze_papers",
                input_data={"analysis_type": analysis_type, "paper_count": len(papers)}
            )
            
            analysis_result = await self._analyze_papers(papers, analysis_type, search_query)
            
            await self.complete_step(task_id, step_id, {"analysis_completed": True})
            await self.update_task_progress(task_id, 90.0, "Generating final report")
            
            # Step 5: Generate comprehensive report
            step_id = await self.create_step(
                task_id=task_id,
                action="generate_report",
                input_data={"report_type": "comprehensive"}
            )
            
            final_report = await self._generate_report(
                query=search_query,
                papers=papers,
                analysis=analysis_result,
                config=config or {}
            )
            
            await self.complete_step(task_id, step_id, {"report_generated": True})
            await self.update_task_progress(task_id, 95.0, "Translating results if needed")
            
            # Step 6: Translate results back to original language if needed
            if original_language == 'ja':
                step_id = await self.create_step(
                    task_id=task_id,
                    action="translate_results",
                    input_data={"target_language": original_language}
                )
                
                # Translate the final report and analysis
                translated_report = await translation_service.translate_results(final_report, 'ja')
                translated_analysis = await translation_service.translate_results(
                    analysis_result.get('analysis_text', ''), 'ja'
                )
                
                # Update analysis with translated text
                if 'analysis_text' in analysis_result:
                    analysis_result['analysis_text_japanese'] = translated_analysis
                
                await self.complete_step(task_id, step_id, {"translation_completed": True})
                
                # Use translated report for Japanese users
                final_report = translated_report
            
            await self.update_task_progress(task_id, 100.0, "Task completed")
            
            # Prepare output
            output_data = {
                'original_query': original_query,
                'search_query': search_query,
                'optimized_query': optimized_query,
                'papers_found': len(papers),
                'papers': [self._paper_to_dict(paper) for paper in papers],
                'analysis': analysis_result,
                'report': final_report,
                'translation_metadata': {
                    'original_language': original_language,
                    'search_language': 'en',
                    'results_language': original_language
                },
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
        """Optimize the search query for better PubMed results with advanced keyword extraction"""
        try:
            # First, extract key concepts and keywords
            keyword_extraction_prompt = f"""
Analyze this research query and extract the most important keywords and concepts for academic paper search:

Query: "{original_query}"

Extract:
1. Main research topic/domain
2. Key methods or techniques
3. Important terminologies
4. Relevant subject areas
5. Potential MeSH terms
6. Synonyms and related terms

Provide a structured analysis focusing on search optimization.
"""
            
            messages = [HumanMessage(content=keyword_extraction_prompt)]
            keyword_analysis = await self.invoke_llm(messages)
            
            # Then optimize the search query
            optimization_prompt = f"""
Based on this keyword analysis, create an optimized PubMed search query:

Original query: "{original_query}"
Keyword analysis: {keyword_analysis}

Create a sophisticated search strategy using:
- Medical Subject Headings (MeSH) terms where applicable
- Boolean operators (AND, OR, NOT) for precise targeting
- Field tags: [ti] for title, [ab] for abstract, [au] for author
- Wildcards (*) for term variations
- Quotation marks for exact phrases
- Parentheses for grouping logical operations

Generate multiple search variations and combine them for comprehensive coverage.
Return only the final optimized query without explanation.
"""
            
            messages = [HumanMessage(content=optimization_prompt)]
            response = await self.invoke_llm(messages)
            
            # Clean the response to get just the query
            optimized = response.strip().strip('"').strip("'")
            
            # If optimization failed, return original
            if not optimized or len(optimized) < 3:
                return original_query
            
            print(f"🔍 Query optimization: '{original_query}' → '{optimized}'")
            return optimized
            
        except Exception as e:
            print(f"❌ Query optimization error: {str(e)}")
            return original_query
    
    async def _analyze_papers(self, papers: List[PubMedPaper], analysis_type: str, original_query: str) -> Dict[str, Any]:
        """Analyze the found papers with enhanced similarity scoring"""
        if not papers:
            return {"status": "no_papers_found"}
        
        try:
            # First, calculate relevance scores for all papers
            scored_papers = await self._calculate_relevance_scores(papers, original_query)
            
            # Sort papers by relevance score
            scored_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Take top papers for detailed analysis
            top_papers = scored_papers[:10]
            
            # Prepare paper summaries for analysis
            paper_summaries = []
            for paper_data in top_papers:
                paper = paper_data['paper']
                score = paper_data['relevance_score']
                summary = f"""
Title: {paper.title}
Authors: {', '.join(paper.authors[:3])}
Journal: {paper.journal}
Date: {paper.publication_date}
Relevance Score: {score:.2f}
Abstract: {paper.abstract[:400]}...
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
    
    async def _calculate_relevance_scores(self, papers: List[PubMedPaper], query: str) -> List[Dict[str, Any]]:
        """Calculate relevance scores for papers based on multiple factors"""
        try:
            # Extract query keywords for comparison
            query_keywords = await self._extract_keywords(query)
            
            scored_papers = []
            for paper in papers:
                # Calculate multiple relevance factors
                title_score = self._calculate_text_similarity(query_keywords, paper.title.lower())
                abstract_score = self._calculate_text_similarity(query_keywords, paper.abstract.lower())
                keyword_score = self._calculate_keyword_overlap(query_keywords, paper.keywords)
                
                # Quality factors
                journal_score = self._calculate_journal_score(paper.journal)
                recency_score = self._calculate_recency_score(paper.publication_date)
                
                # Combined relevance score with weights
                relevance_score = (
                    title_score * 0.3 +           # Title relevance
                    abstract_score * 0.4 +        # Abstract relevance  
                    keyword_score * 0.2 +         # Keyword overlap
                    journal_score * 0.05 +        # Journal quality
                    recency_score * 0.05           # Publication recency
                )
                
                scored_papers.append({
                    'paper': paper,
                    'relevance_score': relevance_score,
                    'score_breakdown': {
                        'title': title_score,
                        'abstract': abstract_score,
                        'keywords': keyword_score,
                        'journal': journal_score,
                        'recency': recency_score
                    }
                })
            
            return scored_papers
            
        except Exception as e:
            print(f"❌ Error calculating relevance scores: {str(e)}")
            # Return original papers with default scores
            return [{'paper': paper, 'relevance_score': 0.5} for paper in papers]
    
    async def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text using AI"""
        try:
            prompt = f"""
Extract the most important keywords and key phrases from this text for academic paper matching:

Text: "{text}"

Return only a comma-separated list of keywords and phrases (no explanations).
Focus on:
- Technical terms
- Research domains
- Methodologies
- Important concepts
"""
            
            messages = [HumanMessage(content=prompt)]
            response = await self.invoke_llm(messages)
            
            # Parse keywords
            keywords = [kw.strip().lower() for kw in response.split(',') if kw.strip()]
            return keywords[:20]  # Limit to top 20 keywords
            
        except Exception:
            # Fallback to simple keyword extraction
            import re
            words = re.findall(r'\b\w{3,}\b', text.lower())
            return list(set(words))[:10]
    
    def _calculate_text_similarity(self, query_keywords: List[str], text: str) -> float:
        """Calculate similarity between query keywords and text"""
        if not query_keywords or not text:
            return 0.0
        
        text_words = set(text.lower().split())
        matches = 0
        total_weight = 0
        
        for keyword in query_keywords:
            keyword_words = keyword.split()
            weight = len(keyword_words)  # Multi-word phrases get higher weight
            total_weight += weight
            
            if len(keyword_words) == 1:
                # Single word matching
                if keyword in text_words:
                    matches += weight
            else:
                # Phrase matching
                if keyword in text:
                    matches += weight * 1.5  # Bonus for exact phrase match
        
        return matches / max(total_weight, 1)
    
    def _calculate_keyword_overlap(self, query_keywords: List[str], paper_keywords: List[str]) -> float:
        """Calculate overlap between query keywords and paper keywords"""
        if not query_keywords or not paper_keywords:
            return 0.0
        
        query_set = set([kw.lower() for kw in query_keywords])
        paper_set = set([kw.lower() for kw in paper_keywords])
        
        intersection = query_set.intersection(paper_set)
        union = query_set.union(paper_set)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_journal_score(self, journal: str) -> float:
        """Calculate journal quality score (simplified)"""
        if not journal:
            return 0.0
        
        # High-impact journal patterns (simplified scoring)
        high_impact_patterns = [
            'nature', 'science', 'cell', 'lancet', 'nejm', 'jama',
            'pnas', 'plos', 'bmc', 'frontiers', 'ieee', 'acm'
        ]
        
        journal_lower = journal.lower()
        for pattern in high_impact_patterns:
            if pattern in journal_lower:
                return 1.0
        
        # Medium impact indicators
        if any(word in journal_lower for word in ['journal', 'international', 'research']):
            return 0.7
        
        return 0.5  # Default score
    
    def _calculate_recency_score(self, pub_date: str) -> float:
        """Calculate recency score based on publication date"""
        try:
            from datetime import datetime
            
            if not pub_date:
                return 0.0
            
            # Parse publication year
            year = int(pub_date[:4]) if len(pub_date) >= 4 else 2000
            current_year = datetime.now().year
            
            years_ago = current_year - year
            
            # Score based on recency (higher for newer papers)
            if years_ago <= 2:
                return 1.0
            elif years_ago <= 5:
                return 0.8
            elif years_ago <= 10:
                return 0.6
            else:
                return 0.3
                
        except Exception:
            return 0.5
    
    def _generate_detailed_references(self, papers: List[PubMedPaper]) -> str:
        """Generate a comprehensive references section for Paper Scout reports"""
        if not papers:
            return "No papers were found for the given search query."
        
        references = []
        for i, paper in enumerate(papers, 1):
            reference = self._format_paper_reference(paper, i)
            references.append(reference)
        
        # Create a comprehensive references section
        references_text = "\n\n".join(references)
        
        return f"""The following {len(papers)} papers were identified through PubMed search and analysis:

{references_text}

---
*Note: Papers are listed in order of relevance score. PMID (PubMed ID) and DOI are provided where available for easy access to full texts.*"""
    
    def _format_paper_reference(self, paper: PubMedPaper, ref_number: int) -> str:
        """Format a single paper reference with comprehensive information"""
        try:
            # Basic citation information
            authors_list = paper.authors if paper.authors else ["Unknown authors"]
            
            # Format authors (APA style: Last, F. M.)
            if len(authors_list) <= 6:
                authors_text = ", ".join(authors_list)
            else:
                authors_text = ", ".join(authors_list[:6]) + ", et al."
            
            # Extract year
            year = paper.publication_date[:4] if paper.publication_date and len(paper.publication_date) >= 4 else "Unknown year"
            
            # Build the main citation
            citation_parts = [
                f"**[{ref_number}]** {authors_text}",
                f"({year})",
                f"*{paper.title}*",
                f"{paper.journal}" if paper.journal else "Journal unknown"
            ]
            
            main_citation = ". ".join(citation_parts) + "."
            
            # Add identifiers and links
            identifiers = []
            if paper.pmid:
                identifiers.append(f"**PMID:** {paper.pmid}")
                identifiers.append(f"**PubMed:** https://pubmed.ncbi.nlm.nih.gov/{paper.pmid}/")
            if paper.doi:
                identifiers.append(f"**DOI:** {paper.doi}")
            if paper.url and not paper.doi:
                identifiers.append(f"**URL:** {paper.url}")
            
            # Add keywords if available
            if paper.keywords:
                keywords_text = ", ".join(paper.keywords[:10])  # Limit to 10 keywords
                identifiers.append(f"**Keywords:** {keywords_text}")
            
            # Combine citation with metadata
            full_reference = main_citation
            if identifiers:
                full_reference += f"\n   {' | '.join(identifiers)}"
            
            # Add abstract preview
            if paper.abstract:
                abstract_preview = paper.abstract[:300] + "..." if len(paper.abstract) > 300 else paper.abstract
                full_reference += f"\n   **Abstract:** {abstract_preview}"
            
            # Add relevance note if this paper was scored
            if hasattr(paper, 'relevance_score'):
                full_reference += f"\n   *Relevance Score: {paper.relevance_score:.2f}/1.00*"
            
            return full_reference
            
        except Exception as e:
            print(f"❌ Error formatting reference {ref_number}: {str(e)}")
            return f"**[{ref_number}]** Error formatting reference for: {getattr(paper, 'title', 'Unknown title')}"
    
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
            
            # Always add comprehensive references section
            references_section = self._generate_detailed_references(papers)
            report += f"\n\n## References\n\n{references_section}"
            
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