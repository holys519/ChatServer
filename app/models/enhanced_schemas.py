"""
Enhanced Schemas for Advanced RAG System
Defines data structures for context-aware document processing and retrieval
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

class ChunkType(str, Enum):
    """Types of text chunks"""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    LIST = "list"
    CAPTION = "caption"

class DocumentLocation(BaseModel):
    """Precise location within a document"""
    page_number: int = Field(..., description="Page number (1-indexed)")
    bounding_box: Optional[Dict[str, float]] = Field(None, description="x, y, width, height coordinates")
    paragraph_index: Optional[int] = Field(None, description="Paragraph index on the page")
    line_range: Optional[Dict[str, int]] = Field(None, description="start_line, end_line")

class ChunkMetadata(BaseModel):
    """Enhanced metadata for text chunks"""
    # Document identification
    document_id: str = Field(..., description="Original document identifier")
    document_name: str = Field(..., description="Original file name")
    
    # Location information
    location: DocumentLocation = Field(..., description="Precise location in document")
    
    # Content structure
    chunk_type: ChunkType = Field(ChunkType.PARAGRAPH, description="Type of content chunk")
    hierarchy_level: Optional[int] = Field(None, description="Heading level (1-6) if applicable")
    parent_section: Optional[str] = Field(None, description="Parent section title")
    
    # Chunk sequencing
    global_chunk_index: int = Field(..., description="Global sequence number in document")
    page_chunk_index: int = Field(..., description="Sequence number within the page")
    
    # Content statistics
    word_count: int = Field(..., description="Number of words in chunk")
    char_count: int = Field(..., description="Number of characters in chunk")
    sentence_count: int = Field(..., description="Number of sentences in chunk")
    
    # Processing info
    processing_version: str = Field("1.0", description="Version of processing pipeline")
    extracted_at: datetime = Field(default_factory=datetime.now)

class EnhancedChunk(BaseModel):
    """Enhanced chunk with full context information"""
    id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Chunk content")
    metadata: ChunkMetadata = Field(..., description="Enhanced metadata")
    
    # Relationships
    prev_chunk_id: Optional[str] = Field(None, description="Previous chunk ID for context")
    next_chunk_id: Optional[str] = Field(None, description="Next chunk ID for context")
    related_chunks: List[str] = Field(default_factory=list, description="Related chunk IDs")
    
    # Vector data
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")

class ContextWindow(BaseModel):
    """Context window for RAG retrieval"""
    target_chunk: EnhancedChunk = Field(..., description="Main chunk")
    preceding_chunks: List[EnhancedChunk] = Field(default_factory=list, description="Context before")
    following_chunks: List[EnhancedChunk] = Field(default_factory=list, description="Context after")
    
    def get_full_context(self, max_tokens: int = 4000) -> str:
        """Get full context text within token limit"""
        context_parts = []
        
        # Add preceding context
        for chunk in reversed(self.preceding_chunks):
            context_parts.insert(0, f"[Page {chunk.metadata.location.page_number}] {chunk.text}")
        
        # Add target chunk
        context_parts.append(f"[Page {self.target_chunk.metadata.location.page_number}] **{self.target_chunk.text}**")
        
        # Add following context
        for chunk in self.following_chunks:
            context_parts.append(f"[Page {chunk.metadata.location.page_number}] {chunk.text}")
        
        full_text = "\n\n".join(context_parts)
        
        # Truncate if needed (simple word-based truncation)
        words = full_text.split()
        if len(words) > max_tokens:
            truncated_words = words[:max_tokens]
            full_text = " ".join(truncated_words) + "..."
        
        return full_text

class RAGSearchResult(BaseModel):
    """Enhanced search result with context"""
    chunk: EnhancedChunk = Field(..., description="Primary matching chunk")
    similarity_score: float = Field(..., description="Similarity score")
    context_window: ContextWindow = Field(..., description="Context around the chunk")
    source_citation: str = Field(..., description="Formatted citation")
    
    def get_citation(self) -> str:
        """Generate formatted citation"""
        metadata = self.chunk.metadata
        return f"{metadata.document_name}, Page {metadata.location.page_number}"

class RAGQuery(BaseModel):
    """RAG search query with options"""
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, description="Minimum similarity threshold")
    context_window_size: int = Field(2, description="Number of chunks before/after for context")
    include_tables: bool = Field(True, description="Include table content")
    include_captions: bool = Field(True, description="Include image/table captions")
    page_filter: Optional[List[int]] = Field(None, description="Filter by specific pages")
    document_filter: Optional[List[str]] = Field(None, description="Filter by specific documents")

class ProcessingStatus(BaseModel):
    """Enhanced processing status tracking"""
    job_id: str
    user_id: str
    document_name: str
    status: str  # processing, completed, failed
    progress: int  # 0-100
    current_step: str
    
    # Enhanced tracking
    pages_processed: int = 0
    total_pages: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    
    # Timing information
    started_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    warnings: List[str] = Field(default_factory=list)