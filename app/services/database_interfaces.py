"""
Database interfaces for academic paper search systems.
Provides abstract base classes and protocols for different academic databases.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio


class DatabaseType(Enum):
    """Enumeration of supported academic databases."""
    PUBMED = "pubmed"
    GOOGLE_SCHOLAR = "google_scholar"
    ARXIV = "arxiv"
    IEEE = "ieee"
    ACM = "acm"
    SEMANTIC_SCHOLAR = "semantic_scholar"


class SearchResultStatus(Enum):
    """Status of search results."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class PaperMetadata:
    """Standardized paper metadata across all databases."""
    title: str
    authors: List[str]
    abstract: Optional[str] = None
    publication_date: Optional[datetime] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None  # PubMed ID
    arxiv_id: Optional[str] = None  # arXiv ID
    ieee_id: Optional[str] = None  # IEEE Xplore ID
    acm_id: Optional[str] = None  # ACM DL ID
    semantic_scholar_id: Optional[str] = None
    url: Optional[str] = None
    citation_count: Optional[int] = None
    database_source: DatabaseType = None
    confidence_score: float = 0.0
    relevance_score: float = 0.0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class SearchQuery:
    """Standardized search query structure."""
    query: str
    max_results: int = 50
    years_back: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    filters: Dict[str, Any] = None
    sort_by: str = "relevance"  # relevance, date, citation_count
    include_abstracts: bool = True
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


@dataclass
class SearchResult:
    """Standardized search result container."""
    papers: List[PaperMetadata]
    query: SearchQuery
    database: DatabaseType
    status: SearchResultStatus
    total_found: int
    search_time: float
    error_message: Optional[str] = None
    rate_limit_info: Optional[Dict[str, Any]] = None
    next_page_token: Optional[str] = None


class DatabaseInterface(ABC):
    """Abstract base class for all academic database interfaces."""
    
    def __init__(self, name: str, database_type: DatabaseType):
        self.name = name
        self.database_type = database_type
        self.is_initialized = False
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the database connection and authentication."""
        pass
    
    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResult:
        """Perform a search query and return standardized results."""
        pass
    
    @abstractmethod
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperMetadata]:
        """Retrieve a specific paper by its database-specific ID."""
        pass
    
    @abstractmethod
    async def get_citations(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers that cite the given paper."""
        pass
    
    @abstractmethod
    async def get_references(self, paper_id: str) -> List[PaperMetadata]:
        """Get papers referenced by the given paper."""
        pass
    
    @abstractmethod
    def validate_query(self, query: SearchQuery) -> tuple[bool, Optional[str]]:
        """Validate if the query is compatible with this database."""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health and availability of the database."""
        return {
            "database": self.name,
            "type": self.database_type.value,
            "initialized": self.is_initialized,
            "rate_limit_remaining": self.rate_limit_remaining,
            "rate_limit_reset": self.rate_limit_reset,
            "timestamp": datetime.now().isoformat()
        }


class RateLimitAwareMixin:
    """Mixin for database interfaces that need rate limiting."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests_per_minute = 60
        self.requests_per_hour = 1000
        self.request_history: List[datetime] = []
    
    async def wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        
        # Clean old requests (older than 1 hour)
        self.request_history = [
            req_time for req_time in self.request_history 
            if (now - req_time).total_seconds() < 3600
        ]
        
        # Check hourly limit
        if len(self.request_history) >= self.requests_per_hour:
            oldest_request = min(self.request_history)
            wait_time = 3600 - (now - oldest_request).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return
        
        # Check per-minute limit
        recent_requests = [
            req_time for req_time in self.request_history 
            if (now - req_time).total_seconds() < 60
        ]
        
        if len(recent_requests) >= self.requests_per_minute:
            oldest_recent = min(recent_requests)
            wait_time = 60 - (now - oldest_recent).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    def record_request(self) -> None:
        """Record a request for rate limiting purposes."""
        self.request_history.append(datetime.now())


class CacheAwareMixin:
    """Mixin for database interfaces with caching capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.cache_ttl_seconds = 3600  # 1 hour default
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate a cache key for the given method and parameters."""
        import hashlib
        key_data = f"{method}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from cache if not expired."""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl_seconds:
                return data
            else:
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache with current timestamp."""
        self.cache[cache_key] = (data, datetime.now())
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()


class RetryAwareMixin:
    """Mixin for database interfaces with retry capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = 3
        self.retry_delay = 1.0
        self.backoff_factor = 2.0
    
    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                # Exponential backoff
                delay = self.retry_delay * (self.backoff_factor ** attempt)
                await asyncio.sleep(delay)
        
        raise last_exception


class DatabaseRegistry:
    """Registry for managing multiple database interfaces."""
    
    def __init__(self):
        self._databases: Dict[DatabaseType, DatabaseInterface] = {}
        self._initialized_databases: set[DatabaseType] = set()
    
    def register(self, database: DatabaseInterface) -> None:
        """Register a database interface."""
        self._databases[database.database_type] = database
    
    def unregister(self, database_type: DatabaseType) -> None:
        """Unregister a database interface."""
        if database_type in self._databases:
            del self._databases[database_type]
            self._initialized_databases.discard(database_type)
    
    async def initialize_all(self) -> Dict[DatabaseType, bool]:
        """Initialize all registered databases."""
        results = {}
        
        for db_type, database in self._databases.items():
            try:
                success = await database.initialize()
                results[db_type] = success
                if success:
                    self._initialized_databases.add(db_type)
            except Exception as e:
                print(f"Failed to initialize {db_type.value}: {str(e)}")
                results[db_type] = False
        
        return results
    
    def get_database(self, database_type: DatabaseType) -> Optional[DatabaseInterface]:
        """Get a database interface by type."""
        return self._databases.get(database_type)
    
    def get_available_databases(self) -> List[DatabaseType]:
        """Get list of available (registered and initialized) databases."""
        return [
            db_type for db_type in self._databases.keys() 
            if db_type in self._initialized_databases
        ]
    
    async def health_check_all(self) -> Dict[DatabaseType, Dict[str, Any]]:
        """Perform health check on all databases."""
        results = {}
        
        for db_type, database in self._databases.items():
            try:
                results[db_type] = await database.health_check()
            except Exception as e:
                results[db_type] = {
                    "database": database.name,
                    "type": db_type.value,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        return results


# Global database registry instance
database_registry = DatabaseRegistry()