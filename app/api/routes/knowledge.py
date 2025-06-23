"""
Knowledge System API Routes
Handles document upload, vector search, and knowledge graph operations
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime

from app.models.schemas import TaskRequest, TaskResponse, TaskStatus
from app.services.knowledge_service import knowledge_service
from app.services.task_service import task_service
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    processing_options: str = Form(...),
    authorization: Optional[str] = Header(None)
):
    """Upload document and start processing pipeline"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
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
        try:
            options = json.loads(processing_options)
        except json.JSONDecodeError:
            options = {
                'enable_vector_search': True,
                'enable_knowledge_graph': True,
                'chunk_size': 500,
                'overlap_size': 50
            }
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Start background processing
        background_tasks.add_task(
            knowledge_service.process_document,
            job_id=job_id,
            user_id=user_id,
            file=file,
            options=options
        )
        
        return JSONResponse(content={
            'success': True,
            'job_id': job_id,
            'message': 'Document upload started, processing in background'
        })
        
    except Exception as e:
        print(f"❌ Document upload error: {str(e)}")
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
    """Get status of document processing jobs"""
    try:
        user_id = get_user_id_from_auth_header(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Get processing jobs for user
        jobs = await knowledge_service.get_processing_jobs(user_id)
        
        return JSONResponse(content={
            'success': True,
            'jobs': jobs
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