"""
PubMed integration service for CRA-Copilot
Provides tools for searching and retrieving research papers from PubMed
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, NamedTuple
from datetime import datetime, timedelta
from urllib.parse import quote
import re

class PubMedPaper(NamedTuple):
    """Structure for PubMed paper information"""
    pmid: str
    title: str
    authors: List[str]
    abstract: str
    journal: str
    publication_date: str
    doi: Optional[str]
    keywords: List[str]
    citation_count: int
    url: str

class PubMedService:
    """Service for interacting with PubMed API"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.tool_name = "CRA-Copilot"
        self.email = "cra-copilot@research.ai"  # Should be configurable
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def search_papers(
        self,
        query: str,
        max_results: int = 20,
        years_back: int = 5,
        include_abstracts: bool = True,
        sort: str = "relevance"
    ) -> List[PubMedPaper]:
        """
        Search for papers in PubMed
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            years_back: How many years back to search
            include_abstracts: Whether to fetch abstracts
            sort: Sort order (relevance, date, citation_count)
        
        Returns:
            List of PubMedPaper objects
        """
        try:
            print(f"🔍 Searching PubMed for: '{query}'")
            
            # Step 1: Search for PMIDs
            pmids = await self._search_pmids(query, max_results, years_back)
            
            if not pmids:
                print("📭 No papers found")
                return []
            
            print(f"📚 Found {len(pmids)} papers, fetching details...")
            
            # Step 2: Fetch paper details
            papers = await self._fetch_paper_details(pmids, include_abstracts)
            
            # Step 3: Sort results
            if sort == "date":
                papers.sort(key=lambda p: p.publication_date, reverse=True)
            elif sort == "citation_count":
                papers.sort(key=lambda p: p.citation_count, reverse=True)
            # Default is relevance order from PubMed
            
            print(f"✅ Retrieved {len(papers)} papers successfully")
            return papers
            
        except Exception as e:
            print(f"❌ Error searching PubMed: {str(e)}")
            return []
    
    async def _search_pmids(self, query: str, max_results: int, years_back: int) -> List[str]:
        """Search for PMIDs using ESearch"""
        try:
            session = await self._get_session()
            
            # Build date filter
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)
            date_filter = f"{start_date.year}/{start_date.month:02d}/{start_date.day:02d}:{end_date.year}/{end_date.month:02d}/{end_date.day:02d}[pdat]"
            
            # Combine query with date filter
            full_query = f"({query}) AND {date_filter}"
            
            # ESearch parameters
            params = {
                'db': 'pubmed',
                'term': full_query,
                'retmax': max_results,
                'retmode': 'xml',
                'tool': self.tool_name,
                'email': self.email,
                'sort': 'relevance'
            }
            
            url = f"{self.base_url}/esearch.fcgi"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"ESearch API error: {response.status}")
                
                xml_data = await response.text()
                root = ET.fromstring(xml_data)
                
                # Extract PMIDs
                pmids = []
                id_list = root.find('.//IdList')
                if id_list is not None:
                    for id_elem in id_list.findall('Id'):
                        pmids.append(id_elem.text)
                
                return pmids
                
        except Exception as e:
            print(f"❌ Error in ESearch: {str(e)}")
            return []
    
    async def _fetch_paper_details(self, pmids: List[str], include_abstracts: bool) -> List[PubMedPaper]:
        """Fetch detailed paper information using EFetch"""
        try:
            session = await self._get_session()
            
            # Process in batches to avoid overwhelming the API
            batch_size = 20
            all_papers = []
            
            for i in range(0, len(pmids), batch_size):
                batch_pmids = pmids[i:i + batch_size]
                
                # EFetch parameters
                params = {
                    'db': 'pubmed',
                    'id': ','.join(batch_pmids),
                    'retmode': 'xml',
                    'tool': self.tool_name,
                    'email': self.email
                }
                
                url = f"{self.base_url}/efetch.fcgi"
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"⚠️ EFetch API error for batch: {response.status}")
                        continue
                    
                    xml_data = await response.text()
                    papers = self._parse_pubmed_xml(xml_data, include_abstracts)
                    all_papers.extend(papers)
                
                # Be nice to the API
                await asyncio.sleep(0.5)
            
            return all_papers
            
        except Exception as e:
            print(f"❌ Error in EFetch: {str(e)}")
            return []
    
    def _parse_pubmed_xml(self, xml_data: str, include_abstracts: bool) -> List[PubMedPaper]:
        """Parse PubMed XML response"""
        papers = []
        
        try:
            root = ET.fromstring(xml_data)
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    paper = self._extract_paper_info(article, include_abstracts)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    print(f"⚠️ Error parsing individual paper: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"❌ Error parsing PubMed XML: {str(e)}")
        
        return papers
    
    def _extract_paper_info(self, article_elem, include_abstracts: bool) -> Optional[PubMedPaper]:
        """Extract paper information from XML element"""
        try:
            # PMID
            pmid_elem = article_elem.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # Title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ""
            title = self._clean_text(title)
            
            # Authors
            authors = []
            author_list = article_elem.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('Author'):
                    last_name = author.find('LastName')
                    first_name = author.find('ForeName')
                    if last_name is not None and first_name is not None:
                        authors.append(f"{first_name.text} {last_name.text}")
                    elif last_name is not None:
                        authors.append(last_name.text)
            
            # Abstract
            abstract = ""
            if include_abstracts:
                abstract_elem = article_elem.find('.//Abstract/AbstractText')
                if abstract_elem is not None:
                    abstract = abstract_elem.text or ""
                    abstract = self._clean_text(abstract)
            
            # Journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Publication date
            pub_date = self._extract_publication_date(article_elem)
            
            # DOI
            doi = self._extract_doi(article_elem)
            
            # Keywords (simplified extraction)
            keywords = self._extract_keywords(article_elem, title, abstract)
            
            # URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            # Citation count (placeholder - would need additional API calls)
            citation_count = 0
            
            return PubMedPaper(
                pmid=pmid,
                title=title,
                authors=authors,
                abstract=abstract,
                journal=journal,
                publication_date=pub_date,
                doi=doi,
                keywords=keywords,
                citation_count=citation_count,
                url=url
            )
            
        except Exception as e:
            print(f"❌ Error extracting paper info: {str(e)}")
            return None
    
    def _extract_publication_date(self, article_elem) -> str:
        """Extract publication date from article"""
        try:
            # Try PubDate first
            pub_date = article_elem.find('.//PubDate')
            if pub_date is not None:
                year = pub_date.find('Year')
                month = pub_date.find('Month')
                day = pub_date.find('Day')
                
                if year is not None:
                    date_parts = [year.text]
                    if month is not None:
                        date_parts.append(month.text)
                        if day is not None:
                            date_parts.append(day.text)
                    return "-".join(date_parts)
            
            # Fallback to ArticleDate
            article_date = article_elem.find('.//ArticleDate')
            if article_date is not None:
                year = article_date.find('Year')
                month = article_date.find('Month')
                day = article_date.find('Day')
                
                if year is not None:
                    date_parts = [year.text]
                    if month is not None:
                        date_parts.append(month.text.zfill(2))
                        if day is not None:
                            date_parts.append(day.text.zfill(2))
                    return "-".join(date_parts)
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_doi(self, article_elem) -> Optional[str]:
        """Extract DOI from article"""
        try:
            # Look for DOI in ArticleIdList
            id_list = article_elem.find('.//ArticleIdList')
            if id_list is not None:
                for article_id in id_list.findall('ArticleId'):
                    id_type = article_id.get('IdType')
                    if id_type == 'doi':
                        return article_id.text
            return None
            
        except Exception:
            return None
    
    def _extract_keywords(self, article_elem, title: str, abstract: str) -> List[str]:
        """Extract keywords from various sources"""
        keywords = []
        
        try:
            # Try to find MeSH terms
            mesh_list = article_elem.find('.//MeshHeadingList')
            if mesh_list is not None:
                for mesh_heading in mesh_list.findall('MeshHeading'):
                    descriptor = mesh_heading.find('DescriptorName')
                    if descriptor is not None:
                        keywords.append(descriptor.text)
            
            # If no MeSH terms, extract from title/abstract
            if not keywords:
                keywords = self._extract_keywords_from_text(title + " " + abstract)
            
            return keywords[:10]  # Limit to 10 keywords
            
        except Exception:
            return []
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Simple keyword extraction from text"""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'will', 'would', 'could', 'should', 'this', 'that', 
            'these', 'those', 'we', 'they', 'our', 'their'
        }
        
        # Extract words (letters only, 4+ characters)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Filter and count
        from collections import Counter
        filtered_words = [word for word in words if word not in stop_words]
        word_counts = Counter(filtered_words)
        
        # Return top keywords
        return [word for word, count in word_counts.most_common(10)]
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace and special characters"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special XML characters
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        return text.strip()
    
    async def get_paper_by_pmid(self, pmid: str, include_abstract: bool = True) -> Optional[PubMedPaper]:
        """Get a specific paper by PMID"""
        papers = await self._fetch_paper_details([pmid], include_abstract)
        return papers[0] if papers else None
    
    def format_papers_for_display(self, papers: List[PubMedPaper], include_abstracts: bool = False) -> str:
        """Format papers for display"""
        if not papers:
            return "No papers found."
        
        formatted_papers = []
        
        for i, paper in enumerate(papers, 1):
            paper_text = f"""
**{i}. {paper.title}**
- **Authors**: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}
- **Journal**: {paper.journal}
- **Date**: {paper.publication_date}
- **PMID**: {paper.pmid}
- **URL**: {paper.url}
"""
            
            if paper.doi:
                paper_text += f"- **DOI**: {paper.doi}\n"
            
            if paper.keywords:
                paper_text += f"- **Keywords**: {', '.join(paper.keywords[:5])}\n"
            
            if include_abstracts and paper.abstract:
                paper_text += f"- **Abstract**: {paper.abstract[:200]}{'...' if len(paper.abstract) > 200 else ''}\n"
            
            formatted_papers.append(paper_text)
        
        return "\n".join(formatted_papers)

# Singleton instance
pubmed_service = PubMedService()