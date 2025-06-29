"""
PubMed Adapter for Database Interface compatibility.
Adapts the existing PubMed service to work with the new database interface system.
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .database_interfaces import (
    DatabaseInterface, DatabaseType, SearchQuery, SearchResult, 
    PaperMetadata, SearchResultStatus, RateLimitAwareMixin, 
    CacheAwareMixin, RetryAwareMixin
)
from .pubmed_service import pubmed_service


class PubMedAdapter(DatabaseInterface, RateLimitAwareMixin, CacheAwareMixin, RetryAwareMixin):
    """
    Adapter that wraps the existing PubMed service to conform to the DatabaseInterface.
    """
    
    def __init__(self):
        super().__init__("PubMed", DatabaseType.PUBMED)
        self.pubmed_service = pubmed_service
        
        # PubMed rate limiting (NCBI guidelines: 3 requests per second max)
        self.requests_per_minute = 180  # 3 per second * 60 seconds
        self.requests_per_hour = 10800  # Conservative limit
        self.cache_ttl_seconds = 3600   # 1 hour cache for PubMed results
    
    async def initialize(self) -> bool:
        """Initialize the PubMed adapter."""
        try:
            # The existing PubMed service should already be initialized
            self.is_initialized = True
            print(f"✅ {self.name} adapter initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Error initializing {self.name} adapter: {str(e)}")
            self.is_initialized = False
            return False
    
    async def search(self, query: SearchQuery) -> SearchResult:
        """Perform search using the existing PubMed service."""
        cache_key = self._get_cache_key("search", query.query, query.max_results, query.years_back)
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            return cached_result
        
        if not self.is_initialized:
            return SearchResult(
                papers=[], query=query, database=self.database_type,
                status=SearchResultStatus.FAILED, total_found=0, search_time=0.0,
                error_message="Service not initialized"
            )
        
        start_time = datetime.now()
        
        try:
            await self.wait_for_rate_limit()
            self.record_request()
            
            # Convert SearchQuery to PubMed service parameters
            pubmed_params = self._convert_query_to_pubmed_params(query)
            
            # Call the existing PubMed service
            papers = await self.execute_with_retry(
                self.pubmed_service.search_papers, **pubmed_params
            )
            
            # Convert PubMed results to standardized format
            standardized_papers = self._convert_pubmed_results(papers)
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            result = SearchResult(
                papers=standardized_papers,
                query=query,
                database=self.database_type,
                status=SearchResultStatus.SUCCESS if standardized_papers else SearchResultStatus.PARTIAL,
                total_found=len(standardized_papers),
                search_time=search_time
            )
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            search_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"PubMed search error: {str(e)}"
            print(f"❌ {error_msg}")
            
            return SearchResult(
                papers=[], query=query, database=self.database_type,
                status=SearchResultStatus.FAILED, total_found=0, 
                search_time=search_time, error_message=error_msg
            )
    
    def _convert_query_to_pubmed_params(self, query: SearchQuery) -> Dict[str, Any]:
        """Convert SearchQuery to parameters for the existing PubMed service."""
        params = {
            'query': query.query,
            'max_results': query.max_results,
            'include_abstracts': query.include_abstracts
        }
        
        # Add date filtering
        if query.years_back:
            params['years_back'] = query.years_back
        elif query.start_date and query.end_date:
            # Convert to years for the existing service
            start_year = query.start_date.year
            end_year = query.end_date.year
            current_year = datetime.now().year
            params['years_back'] = current_year - start_year
        
        # Add filters if supported by the existing service
        if query.filters:
            # Map common filters to PubMed service parameters
            if 'include_mesh' in query.filters:
                params['include_mesh'] = query.filters['include_mesh']
            if 'study_types' in query.filters:
                params['study_types'] = query.filters['study_types']
        
        return params
    
    def _convert_pubmed_results(self, pubmed_papers: List[Dict[str, Any]]) -> List[PaperMetadata]:
        """Convert PubMed service results to standardized PaperMetadata."""
        standardized_papers = []
        
        for paper_dict in pubmed_papers:
            try:
                # Parse publication date
                pub_date = None
                if 'publication_date' in paper_dict and paper_dict['publication_date']:
                    try:
                        pub_date = datetime.fromisoformat(paper_dict['publication_date'])
                    except (ValueError, TypeError):
                        pass
                
                # Create standardized paper metadata
                paper = PaperMetadata(
                    title=paper_dict.get('title', ''),
                    authors=paper_dict.get('authors', []),
                    abstract=paper_dict.get('abstract'),
                    publication_date=pub_date,
                    journal=paper_dict.get('journal'),
                    doi=paper_dict.get('doi'),
                    pmid=paper_dict.get('pmid'),
                    url=paper_dict.get('url'),
                    citation_count=paper_dict.get('citation_count'),
                    database_source=DatabaseType.PUBMED,
                    confidence_score=paper_dict.get('relevance_score', 0.8),  # Default confidence
                    relevance_score=paper_dict.get('relevance_score', 0.0),
                    tags=paper_dict.get('tags', ['pubmed'])
                )
                
                standardized_papers.append(paper)
                
            except Exception as e:
                print(f"⚠️ Error converting PubMed paper: {str(e)}")
                continue
        
        return standardized_papers
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperMetadata]:
        """Get a specific paper by PMID."""
        cache_key = self._get_cache_key("get_paper", paper_id)
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            await self.wait_for_rate_limit()
            self.record_request()
            
            # Use the existing PubMed service to get paper by PMID
            # This assumes the service has a method to get by ID
            if hasattr(self.pubmed_service, 'get_paper_by_pmid'):
                paper_dict = await self.pubmed_service.get_paper_by_pmid(paper_id)
                if paper_dict:
                    papers = self._convert_pubmed_results([paper_dict])
                    if papers:
                        paper = papers[0]
                        self._set_cache(cache_key, paper)
                        return paper
            
            # Fallback: search by PMID
            search_result = await self.search(SearchQuery(query=f'pmid:{paper_id}', max_results=1))
            if search_result.papers:
                paper = search_result.papers[0]
                self._set_cache(cache_key, paper)
                return paper
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting paper by ID: {str(e)}")
            return None
    
    async def get_citations(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers that cite the given paper."""
        # PubMed doesn't directly provide citation data
        # This would require integration with other services
        return []
    
    async def get_references(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers referenced by the given paper."""
        # PubMed provides some reference data, but it's limited
        return []
    
    def validate_query(self, query: SearchQuery) -> tuple[bool, Optional[str]]:
        """Validate if the query is compatible with PubMed."""
        if not query.query or not query.query.strip():
            return False, "Query cannot be empty"
        
        if query.max_results > 10000:
            return False, "Maximum results should be <= 10000 for PubMed"
        
        # PubMed has specific query syntax requirements
        if len(query.query) > 4000:
            return False, "Query too long (max 4000 characters for PubMed)"
        
        return True, None


# Create adapter instance
pubmed_adapter = PubMedAdapter()