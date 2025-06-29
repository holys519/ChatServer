"""
arXiv academic database interface implementation.
Provides preprint paper search via arXiv API with proper rate limiting and caching.
"""
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
import re

from .database_interfaces import (
    DatabaseInterface, DatabaseType, SearchQuery, SearchResult, 
    PaperMetadata, SearchResultStatus, RateLimitAwareMixin, 
    CacheAwareMixin, RetryAwareMixin
)


class ArxivService(DatabaseInterface, RateLimitAwareMixin, CacheAwareMixin, RetryAwareMixin):
    """arXiv database interface implementation."""
    
    def __init__(self):
        super().__init__("arXiv", DatabaseType.ARXIV)
        self.base_url = "http://export.arxiv.org/api/query"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # arXiv specific rate limiting (3 seconds between requests recommended)
        self.requests_per_minute = 20
        self.requests_per_hour = 1000
        self.min_request_interval = 3.0  # seconds
        self.last_request_time = None
        
        # Cache for 6 hours as arXiv data is relatively stable
        self.cache_ttl_seconds = 21600
        
        # arXiv subject categories mapping
        self.subject_categories = {
            'computer_science': ['cs.AI', 'cs.CL', 'cs.CV', 'cs.LG', 'cs.NE'],
            'physics': ['physics.med-ph', 'physics.bio-ph', 'cond-mat'],
            'mathematics': ['math.ST', 'math.PR', 'math.OC'],
            'biology': ['q-bio.BM', 'q-bio.GN', 'q-bio.MN'],
            'economics': ['econ.EM', 'econ.TH'],
            'statistics': ['stat.AP', 'stat.ML', 'stat.ME']
        }
    
    async def initialize(self) -> bool:
        """Initialize the arXiv service with HTTP session."""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': 'Academic Research Bot (arxiv-api-client)',
                    'Accept': 'application/atom+xml',
                }
            )
            
            # Test connection with a simple query
            test_result = await self._test_connection()
            self.is_initialized = test_result
            
            if self.is_initialized:
                print(f"✅ {self.name} service initialized successfully")
            else:
                print(f"❌ {self.name} service initialization failed")
            
            return self.is_initialized
            
        except Exception as e:
            print(f"❌ Error initializing {self.name}: {str(e)}")
            self.is_initialized = False
            return False
    
    async def _test_connection(self) -> bool:
        """Test connection to arXiv API."""
        try:
            params = {
                'search_query': 'cat:cs.AI',
                'max_results': 1
            }
            url = f"{self.base_url}?" + urlencode(params)
            
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def _wait_for_rate_limit(self) -> None:
        """Enhanced rate limiting with minimum interval between requests."""
        # First apply the standard rate limiting
        await super().wait_for_rate_limit()
        
        # Then apply arXiv-specific minimum interval
        if self.last_request_time:
            time_since_last = (datetime.now() - self.last_request_time).total_seconds()
            if time_since_last < self.min_request_interval:
                wait_time = self.min_request_interval - time_since_last
                await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
    
    async def search(self, query: SearchQuery) -> SearchResult:
        """Perform search on arXiv."""
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
            await self._wait_for_rate_limit()
            self.record_request()
            
            papers = await self.execute_with_retry(self._perform_search, query)
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            result = SearchResult(
                papers=papers,
                query=query,
                database=self.database_type,
                status=SearchResultStatus.SUCCESS if papers else SearchResultStatus.PARTIAL,
                total_found=len(papers),
                search_time=search_time
            )
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            search_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"arXiv search error: {str(e)}"
            print(f"❌ {error_msg}")
            
            return SearchResult(
                papers=[], query=query, database=self.database_type,
                status=SearchResultStatus.FAILED, total_found=0, 
                search_time=search_time, error_message=error_msg
            )
    
    async def _perform_search(self, query: SearchQuery) -> List[PaperMetadata]:
        """Perform the actual search operation."""
        # Build arXiv search query
        search_query = self._build_arxiv_query(query)
        
        params = {
            'search_query': search_query,
            'max_results': min(query.max_results, 2000),  # arXiv API limit
            'sortBy': 'relevance' if query.sort_by == 'relevance' else 'submittedDate',
            'sortOrder': 'descending'
        }
        
        url = f"{self.base_url}?" + urlencode(params)
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}: {response.reason}")
            
            xml_content = await response.text()
            papers = self._parse_arxiv_response(xml_content)
            
            # Apply date filtering if needed
            if query.years_back or (query.start_date and query.end_date):
                papers = self._filter_by_date(papers, query)
        
        return papers[:query.max_results]
    
    def _build_arxiv_query(self, query: SearchQuery) -> str:
        """Build arXiv-specific search query."""
        search_terms = []
        
        # Add main query terms
        if query.query:
            # Escape special characters and build query
            escaped_query = query.query.replace('"', '\\"')
            search_terms.append(f'all:"{escaped_query}"')
        
        # Add category filters from query filters
        if query.filters and 'categories' in query.filters:
            categories = query.filters['categories']
            if isinstance(categories, str):
                categories = [categories]
            
            for category in categories:
                search_terms.append(f'cat:{category}')
        
        # Add subject area filters if specified
        if query.filters and 'subject_area' in query.filters:
            subject_area = query.filters['subject_area']
            if subject_area in self.subject_categories:
                cats = self.subject_categories[subject_area]
                cat_query = ' OR '.join([f'cat:{cat}' for cat in cats])
                search_terms.append(f'({cat_query})')
        
        # Combine all search terms
        if search_terms:
            return ' AND '.join(search_terms)
        else:
            return 'all:*'  # Search everything if no specific terms
    
    def _filter_by_date(self, papers: List[PaperMetadata], query: SearchQuery) -> List[PaperMetadata]:
        """Filter papers by date range."""
        if not papers:
            return papers
        
        filtered_papers = []
        current_date = datetime.now()
        
        for paper in papers:
            if not paper.publication_date:
                continue
            
            include_paper = True
            
            if query.years_back:
                cutoff_date = current_date - timedelta(days=query.years_back * 365)
                include_paper = paper.publication_date >= cutoff_date
            
            if query.start_date and query.end_date:
                include_paper = (query.start_date <= paper.publication_date <= query.end_date)
            
            if include_paper:
                filtered_papers.append(paper)
        
        return filtered_papers
    
    def _parse_arxiv_response(self, xml_content: str) -> List[PaperMetadata]:
        """Parse arXiv API XML response."""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # arXiv uses Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom',
                  'arxiv': 'http://arxiv.org/schemas/atom'}
            
            entries = root.findall('atom:entry', ns)
            
            for entry in entries:
                try:
                    paper = self._parse_arxiv_entry(entry, ns)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    print(f"⚠️ Error parsing arXiv entry: {str(e)}")
                    continue
            
        except ET.ParseError as e:
            print(f"❌ XML parsing error: {str(e)}")
        
        return papers
    
    def _parse_arxiv_entry(self, entry, namespaces) -> Optional[PaperMetadata]:
        """Parse a single arXiv entry."""
        try:
            # Extract arXiv ID
            arxiv_id = None
            id_element = entry.find('atom:id', namespaces)
            if id_element is not None:
                arxiv_url = id_element.text
                # Extract ID from URL like http://arxiv.org/abs/2301.00001v1
                arxiv_match = re.search(r'arxiv\.org/abs/([^v]+)', arxiv_url)
                if arxiv_match:
                    arxiv_id = arxiv_match.group(1)
            
            # Extract title
            title_element = entry.find('atom:title', namespaces)
            title = title_element.text.strip() if title_element is not None else "No title"
            
            # Extract authors
            authors = []
            author_elements = entry.findall('atom:author', namespaces)
            for author_elem in author_elements:
                name_elem = author_elem.find('atom:name', namespaces)
                if name_elem is not None:
                    authors.append(name_elem.text.strip())
            
            # Extract abstract
            abstract = None
            summary_element = entry.find('atom:summary', namespaces)
            if summary_element is not None:
                abstract = summary_element.text.strip()
            
            # Extract publication date
            pub_date = None
            published_element = entry.find('atom:published', namespaces)
            if published_element is not None:
                try:
                    # arXiv dates are in format: 2023-01-01T12:00:00Z
                    date_str = published_element.text
                    pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            # Extract categories
            categories = []
            category_elements = entry.findall('atom:category', namespaces)
            for cat_elem in category_elements:
                term = cat_elem.get('term')
                if term:
                    categories.append(term)
            
            # Extract DOI if available
            doi = None
            doi_element = entry.find('arxiv:doi', namespaces)
            if doi_element is not None:
                doi = doi_element.text.strip()
            
            # Build URL
            url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None
            
            # Extract journal reference if available
            journal = None
            journal_element = entry.find('arxiv:journal_ref', namespaces)
            if journal_element is not None:
                journal = journal_element.text.strip()
            
            return PaperMetadata(
                title=title,
                authors=authors,
                abstract=abstract,
                publication_date=pub_date,
                journal=journal,
                doi=doi,
                arxiv_id=arxiv_id,
                url=url,
                database_source=DatabaseType.ARXIV,
                confidence_score=0.9,  # High confidence for arXiv data
                relevance_score=0.0,   # Will be calculated later
                tags=['arxiv', 'preprint'] + categories
            )
            
        except Exception as e:
            print(f"⚠️ Error parsing arXiv entry: {str(e)}")
            return None
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperMetadata]:
        """Get a specific paper by its arXiv ID."""
        cache_key = self._get_cache_key("get_paper", paper_id)
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            await self._wait_for_rate_limit()
            self.record_request()
            
            # Query by arXiv ID
            params = {
                'id_list': paper_id,
                'max_results': 1
            }
            
            url = f"{self.base_url}?" + urlencode(params)
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                xml_content = await response.text()
                papers = self._parse_arxiv_response(xml_content)
                
                if papers:
                    paper = papers[0]
                    self._set_cache(cache_key, paper)
                    return paper
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting paper by ID: {str(e)}")
            return None
    
    async def get_citations(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers that cite the given paper."""
        # arXiv doesn't provide citation data directly
        # This would require integration with other services like Semantic Scholar
        return []
    
    async def get_references(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers referenced by the given paper."""
        # arXiv doesn't provide reference lists via API
        return []
    
    def validate_query(self, query: SearchQuery) -> tuple[bool, Optional[str]]:
        """Validate if the query is compatible with arXiv."""
        if not query.query or not query.query.strip():
            return False, "Query cannot be empty"
        
        if query.max_results > 2000:
            return False, "Maximum results should be <= 2000 for arXiv"
        
        # Validate category filters if present
        if query.filters and 'categories' in query.filters:
            categories = query.filters['categories']
            if isinstance(categories, str):
                categories = [categories]
            
            # Basic validation for arXiv category format
            for cat in categories:
                if not re.match(r'^[a-z-]+\.[A-Z]{2,3}$', cat):
                    return False, f"Invalid arXiv category format: {cat}"
        
        return True, None
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None


# Service instance
arxiv_service = ArxivService()