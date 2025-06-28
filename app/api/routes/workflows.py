"""
Workflows API for CRA-Copilot
Provides workflow status tracking, progress monitoring, and result visualization
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.services.workflow_status_service import workflow_status_service, WorkflowType

router = APIRouter()

class WorkflowCreateRequest(BaseModel):
    """Request to create a new workflow"""
    workflow_type: str
    title: str
    description: str
    input_parameters: Dict[str, Any]

class WorkflowResponse(BaseModel):
    """Workflow response model"""
    workflow_id: str
    type: str
    title: str
    description: str
    status: str
    progress: Dict[str, Any]
    steps: List[Dict[str, Any]]
    timing: Dict[str, str]
    input_parameters: Dict[str, Any]
    results: Dict[str, Any]
    quality_metrics: Dict[str, Any]

class WorkflowListResponse(BaseModel):
    """Response for listing workflows"""
    workflows: List[WorkflowResponse]
    total_count: int
    active_count: int
    completed_count: int

@router.post("/create")
async def create_workflow(request: WorkflowCreateRequest) -> Dict[str, str]:
    """Create a new workflow and return workflow ID"""
    try:
        # Validate workflow type
        try:
            workflow_type = WorkflowType(request.workflow_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid workflow type: {request.workflow_type}")
        
        # Create workflow card
        workflow_id = workflow_status_service.create_workflow_card(
            workflow_type=workflow_type,
            title=request.title,
            description=request.description,
            input_parameters=request.input_parameters
        )
        
        return {
            "workflow_id": workflow_id,
            "message": f"Workflow '{request.title}' created successfully",
            "estimated_completion": workflow_status_service.get_workflow_card(workflow_id).estimated_completion
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}")
async def get_workflow_status(workflow_id: str) -> WorkflowResponse:
    """Get detailed workflow status and progress"""
    try:
        workflow_data = workflow_status_service.format_workflow_for_display(workflow_id)
        
        if not workflow_data:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        return WorkflowResponse(**workflow_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/progress")
async def get_workflow_progress(workflow_id: str) -> Dict[str, Any]:
    """Get real-time workflow progress"""
    try:
        workflow = workflow_status_service.get_workflow_card(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        # Get current step details
        current_step = next((step for step in workflow.steps if step.status == "running"), None)
        
        return {
            "workflow_id": workflow_id,
            "overall_progress": round(workflow.overall_progress, 1),
            "current_stage": workflow.current_stage.value,
            "current_step": {
                "name": current_step.name.replace("_", " ").title() if current_step else "None",
                "description": current_step.description if current_step else "",
                "progress": current_step.progress if current_step else 0.0
            } if current_step else None,
            "estimated_remaining": workflow.estimated_completion,
            "last_updated": workflow.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/steps")
async def get_workflow_steps(workflow_id: str) -> List[Dict[str, Any]]:
    """Get detailed workflow steps information"""
    try:
        workflow_data = workflow_status_service.format_workflow_for_display(workflow_id)
        
        if not workflow_data:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        return workflow_data["steps"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/results")
async def get_workflow_results(workflow_id: str) -> Dict[str, Any]:
    """Get workflow results in structured format"""
    try:
        workflow = workflow_status_service.get_workflow_card(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        if not workflow.final_results:
            return {
                "workflow_id": workflow_id,
                "status": "in_progress",
                "message": "Results not yet available - workflow still running"
            }
        
        formatted_data = workflow_status_service.format_workflow_for_display(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "results": formatted_data["results"],
            "quality_metrics": formatted_data["quality_metrics"],
            "summary": {
                "workflow_type": workflow.workflow_type.value,
                "total_duration": formatted_data["timing"]["duration"],
                "completion_time": formatted_data["timing"]["updated_at"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by status"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    limit: int = Query(10, description="Maximum number of workflows to return")
) -> WorkflowListResponse:
    """List workflows with optional filtering"""
    try:
        workflows = workflow_status_service.list_active_workflows()
        
        # Apply filters
        if status:
            workflows = [w for w in workflows if w.current_stage.value == status]
        
        if workflow_type:
            workflows = [w for w in workflows if w.workflow_type.value == workflow_type]
        
        # Sort by most recent first
        workflows.sort(key=lambda w: w.updated_at, reverse=True)
        
        # Apply limit
        limited_workflows = workflows[:limit]
        
        # Format for response
        formatted_workflows = []
        for workflow in limited_workflows:
            workflow_data = workflow_status_service.format_workflow_for_display(workflow.workflow_id)
            formatted_workflows.append(WorkflowResponse(**workflow_data))
        
        # Calculate counts
        total_count = len(workflows)
        active_count = len([w for w in workflows if w.current_stage.value not in ["completed", "failed"]])
        completed_count = len([w for w in workflows if w.current_stage.value == "completed"])
        
        return WorkflowListResponse(
            workflows=formatted_workflows,
            total_count=total_count,
            active_count=active_count,
            completed_count=completed_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types/available")
async def get_available_workflow_types() -> List[Dict[str, str]]:
    """Get list of available workflow types"""
    return [
        {
            "type": WorkflowType.COMPLETE_RESEARCH.value,
            "name": "Complete Research Workflow",
            "description": "Full research pipeline: paper search + quality validation + literature review creation",
            "estimated_time": "3-5 minutes"
        },
        {
            "type": WorkflowType.PAPER_SEARCH_AUDITOR.value,
            "name": "Paper Search Auditor",
            "description": "Enhanced paper search with multi-agent quality validation",
            "estimated_time": "1-2 minutes"
        },
        {
            "type": WorkflowType.PAPER_SCOUT.value,
            "name": "Paper Scout",
            "description": "Basic paper search and analysis from PubMed database",
            "estimated_time": "30-60 seconds"
        },
        {
            "type": WorkflowType.STREAMLINED_REVIEW.value,
            "name": "Streamlined Review Creation",
            "description": "Literature review creation from pre-validated papers",
            "estimated_time": "2-3 minutes"
        }
    ]

@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, str]:
    """Delete a workflow"""
    try:
        if workflow_id in workflow_status_service.active_workflows:
            del workflow_status_service.active_workflows[workflow_id]
            return {"message": f"Workflow '{workflow_id}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/export")
async def export_workflow_results(
    workflow_id: str,
    format: str = Query("json", description="Export format: json, markdown, csv")
) -> Dict[str, Any]:
    """Export workflow results in various formats"""
    try:
        workflow = workflow_status_service.get_workflow_card(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        if not workflow.final_results:
            raise HTTPException(status_code=400, detail="Workflow not completed - no results to export")
        
        formatted_data = workflow_status_service.format_workflow_for_display(workflow_id)
        
        if format.lower() == "json":
            return {
                "format": "json",
                "data": formatted_data
            }
        
        elif format.lower() == "markdown":
            # Convert to markdown format
            markdown_content = f"""# {workflow.title}

**Type**: {workflow.workflow_type.value}
**Status**: {workflow.current_stage.value}
**Completion**: {workflow.updated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Results Summary
{json.dumps(formatted_data['results'], indent=2)}

## Quality Metrics
{json.dumps(formatted_data['quality_metrics'], indent=2)}
"""
            return {
                "format": "markdown",
                "data": markdown_content
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))