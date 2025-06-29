"""
Google Scholar academic database interface implementation.
Provides scholarly paper search via web scraping with rate limiting and caching.
"""
import asyncio
import aiohttp
import re
from typing import Dict, List, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup
import json

from .database_interfaces import (
    DatabaseInterface, DatabaseType, SearchQuery, SearchResult, 
    PaperMetadata, SearchResultStatus, RateLimitAwareMixin, 
    CacheAwareMixin, RetryAwareMixin
)


class GoogleScholarService(DatabaseInterface, RateLimitAwareMixin, CacheAwareMixin, RetryAwareMixin):
    """Google Scholar database interface implementation."""
    
    def __init__(self):
        super().__init__("Google Scholar", DatabaseType.GOOGLE_SCHOLAR)
        self.base_url = "https://scholar.google.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        self.current_user_agent_index = 0
        
        # Rate limiting specific to Google Scholar
        self.requests_per_minute = 10  # Conservative to avoid blocking
        self.requests_per_hour = 200
        self.cache_ttl_seconds = 7200  # 2 hours for Scholar results
    
    async def initialize(self) -> bool:
        """Initialize the Google Scholar service with HTTP session."""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': self.user_agents[0],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
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
        """Test connection to Google Scholar."""
        try:
            url = f"{self.base_url}/scholar"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _rotate_user_agent(self) -> None:
        """Rotate user agent to avoid detection."""
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        if self.session:
            self.session.headers.update({
                'User-Agent': self.user_agents[self.current_user_agent_index]
            })
    
    async def search(self, query: SearchQuery) -> SearchResult:
        """Perform search on Google Scholar."""
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
            error_msg = f"Google Scholar search error: {str(e)}"
            print(f"❌ {error_msg}")
            
            return SearchResult(
                papers=[], query=query, database=self.database_type,
                status=SearchResultStatus.FAILED, total_found=0, 
                search_time=search_time, error_message=error_msg
            )
    
    async def _perform_search(self, query: SearchQuery) -> List[PaperMetadata]:
        """Perform the actual search operation."""
        papers = []
        
        # Build Scholar search URL
        params = {
            'q': query.query,
            'hl': 'en',
            'num': min(query.max_results, 20),  # Scholar limits per page
        }
        
        # Add date filtering if specified
        if query.years_back:
            current_year = datetime.now().year
            start_year = current_year - query.years_back
            params['as_ylo'] = start_year
            params['as_yhi'] = current_year
        elif query.start_date and query.end_date:
            params['as_ylo'] = query.start_date.year
            params['as_yhi'] = query.end_date.year
        
        url = f"{self.base_url}/scholar?" + urlencode(params)
        
        # Rotate user agent
        self._rotate_user_agent()
        
        async with self.session.get(url) as response:
            if response.status == 429:
                raise Exception("Rate limited by Google Scholar")
            elif response.status != 200:
                raise Exception(f"HTTP {response.status}: {response.reason}")
            
            html = await response.text()
            papers = self._parse_search_results(html)
        
        return papers[:query.max_results]
    
    def _parse_search_results(self, html: str) -> List[PaperMetadata]:
        """Parse Google Scholar search results HTML."""
        papers = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all result entries
        result_divs = soup.find_all('div', class_='gs_r gs_or gs_scl')
        
        for div in result_divs:
            try:
                paper = self._parse_single_result(div)
                if paper:
                    papers.append(paper)
            except Exception as e:
                print(f"⚠️ Error parsing Scholar result: {str(e)}")
                continue
        
        return papers
    
    def _parse_single_result(self, result_div) -> Optional[PaperMetadata]:
        """Parse a single search result entry."""
        try:
            # Extract title
            title_element = result_div.find('h3', class_='gs_rt')
            if not title_element:
                return None
            
            title_link = title_element.find('a')
            title = title_link.get_text().strip() if title_link else title_element.get_text().strip()
            url = title_link.get('href') if title_link else None
            
            # Extract authors and publication info
            authors = []
            journal = None
            pub_date = None
            
            author_element = result_div.find('div', class_='gs_a')
            if author_element:
                author_text = author_element.get_text()
                
                # Parse author information (format: "Author1, Author2 - Journal, Year - Publisher")
                parts = author_text.split(' - ')
                if parts:
                    # Extract authors (first part before first dash)
                    author_part = parts[0].strip()
                    authors = [author.strip() for author in author_part.split(',')]
                
                if len(parts) > 1:
                    # Extract journal and year
                    pub_info = parts[1].strip()
                    
                    # Try to extract year
                    year_match = re.search(r'\b(19|20)\d{2}\b', pub_info)
                    if year_match:
                        try:
                            year = int(year_match.group())
                            pub_date = datetime(year, 1, 1)
                        except ValueError:
                            pass
                    
                    # Extract journal (remove year and clean up)
                    journal = re.sub(r'\b(19|20)\d{2}\b', '', pub_info).strip()
                    journal = re.sub(r'^,\s*|\s*,$', '', journal)  # Remove leading/trailing commas
            
            # Extract abstract/snippet
            abstract = None
            snippet_element = result_div.find('div', class_='gs_rs')
            if snippet_element:
                abstract = snippet_element.get_text().strip()
            
            # Extract citation count
            citation_count = None
            citation_element = result_div.find('a', string=re.compile(r'Cited by \d+'))
            if citation_element:
                citation_match = re.search(r'Cited by (\d+)', citation_element.get_text())
                if citation_match:
                    citation_count = int(citation_match.group(1))
            
            # Try to extract DOI from links
            doi = None
            links = result_div.find_all('a')
            for link in links:
                href = link.get('href', '')
                if 'doi.org' in href:
                    doi_match = re.search(r'doi\.org/(.+)', href)
                    if doi_match:
                        doi = doi_match.group(1)
                        break
            
            return PaperMetadata(
                title=title,
                authors=authors,
                abstract=abstract,
                publication_date=pub_date,
                journal=journal,
                doi=doi,
                url=url,
                citation_count=citation_count,
                database_source=DatabaseType.GOOGLE_SCHOLAR,
                confidence_score=0.8,  # Base confidence for Scholar results
                relevance_score=0.0,   # Will be calculated later
                tags=['google_scholar']
            )
            
        except Exception as e:
            print(f"⚠️ Error parsing single Scholar result: {str(e)}")
            return None
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperMetadata]:
        """Get a specific paper by its Google Scholar ID or URL."""
        # Google Scholar doesn't have stable IDs, so we'll search by title if provided
        cache_key = self._get_cache_key("get_paper", paper_id)
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            # If paper_id looks like a URL, try to fetch it directly
            if paper_id.startswith('http'):
                await self.wait_for_rate_limit()
                self.record_request()
                
                async with self.session.get(paper_id) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Parse the paper page (implementation would be more complex)
                        return None  # Placeholder
            
            # Otherwise, treat as title and search
            query = SearchQuery(query=paper_id, max_results=1)
            result = await self.search(query)
            
            if result.papers:
                paper = result.papers[0]
                self._set_cache(cache_key, paper)
                return paper
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting paper by ID: {str(e)}")
            return None
    
    async def get_citations(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers that cite the given paper."""
        # Implementation would require parsing Scholar's "Cited by" pages
        # This is a placeholder for the complex citation parsing logic
        return []
    
    async def get_references(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers referenced by the given paper."""
        # Google Scholar doesn't easily provide reference lists
        return []
    
    def validate_query(self, query: SearchQuery) -> tuple[bool, Optional[str]]:
        """Validate if the query is compatible with Google Scholar."""
        if not query.query or not query.query.strip():
            return False, "Query cannot be empty"
        
        if query.max_results > 1000:
            return False, "Maximum results should be <= 1000 for Scholar"
        
        # Scholar has limitations on complex queries
        if len(query.query) > 256:
            return False, "Query too long (max 256 characters)"
        
        return True, None
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None


# Service instance
google_scholar_service = GoogleScholarService()