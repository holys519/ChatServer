"""
Knowledge System API Routes
Handles document upload, vector search, and knowledge graph operations
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import uuid
import base64
from datetime import datetime

from app.models.schemas import TaskRequest, TaskResponse, TaskStatus
from app.services.knowledge_service import knowledge_service
from app.services.task_service import task_service
from app.services.context_aware_rag_service import context_aware_rag_service
from app.services.enhanced_knowledge_graph_service import enhanced_knowledge_graph_service
from app.models.enhanced_schemas import RAGQuery
from app.models.knowledge_graph_schemas import (
    KnowledgeGraphQuery, TopicCluster, ConceptMap, 
    GraphVisualizationConfig, EntityType, RelationType
)
def get_user_id_from_auth_header(authorization: Optional[str]) -> Optional[str]:
    """Authorization ヘッダーからユーザーIDを取得"""
    if not authorization:
        return None
    
    try:
        scheme, user_id = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        return user_id
    except ValueError:
        return None

router = APIRouter()

@router.post("/upload")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """Upload document and start processing pipeline - DEPRECATED: Use /upload-base64 instead"""
    try:
        print(f"📤 Upload request received")
        print(f"   Authorization header: {authorization}")
        
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Try to parse as JSON first (Base64 format)
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            print("📥 Detected JSON request - trying Base64 format")
            try:
                json_data = await request.json()
                
                if "file_content" in json_data:
                    print("✅ Base64 format detected")
                    # Decode Base64 content
                    file_content = base64.b64decode(json_data["file_content"])
                    file_name = json_data["file_name"]
                    content_type_file = json_data["content_type"]
                    processing_options = json_data.get("processing_options", {
                        'enable_vector_search': True,
                        'enable_knowledge_graph': True,
                        'chunk_size': 500,
                        'overlap_size': 50
                    })
                    
                    print(f"📁 Base64 file - Name: {file_name}, Type: {content_type_file}, Size: {len(file_content)} bytes")
                    
                    # Generate job ID
                    job_id = str(uuid.uuid4())
                    
                    # Start enhanced background processing
                    background_tasks.add_task(
                        knowledge_service.process_document_enhanced,
                        job_id=job_id,
                        user_id=user_id,
                        file_content=file_content,
                        file_name=file_name,
                        content_type=content_type_file,
                        options=processing_options
                    )
                    
                    return JSONResponse(content={
                        'success': True,
                        'job_id': job_id,
                        'message': 'Document upload started, processing in background'
                    })
            except Exception as e:
                print(f"❌ JSON parsing failed: {str(e)}")
        
        print("📥 Trying FormData parsing")
        # リクエストからフォームデータを手動で解析
        form_data = await request.form()
        
        # デバッグ: フォームデータの内容をログ出力
        print(f"🔍 Form data keys: {list(form_data.keys())}")
        for key, value in form_data.items():
            if isinstance(value, UploadFile):
                print(f"   {key}: UploadFile(filename={value.filename}, content_type={value.content_type})")
            else:
                print(f"   {key}: {type(value).__name__}({value})")
        
        file = form_data.get("file")
        processing_options_str = form_data.get("processing_options")

        # ファイルの存在と型をチェック
        if not file or not isinstance(file, UploadFile):
            print(f"❌ File validation failed - file: {file}, type: {type(file)}")
            raise HTTPException(status_code=422, detail="File part is missing or invalid.")

        print(f"   Processing options: {processing_options_str}")
        print(f"   File: {file.filename if file else 'No file'}")
        print(f"   File content_type: {file.content_type if file else 'No file'}")
        print(f"   File size: {file.size if file and hasattr(file, 'size') else 'Unknown'}")
        
        # Validate file type
        allowed_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        # Check both content type and file extension
        is_valid_type = file.content_type in allowed_types
        
        # Also check file extension as fallback
        if not is_valid_type and file.filename:
            extension = file.filename.lower().split('.')[-1]
            is_valid_type = extension in ['pdf', 'docx']
        
        print(f"📁 File validation - Name: {file.filename}, Content-Type: {file.content_type}, Valid: {is_valid_type}")
        
        if not is_valid_type:
            raise HTTPException(
                status_code=400, 
                detail=f"Only PDF and DOCX files are supported. Received: {file.content_type} for {file.filename}"
            )
        
        # Parse processing options
        if processing_options_str:
            try:
                options = json.loads(processing_options_str)
            except json.JSONDecodeError:
                options = {
                    'enable_vector_search': True,
                    'enable_knowledge_graph': True,
                    'chunk_size': 500,
                    'overlap_size': 50
                }
        else:
            # Default options when none provided
            options = {
                'enable_vector_search': True,
                'enable_knowledge_graph': True,
                'chunk_size': 500,
                'overlap_size': 50
            }
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # ファイルの内容を読み込む（バックグラウンドタスクの前に）
        file_content = await file.read()
        
        # Start background processing
        background_tasks.add_task(
            knowledge_service.process_document,
            job_id=job_id,
            user_id=user_id,
            file_content=file_content,
            file_name=file.filename,
            content_type=file.content_type,
            options=options
        )
        
        return JSONResponse(content={
            'success': True,
            'job_id': job_id,
            'message': 'Document upload started, processing in background'
        })
        
    except HTTPException as e:
        print(f"❌ HTTP Exception in upload: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Document upload error: {str(e)}")
        print(f"   Error type: {type(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

class Base64FileUpload(BaseModel):
    file_content: str  # Base64 encoded file content
    file_name: str
    content_type: str
    processing_options: Optional[Dict[str, Any]] = {
        'enable_vector_search': True,
        'enable_knowledge_graph': True,
        'chunk_size': 500,
        'overlap_size': 50
    }

@router.post("/upload-base64")
async def upload_document_base64(
    request: Base64FileUpload,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """Upload document using Base64 encoding - Cross-platform compatible"""
    try:
        print(f"📤 Base64 upload request received")
        print(f"   Authorization header: {authorization}")
        print(f"   File name: {request.file_name}")
        print(f"   Content type: {request.content_type}")
        
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Validate file type
        allowed_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        is_valid_type = request.content_type in allowed_types
        
        # Also check file extension as fallback
        if not is_valid_type and request.file_name:
            extension = request.file_name.lower().split('.')[-1]
            is_valid_type = extension in ['pdf', 'docx']
        
        print(f"📁 File validation - Name: {request.file_name}, Content-Type: {request.content_type}, Valid: {is_valid_type}")
        
        if not is_valid_type:
            raise HTTPException(
                status_code=400, 
                detail=f"Only PDF and DOCX files are supported. Received: {request.content_type} for {request.file_name}"
            )
        
        # Decode Base64 content
        try:
            file_content = base64.b64decode(request.file_content)
            print(f"📊 Decoded file size: {len(file_content)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Base64 content: {str(e)}")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Start background processing
        background_tasks.add_task(
            knowledge_service.process_document,
            job_id=job_id,
            user_id=user_id,
            file_content=file_content,
            file_name=request.file_name,
            content_type=request.content_type,
            options=request.processing_options
        )
        
        return JSONResponse(content={
            'success': True,
            'job_id': job_id,
            'message': 'Document upload started, processing in background'
        })
        
    except HTTPException as e:
        print(f"❌ HTTP Exception in base64 upload: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Base64 document upload error: {str(e)}")
        print(f"   Error type: {type(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

class VectorSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True

@router.post("/vector-search")
async def vector_search(
    request: VectorSearchRequest,
    authorization: Optional[str] = Header(None)
):
    """Perform semantic vector search on documents"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Search query is required")
        
        # Set default filters
        filters = request.filters or {
            'similarity_threshold': 0.7,
            'max_results': 10
        }
        
        # Perform vector search
        results = await knowledge_service.vector_search(
            user_id=user_id,
            query=request.query,
            filters=filters,
            include_metadata=request.include_metadata
        )
        
        return JSONResponse(content={
            'success': True,
            'results': results,
            'query': request.query,
            'filters': filters
        })
        
    except Exception as e:
        print(f"❌ Vector search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph")
async def get_knowledge_graph(
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    authorization: Optional[str] = Header(None)
):
    """Get knowledge graph entities and relations"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get knowledge graph data
        graph_data = await knowledge_service.get_knowledge_graph(
            user_id=user_id,
            entity_type=entity_type,
            search_query=search,
            limit=limit
        )
        
        return JSONResponse(content={
            'success': True,
            'graph': graph_data
        })
        
    except Exception as e:
        print(f"❌ Knowledge graph error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing-status")
async def get_processing_status(
    authorization: Optional[str] = Header(None)
):
    """Get status of document processing jobs with enhanced details"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get both regular and enhanced processing jobs
        regular_jobs = await knowledge_service.get_processing_jobs(user_id)
        enhanced_jobs = await knowledge_service.get_enhanced_processing_jobs(user_id)
        
        # Combine and format jobs
        all_jobs = []
        
        # Add regular jobs
        for job in regular_jobs:
            formatted_job = {
                'job_id': job.get('id', ''),
                'document_name': job.get('document_name', ''),
                'status': job.get('status', 'unknown'),
                'progress': job.get('progress', 0),
                'current_step': job.get('current_step', ''),
                'pages_processed': 0,
                'total_pages': 0,
                'chunks_created': 0,
                'embeddings_generated': 0,
                'started_at': job.get('created_at', ''),
                'updated_at': job.get('created_at', ''),
                'error_message': job.get('error_message'),
                'warnings': [],
                'enhanced_processing': False
            }
            all_jobs.append(formatted_job)
        
        # Add enhanced jobs
        for job in enhanced_jobs:
            formatted_job = {
                'job_id': job.get('job_id', ''),
                'document_name': job.get('document_name', ''),
                'status': job.get('status', 'unknown'),
                'progress': job.get('progress', 0),
                'current_step': job.get('current_step', ''),
                'pages_processed': job.get('pages_processed', 0),
                'total_pages': job.get('total_pages', 0),
                'chunks_created': job.get('chunks_created', 0),
                'embeddings_generated': job.get('embeddings_generated', 0),
                'started_at': job.get('started_at', ''),
                'updated_at': job.get('updated_at', ''),
                'estimated_completion': job.get('estimated_completion'),
                'error_message': job.get('error_message'),
                'warnings': job.get('warnings', []),
                'enhanced_processing': True
            }
            all_jobs.append(formatted_job)
        
        return JSONResponse(content={
            'success': True,
            'jobs': all_jobs,
            'total_jobs': len(all_jobs),
            'processing_count': len([j for j in all_jobs if j['status'] == 'processing']),
            'completed_count': len([j for j in all_jobs if j['status'] == 'completed']),
            'failed_count': len([j for j in all_jobs if j['status'] == 'failed'])
        })
        
    except Exception as e:
        print(f"❌ Processing status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entities/{entity_id}")
async def get_entity_details(
    entity_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get detailed information about a specific entity"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        entity_details = await knowledge_service.get_entity_details(
            user_id=user_id,
            entity_id=entity_id
        )
        
        if not entity_details:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return JSONResponse(content={
            'success': True,
            'entity': entity_details
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Entity details error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_processed_documents(
    authorization: Optional[str] = Header(None)
):
    """Get list of processed documents"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        documents = await knowledge_service.get_processed_documents(user_id)
        
        return JSONResponse(content={
            'success': True,
            'documents': documents
        })
        
    except Exception as e:
        print(f"❌ Get documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    authorization: Optional[str] = Header(None)
):
    """Delete a processed document and its associated data"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        success = await knowledge_service.delete_document(
            user_id=user_id,
            document_id=document_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return JSONResponse(content={
            'success': True,
            'message': 'Document deleted successfully'
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reprocess/{document_id}")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    processing_options: Optional[Dict[str, Any]] = None,
    authorization: Optional[str] = Header(None)
):
    """Reprocess an existing document with new options"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Set default processing options
        if not processing_options:
            processing_options = {
                'enable_vector_search': True,
                'enable_knowledge_graph': True,
                'chunk_size': 500,
                'overlap_size': 50
            }
        
        # Generate new job ID
        job_id = str(uuid.uuid4())
        
        # Start reprocessing
        background_tasks.add_task(
            knowledge_service.reprocess_document,
            job_id=job_id,
            user_id=user_id,
            document_id=document_id,
            options=processing_options
        )
        
        return JSONResponse(content={
            'success': True,
            'job_id': job_id,
            'message': 'Document reprocessing started'
        })
        
    except Exception as e:
        print(f"❌ Reprocess document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_knowledge_stats(
    authorization: Optional[str] = Header(None)
):
    """Get statistics about the user's knowledge base"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        stats = await knowledge_service.get_knowledge_stats(user_id)
        
        return JSONResponse(content={
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        print(f"❌ Knowledge stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag-search")
async def context_aware_rag_search(
    query: RAGQuery,
    authorization: Optional[str] = Header(None)
):
    """Perform context-aware RAG search with adjacent chunk retrieval"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        print(f"🔍 Context-aware RAG search: '{query.query}' for user {user_id}")
        
        # Perform context-aware search
        search_results = await context_aware_rag_service.search_with_context(query, user_id)
        
        # Format results for API response
        formatted_results = []
        for result in search_results:
            formatted_result = {
                'chunk': {
                    'id': result.chunk.id,
                    'text': result.chunk.text,
                    'metadata': {
                        'document_name': result.chunk.metadata.document_name,
                        'page_number': result.chunk.metadata.location.page_number,
                        'paragraph_index': result.chunk.metadata.location.paragraph_index,
                        'chunk_type': result.chunk.metadata.chunk_type.value,
                        'word_count': result.chunk.metadata.word_count
                    }
                },
                'similarity_score': result.similarity_score,
                'source_citation': result.source_citation,
                'context': {
                    'full_context': result.context_window.get_full_context(),
                    'preceding_count': len(result.context_window.preceding_chunks),
                    'following_count': len(result.context_window.following_chunks)
                }
            }
            formatted_results.append(formatted_result)
        
        return JSONResponse(content={
            'success': True,
            'query': query.query,
            'results': formatted_results,
            'total_results': len(formatted_results),
            'search_params': {
                'similarity_threshold': query.similarity_threshold,
                'max_results': query.max_results,
                'context_window_size': query.context_window_size
            }
        })
        
    except Exception as e:
        print(f"❌ Context-aware RAG search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chunk/{chunk_id}/neighbors")
async def get_chunk_neighbors(
    chunk_id: str,
    neighbor_count: int = 3,
    authorization: Optional[str] = Header(None)
):
    """Get neighboring chunks for context expansion"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        neighbors = await context_aware_rag_service.get_chunk_neighbors(
            chunk_id, user_id, neighbor_count
        )
        
        # Format neighbor chunks
        def format_chunk(chunk):
            return {
                'id': chunk.id,
                'text': chunk.text,
                'page_number': chunk.metadata.location.page_number,
                'chunk_index': chunk.metadata.global_chunk_index
            }
        
        return JSONResponse(content={
            'success': True,
            'chunk_id': chunk_id,
            'neighbors': {
                'before': [format_chunk(chunk) for chunk in neighbors['before']],
                'after': [format_chunk(chunk) for chunk in neighbors['after']]
            }
        })
        
    except Exception as e:
        print(f"❌ Get chunk neighbors error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/similar-chunks/{reference_chunk_id}")
async def find_similar_chunks(
    reference_chunk_id: str,
    max_results: int = 5,
    similarity_threshold: float = 0.8,
    authorization: Optional[str] = Header(None)
):
    """Find chunks similar to a reference chunk"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        similar_chunks = await context_aware_rag_service.search_similar_chunks(
            reference_chunk_id, user_id, max_results, similarity_threshold
        )
        
        # Format results
        results = []
        for chunk, similarity in similar_chunks:
            results.append({
                'chunk': {
                    'id': chunk.id,
                    'text': chunk.text,
                    'document_name': chunk.metadata.document_name,
                    'page_number': chunk.metadata.location.page_number
                },
                'similarity_score': similarity
            })
        
        return JSONResponse(content={
            'success': True,
            'reference_chunk_id': reference_chunk_id,
            'similar_chunks': results,
            'search_params': {
                'max_results': max_results,
                'similarity_threshold': similarity_threshold
            }
        })
        
    except Exception as e:
        print(f"❌ Find similar chunks error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Knowledge Graph Endpoints

class KnowledgeGraphQueryRequest(BaseModel):
    query_type: str = "entity_search"
    search_terms: List[str] = []
    entity_types: List[str] = []
    relation_types: List[str] = []
    max_results: int = 50
    min_confidence: float = 0.5
    include_clusters: bool = False
    include_metrics: bool = True

@router.post("/knowledge-graph/query")
async def query_knowledge_graph(
    request: KnowledgeGraphQueryRequest,
    authorization: Optional[str] = Header(None)
):
    """Query the enhanced knowledge graph with advanced filtering"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Convert string enums to actual enum types
        entity_types = []
        for et in request.entity_types:
            try:
                entity_types.append(EntityType(et))
            except ValueError:
                continue
        
        relation_types = []
        for rt in request.relation_types:
            try:
                relation_types.append(RelationType(rt))
            except ValueError:
                continue
        
        # Create knowledge graph query
        kg_query = KnowledgeGraphQuery(
            query_type=request.query_type,
            search_terms=request.search_terms,
            entity_types=entity_types,
            relation_types=relation_types,
            max_results=request.max_results,
            min_confidence=request.min_confidence,
            include_clusters=request.include_clusters,
            include_metrics=request.include_metrics
        )
        
        # Execute query
        results = await enhanced_knowledge_graph_service.query_knowledge_graph(kg_query, user_id)
        
        return JSONResponse(content={
            'success': True,
            'results': results,
            'query_params': request.dict()
        })
        
    except Exception as e:
        print(f"❌ Knowledge graph query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge-graph/cluster")
async def create_topic_clusters(
    min_cluster_size: int = 3,
    max_clusters: int = 10,
    authorization: Optional[str] = Header(None)
):
    """Create topic-based document clusters"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        print(f"🎯 Creating topic clusters for user {user_id}")
        
        # Create clusters
        clusters = await enhanced_knowledge_graph_service.create_topic_clusters(
            user_id=user_id,
            min_cluster_size=min_cluster_size,
            max_clusters=max_clusters
        )
        
        return JSONResponse(content={
            'success': True,
            'clusters': [cluster.dict() for cluster in clusters],
            'total_clusters': len(clusters),
            'cluster_params': {
                'min_cluster_size': min_cluster_size,
                'max_clusters': max_clusters
            }
        })
        
    except Exception as e:
        print(f"❌ Topic clustering error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class ConceptMapRequest(BaseModel):
    name: str
    description: str = ""
    entity_types: List[str] = []
    relation_types: List[str] = []
    focus_entity_id: Optional[str] = None
    max_entities: int = 50
    depth_level: int = 2
    min_confidence: float = 0.5

@router.post("/knowledge-graph/concept-map")
async def create_concept_map(
    request: ConceptMapRequest,
    authorization: Optional[str] = Header(None)
):
    """Create a concept map from knowledge graph data"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        print(f"🗺️ Creating concept map '{request.name}' for user {user_id}")
        
        # Query entities and relations for the concept map
        kg_query = KnowledgeGraphQuery(
            query_type="all",
            entity_types=[EntityType(et) for et in request.entity_types if et in [e.value for e in EntityType]],
            relation_types=[RelationType(rt) for rt in request.relation_types if rt in [r.value for r in RelationType]],
            max_results=request.max_entities,
            min_confidence=request.min_confidence,
            include_clusters=True,
            include_metrics=True
        )
        
        # Get graph data
        graph_data = await enhanced_knowledge_graph_service.query_knowledge_graph(kg_query, user_id)
        
        # Create concept map
        concept_map = ConceptMap(
            name=request.name,
            description=request.description,
            entities=[entity['id'] for entity in graph_data.get('entities', [])],
            relations=[relation['id'] for relation in graph_data.get('relations', [])],
            clusters=[cluster['id'] for cluster in graph_data.get('clusters', [])],
            focus_entity_id=request.focus_entity_id,
            depth_level=request.depth_level,
            min_confidence=request.min_confidence,
            max_entities=request.max_entities,
            user_id=user_id
        )
        
        return JSONResponse(content={
            'success': True,
            'concept_map': concept_map.dict(),
            'graph_data': graph_data
        })
        
    except Exception as e:
        print(f"❌ Concept map creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge-graph/stats")
async def get_knowledge_graph_stats(
    authorization: Optional[str] = Header(None)
):
    """Get comprehensive knowledge graph statistics"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Create a basic query to get stats
        kg_query = KnowledgeGraphQuery(
            query_type="all",
            max_results=1,
            include_metrics=True
        )
        
        # Get stats through query
        results = await enhanced_knowledge_graph_service.query_knowledge_graph(kg_query, user_id)
        
        return JSONResponse(content={
            'success': True,
            'stats': results.get('stats', {}),
            'entity_count': len(results.get('entities', [])),
            'relation_count': len(results.get('relations', [])),
            'cluster_count': len(results.get('clusters', []))
        })
        
    except Exception as e:
        print(f"❌ Knowledge graph stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge-graph/entity/{entity_id}")
async def get_enhanced_entity(
    entity_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get detailed information about an enhanced entity"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Query specific entity
        kg_query = KnowledgeGraphQuery(
            query_type="entity_search",
            max_results=1,
            include_metrics=True
        )
        
        # Get entity details through the service
        results = await enhanced_knowledge_graph_service.query_knowledge_graph(kg_query, user_id)
        
        # Find the specific entity
        entity = None
        for e in results.get('entities', []):
            if e.get('id') == entity_id:
                entity = e
                break
        
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        # Get related relations
        related_relations = [r for r in results.get('relations', []) 
                           if r.get('source_entity_id') == entity_id or r.get('target_entity_id') == entity_id]
        
        return JSONResponse(content={
            'success': True,
            'entity': entity,
            'related_relations': related_relations,
            'relation_count': len(related_relations)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Enhanced entity details error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))