"""
Context-Aware RAG Service
Provides intelligent document search with context preservation
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.models.enhanced_schemas import (
    EnhancedChunk, ContextWindow, RAGSearchResult, RAGQuery,
    ChunkMetadata, DocumentLocation
)

# Firebase and embedding imports
try:
    from app.services.firebase_service import firebase_service
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_service = None
    FIREBASE_AVAILABLE = False

try:
    from vertexai.language_models import TextEmbeddingModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    TextEmbeddingModel = None
    VERTEX_AI_AVAILABLE = False

class ContextAwareRAGService:
    """
    Advanced RAG service with context-aware retrieval
    """
    
    def __init__(self):
        self.embedding_model = None
        self.firestore_client = None
        
        # Initialize embedding model
        if VERTEX_AI_AVAILABLE:
            try:
                self.embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
                print("✅ Vertex AI embedding model initialized")
            except Exception as e:
                print(f"⚠️ Vertex AI embedding initialization failed: {e}")
        
        # Initialize Firestore
        if FIREBASE_AVAILABLE and firebase_service and firebase_service.is_available():
            self.firestore_client = firebase_service.get_firestore_client()
            print("✅ Firestore client initialized for RAG")
        else:
            print("⚠️ Firestore not available for RAG service")
    
    async def search_with_context(
        self, 
        query: RAGQuery, 
        user_id: str
    ) -> List[RAGSearchResult]:
        """
        Perform context-aware RAG search
        
        Args:
            query: RAG search parameters
            user_id: User identifier for data isolation
            
        Returns:
            List of RAG search results with context windows
        """
        print(f"🔍 Context-aware RAG search: '{query.query}' for user {user_id}")
        
        if not self.firestore_client:
            print("⚠️ Firestore not available, returning empty results")
            return []
        
        try:
            # Step 1: Generate query embedding
            query_embedding = await self._generate_query_embedding(query.query)
            if not query_embedding:
                print("❌ Failed to generate query embedding")
                return []
            
            # Step 2: Retrieve candidate chunks
            candidate_chunks = await self._retrieve_candidate_chunks(
                user_id, query, query_embedding
            )
            
            if not candidate_chunks:
                print("📭 No candidate chunks found")
                return []
            
            # Step 3: Build context windows for each candidate
            search_results = []
            for chunk, similarity in candidate_chunks[:query.max_results]:
                context_window = await self._build_context_window(
                    chunk, query.context_window_size, user_id
                )
                
                # Create search result with citation
                result = RAGSearchResult(
                    chunk=chunk,
                    similarity_score=similarity,
                    context_window=context_window,
                    source_citation=self._generate_citation(chunk)
                )
                
                search_results.append(result)
            
            print(f"✅ Found {len(search_results)} context-aware results")
            return search_results
            
        except Exception as e:
            print(f"❌ Context-aware RAG search error: {e}")
            return []
    
    async def _generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for search query"""
        
        if not self.embedding_model:
            print("⚠️ Embedding model not available")
            return None
        
        try:
            embeddings = self.embedding_model.get_embeddings([query])
            return embeddings[0].values
        except Exception as e:
            print(f"❌ Query embedding generation failed: {e}")
            return None
    
    async def _retrieve_candidate_chunks(
        self,
        user_id: str,
        query: RAGQuery,
        query_embedding: List[float]
    ) -> List[Tuple[EnhancedChunk, float]]:
        """
        Retrieve candidate chunks with similarity scoring
        """
        
        # Build Firestore query
        chunks_ref = self.firestore_client.collection('enhanced_vector_chunks')
        chunks_query = chunks_ref.where('user_id', '==', user_id)
        
        # Apply document filter if specified
        if query.document_filter:
            chunks_query = chunks_query.where('metadata.document_name', 'in', query.document_filter)
        
        # Retrieve chunks (limit to reasonable number for similarity calculation)
        docs = chunks_query.limit(500).stream()
        
        candidates = []
        for doc in docs:
            try:
                chunk_data = doc.to_dict()
                
                # Convert Firestore data to EnhancedChunk
                chunk = self._firestore_to_enhanced_chunk(chunk_data)
                
                # Apply page filter if specified
                if query.page_filter and chunk.metadata.location.page_number not in query.page_filter:
                    continue
                
                # Apply content type filters
                if not query.include_tables and chunk.metadata.chunk_type.value == "table":
                    continue
                if not query.include_captions and chunk.metadata.chunk_type.value == "caption":
                    continue
                
                # Calculate similarity
                if 'embedding' in chunk_data and chunk_data['embedding']:
                    similarity = self._calculate_cosine_similarity(
                        query_embedding, chunk_data['embedding']
                    )
                    
                    # Apply similarity threshold
                    if similarity >= query.similarity_threshold:
                        candidates.append((chunk, similarity))
                
            except Exception as e:
                print(f"⚠️ Error processing chunk {doc.id}: {e}")
                continue
        
        # Sort by similarity (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        print(f"📊 Retrieved {len(candidates)} candidate chunks")
        return candidates
    
    async def _build_context_window(
        self,
        target_chunk: EnhancedChunk,
        window_size: int,
        user_id: str
    ) -> ContextWindow:
        """
        Build context window around target chunk
        """
        
        # Get chunks before and after the target chunk
        preceding_chunks = await self._get_adjacent_chunks(
            target_chunk, user_id, direction="before", count=window_size
        )
        
        following_chunks = await self._get_adjacent_chunks(
            target_chunk, user_id, direction="after", count=window_size
        )
        
        return ContextWindow(
            target_chunk=target_chunk,
            preceding_chunks=preceding_chunks,
            following_chunks=following_chunks
        )
    
    async def _get_adjacent_chunks(
        self,
        target_chunk: EnhancedChunk,
        user_id: str,
        direction: str,
        count: int
    ) -> List[EnhancedChunk]:
        """
        Get adjacent chunks (before or after) the target chunk
        """
        
        if not self.firestore_client:
            return []
        
        try:
            chunks_ref = self.firestore_client.collection('enhanced_vector_chunks')
            
            # Build query based on direction
            target_index = target_chunk.metadata.global_chunk_index
            
            if direction == "before":
                # Get chunks with lower global index (preceding chunks)
                query = chunks_ref.where('user_id', '==', user_id) \
                                 .where('metadata.document_id', '==', target_chunk.metadata.document_id) \
                                 .where('metadata.global_chunk_index', '<', target_index) \
                                 .order_by('metadata.global_chunk_index', direction='DESCENDING') \
                                 .limit(count)
            else:  # direction == "after"
                # Get chunks with higher global index (following chunks)
                query = chunks_ref.where('user_id', '==', user_id) \
                                 .where('metadata.document_id', '==', target_chunk.metadata.document_id) \
                                 .where('metadata.global_chunk_index', '>', target_index) \
                                 .order_by('metadata.global_chunk_index', direction='ASCENDING') \
                                 .limit(count)
            
            # Execute query and convert to EnhancedChunk objects
            docs = query.stream()
            chunks = []
            
            for doc in docs:
                chunk_data = doc.to_dict()
                chunk = self._firestore_to_enhanced_chunk(chunk_data)
                chunks.append(chunk)
            
            # For "before" chunks, reverse to maintain chronological order
            if direction == "before":
                chunks.reverse()
            
            return chunks
            
        except Exception as e:
            print(f"❌ Error retrieving adjacent chunks: {e}")
            return []
    
    def _firestore_to_enhanced_chunk(self, chunk_data: Dict[str, Any]) -> EnhancedChunk:
        """Convert Firestore document data to EnhancedChunk object"""
        
        # Extract metadata
        metadata_dict = chunk_data.get('metadata', {})
        location_dict = metadata_dict.get('location', {})
        
        # Create DocumentLocation
        location = DocumentLocation(
            page_number=location_dict.get('page_number', 1),
            bounding_box=location_dict.get('bounding_box'),
            paragraph_index=location_dict.get('paragraph_index'),
            line_range=location_dict.get('line_range')
        )
        
        # Create ChunkMetadata
        from app.models.enhanced_schemas import ChunkType
        chunk_type = ChunkType(metadata_dict.get('chunk_type', 'paragraph'))
        
        metadata = ChunkMetadata(
            document_id=metadata_dict.get('document_id', ''),
            document_name=metadata_dict.get('document_name', ''),
            location=location,
            chunk_type=chunk_type,
            hierarchy_level=metadata_dict.get('hierarchy_level'),
            parent_section=metadata_dict.get('parent_section'),
            global_chunk_index=metadata_dict.get('global_chunk_index', 0),
            page_chunk_index=metadata_dict.get('page_chunk_index', 0),
            word_count=metadata_dict.get('word_count', 0),
            char_count=metadata_dict.get('char_count', 0),
            sentence_count=metadata_dict.get('sentence_count', 0),
            processing_version=metadata_dict.get('processing_version', '1.0'),
            extracted_at=metadata_dict.get('extracted_at', datetime.now())
        )
        
        # Create EnhancedChunk
        return EnhancedChunk(
            id=chunk_data.get('id', ''),
            text=chunk_data.get('text', ''),
            metadata=metadata,
            prev_chunk_id=chunk_data.get('prev_chunk_id'),
            next_chunk_id=chunk_data.get('next_chunk_id'),
            related_chunks=chunk_data.get('related_chunks', []),
            embedding=chunk_data.get('embedding'),
            embedding_model=chunk_data.get('embedding_model')
        )
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        
        try:
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(b * b for b in vec2))
            
            # Avoid division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            return max(0.0, min(1.0, similarity))  # Clamp between 0 and 1
            
        except Exception as e:
            print(f"❌ Similarity calculation error: {e}")
            return 0.0
    
    def _generate_citation(self, chunk: EnhancedChunk) -> str:
        """Generate formatted citation for a chunk"""
        
        metadata = chunk.metadata
        citation_parts = []
        
        # Document name
        citation_parts.append(metadata.document_name)
        
        # Page number
        citation_parts.append(f"Page {metadata.location.page_number}")
        
        # Additional location info if available
        if metadata.location.paragraph_index is not None:
            citation_parts.append(f"Paragraph {metadata.location.paragraph_index + 1}")
        
        return ", ".join(citation_parts)
    
    async def get_chunk_neighbors(
        self,
        chunk_id: str,
        user_id: str,
        neighbor_count: int = 3
    ) -> Dict[str, List[EnhancedChunk]]:
        """
        Get neighboring chunks for a specific chunk ID
        
        Returns:
            Dict with 'before' and 'after' keys containing neighbor lists
        """
        
        if not self.firestore_client:
            return {"before": [], "after": []}
        
        try:
            # Get the target chunk first
            chunk_doc = self.firestore_client.collection('enhanced_vector_chunks').document(chunk_id).get()
            
            if not chunk_doc.exists:
                print(f"❌ Chunk {chunk_id} not found")
                return {"before": [], "after": []}
            
            target_chunk = self._firestore_to_enhanced_chunk(chunk_doc.to_dict())
            
            # Get neighbors
            before_chunks = await self._get_adjacent_chunks(
                target_chunk, user_id, "before", neighbor_count
            )
            after_chunks = await self._get_adjacent_chunks(
                target_chunk, user_id, "after", neighbor_count
            )
            
            return {
                "before": before_chunks,
                "after": after_chunks
            }
            
        except Exception as e:
            print(f"❌ Error getting chunk neighbors: {e}")
            return {"before": [], "after": []}
    
    async def search_similar_chunks(
        self,
        reference_chunk_id: str,
        user_id: str,
        max_results: int = 5,
        similarity_threshold: float = 0.8
    ) -> List[Tuple[EnhancedChunk, float]]:
        """
        Find chunks similar to a reference chunk
        """
        
        if not self.firestore_client:
            return []
        
        try:
            # Get reference chunk
            ref_doc = self.firestore_client.collection('enhanced_vector_chunks').document(reference_chunk_id).get()
            if not ref_doc.exists:
                return []
            
            ref_data = ref_doc.to_dict()
            ref_embedding = ref_data.get('embedding')
            
            if not ref_embedding:
                return []
            
            # Search for similar chunks
            chunks_ref = self.firestore_client.collection('enhanced_vector_chunks')
            docs = chunks_ref.where('user_id', '==', user_id).limit(200).stream()
            
            similar_chunks = []
            for doc in docs:
                if doc.id == reference_chunk_id:  # Skip the reference chunk itself
                    continue
                
                chunk_data = doc.to_dict()
                if 'embedding' not in chunk_data:
                    continue
                
                similarity = self._calculate_cosine_similarity(
                    ref_embedding, chunk_data['embedding']
                )
                
                if similarity >= similarity_threshold:
                    chunk = self._firestore_to_enhanced_chunk(chunk_data)
                    similar_chunks.append((chunk, similarity))
            
            # Sort by similarity and limit results
            similar_chunks.sort(key=lambda x: x[1], reverse=True)
            return similar_chunks[:max_results]
            
        except Exception as e:
            print(f"❌ Error finding similar chunks: {e}")
            return []

# Global service instance
context_aware_rag_service = ContextAwareRAGService()