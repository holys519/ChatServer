"""
Workflow Status Service for MedAgent-Chat
Manages workflow states, progress tracking, and result formatting
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import json

class WorkflowType(Enum):
    """Types of workflows"""
    COMPLETE_RESEARCH = "complete_research"
    PAPER_SEARCH_AUDITOR = "paper_search_auditor"
    PAPER_SCOUT = "paper_scout"
    REVIEW_CREATION = "review_creation"
    STREAMLINED_REVIEW = "streamlined_review"

class WorkflowStage(Enum):
    """Workflow execution stages"""
    INITIALIZING = "initializing"
    PAPER_COLLECTION = "paper_collection"
    QUALITY_VALIDATION = "quality_validation"
    ANALYSIS = "analysis"
    STRUCTURE_DESIGN = "structure_design"
    CONTENT_WRITING = "content_writing"
    QUALITY_REVIEW = "quality_review"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowStep:
    """Individual workflow step"""
    step_id: str
    name: str
    description: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

@dataclass
class WorkflowCard:
    """Workflow card for UI display"""
    workflow_id: str
    workflow_type: WorkflowType
    title: str
    description: str
    current_stage: WorkflowStage
    overall_progress: float
    estimated_completion: str
    steps: List[WorkflowStep]
    created_at: datetime
    updated_at: datetime
    input_parameters: Dict[str, Any] = field(default_factory=dict)
    final_results: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)

class WorkflowStatusService:
    """Service for managing workflow status and UI components"""
    
    def __init__(self):
        self.active_workflows: Dict[str, WorkflowCard] = {}
        self.workflow_templates = self._create_workflow_templates()
    
    def _create_workflow_templates(self) -> Dict[WorkflowType, List[Dict[str, str]]]:
        """Create workflow step templates"""
        return {
            WorkflowType.COMPLETE_RESEARCH: [
                {"name": "initialization", "description": "Initializing research workflow", "stage": "initializing"},
                {"name": "paper_search", "description": "Searching for relevant papers", "stage": "paper_collection"},
                {"name": "quality_validation", "description": "Validating paper quality", "stage": "quality_validation"},
                {"name": "gap_analysis", "description": "Analyzing research gaps", "stage": "analysis"},
                {"name": "review_structure", "description": "Designing review structure", "stage": "structure_design"},
                {"name": "content_writing", "description": "Writing literature review", "stage": "content_writing"},
                {"name": "quality_review", "description": "Reviewing and polishing", "stage": "quality_review"},
                {"name": "finalization", "description": "Finalizing review", "stage": "finalization"}
            ],
            WorkflowType.PAPER_SEARCH_AUDITOR: [
                {"name": "initialization", "description": "Initializing paper search audit", "stage": "initializing"},
                {"name": "initial_search", "description": "Collecting initial papers", "stage": "paper_collection"},
                {"name": "quality_criticism", "description": "Critiquing paper quality", "stage": "quality_validation"},
                {"name": "collection_revision", "description": "Enhancing paper collection", "stage": "analysis"},
                {"name": "final_validation", "description": "Final quality validation", "stage": "finalization"}
            ],
            WorkflowType.PAPER_SCOUT: [
                {"name": "initialization", "description": "Initializing paper search", "stage": "initializing"},
                {"name": "query_optimization", "description": "Optimizing search query", "stage": "paper_collection"},
                {"name": "database_search", "description": "Searching PubMed database", "stage": "paper_collection"},
                {"name": "result_analysis", "description": "Analyzing search results", "stage": "analysis"},
                {"name": "finalization", "description": "Formatting results", "stage": "finalization"}
            ],
            WorkflowType.REVIEW_CREATION: [
                {"name": "initialization", "description": "Initializing literature review creation", "stage": "initializing"},
                {"name": "translation_analysis", "description": "Analyzing language requirements", "stage": "analysis"},
                {"name": "search_strategy", "description": "Planning search strategy", "stage": "paper_collection"},
                {"name": "paper_collection", "description": "Collecting relevant papers", "stage": "paper_collection"},
                {"name": "paper_analysis", "description": "Analyzing collected papers", "stage": "analysis"},
                {"name": "structure_design", "description": "Designing review structure", "stage": "structure_design"},
                {"name": "content_writing", "description": "Writing review content", "stage": "content_writing"},
                {"name": "quality_review", "description": "Reviewing and polishing", "stage": "quality_review"},
                {"name": "finalization", "description": "Finalizing review", "stage": "finalization"}
            ],
            WorkflowType.STREAMLINED_REVIEW: [
                {"name": "initialization", "description": "Initializing review creation", "stage": "initializing"},
                {"name": "translation_analysis", "description": "Analyzing language requirements", "stage": "analysis"},
                {"name": "paper_analysis", "description": "Analyzing provided papers", "stage": "analysis"},
                {"name": "structure_design", "description": "Designing review structure", "stage": "structure_design"},
                {"name": "content_writing", "description": "Writing review content", "stage": "content_writing"},
                {"name": "quality_review", "description": "Reviewing quality", "stage": "quality_review"},
                {"name": "finalization", "description": "Finalizing review", "stage": "finalization"}
            ]
        }
    
    def create_workflow_card(
        self,
        workflow_type: WorkflowType,
        title: str,
        description: str,
        input_parameters: Dict[str, Any]
    ) -> str:
        """Create a new workflow card"""
        workflow_id = str(uuid.uuid4())
        
        # Create workflow steps from template
        template_steps = self.workflow_templates.get(workflow_type, [])
        steps = []
        
        for i, step_template in enumerate(template_steps):
            step = WorkflowStep(
                step_id=f"{workflow_id}_step_{i+1}",
                name=step_template["name"],
                description=step_template["description"],
                status="pending"
            )
            steps.append(step)
        
        # Estimate completion time based on workflow type
        completion_estimates = {
            WorkflowType.COMPLETE_RESEARCH: "3-5 minutes",
            WorkflowType.PAPER_SEARCH_AUDITOR: "1-2 minutes",
            WorkflowType.PAPER_SCOUT: "30-60 seconds",
            WorkflowType.REVIEW_CREATION: "2-3 minutes",
            WorkflowType.STREAMLINED_REVIEW: "2-3 minutes"
        }
        
        workflow_card = WorkflowCard(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            title=title,
            description=description,
            current_stage=WorkflowStage.INITIALIZING,
            overall_progress=0.0,
            estimated_completion=completion_estimates.get(workflow_type, "2-3 minutes"),
            steps=steps,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            input_parameters=input_parameters
        )
        
        self.active_workflows[workflow_id] = workflow_card
        return workflow_id
    
    def update_workflow_progress(
        self,
        workflow_id: str,
        step_name: str,
        progress: float,
        status: str = "running",
        result_data: Optional[Dict[str, Any]] = None
    ):
        """Update workflow progress"""
        if workflow_id not in self.active_workflows:
            return
        
        workflow = self.active_workflows[workflow_id]
        
        # Find and update the step
        for step in workflow.steps:
            if step.name == step_name:
                step.status = status
                step.progress = progress
                step.result_data = result_data or {}
                
                if status == "running" and step.started_at is None:
                    step.started_at = datetime.now()
                elif status in ["completed", "failed"]:
                    step.completed_at = datetime.now()
                
                break
        
        # Update overall progress
        total_steps = len(workflow.steps)
        completed_steps = sum(1 for step in workflow.steps if step.status == "completed")
        running_steps = sum(step.progress for step in workflow.steps if step.status == "running")
        
        workflow.overall_progress = (completed_steps * 100 + running_steps) / total_steps
        
        # Update current stage
        current_step = next((step for step in workflow.steps if step.status == "running"), None)
        if current_step:
            stage_mapping = {
                "initialization": WorkflowStage.INITIALIZING,
                "paper_search": WorkflowStage.PAPER_COLLECTION,
                "initial_search": WorkflowStage.PAPER_COLLECTION,
                "quality_validation": WorkflowStage.QUALITY_VALIDATION,
                "quality_criticism": WorkflowStage.QUALITY_VALIDATION,
                "analysis": WorkflowStage.ANALYSIS,
                "gap_analysis": WorkflowStage.ANALYSIS,
                "paper_analysis": WorkflowStage.ANALYSIS,
                "structure_design": WorkflowStage.STRUCTURE_DESIGN,
                "review_structure": WorkflowStage.STRUCTURE_DESIGN,
                "content_writing": WorkflowStage.CONTENT_WRITING,
                "quality_review": WorkflowStage.QUALITY_REVIEW,
                "finalization": WorkflowStage.FINALIZATION
            }
            
            workflow.current_stage = stage_mapping.get(current_step.name, WorkflowStage.INITIALIZING)
        
        workflow.updated_at = datetime.now()
    
    def complete_workflow(
        self,
        workflow_id: str,
        final_results: Dict[str, Any],
        quality_metrics: Optional[Dict[str, Any]] = None
    ):
        """Mark workflow as completed"""
        if workflow_id not in self.active_workflows:
            return
        
        workflow = self.active_workflows[workflow_id]
        workflow.current_stage = WorkflowStage.COMPLETED
        workflow.overall_progress = 100.0
        workflow.final_results = final_results
        workflow.quality_metrics = quality_metrics or {}
        workflow.updated_at = datetime.now()
        
        # Mark all steps as completed
        for step in workflow.steps:
            if step.status == "running":
                step.status = "completed"
                step.progress = 100.0
                step.completed_at = datetime.now()
    
    def fail_workflow(
        self,
        workflow_id: str,
        error_message: str,
        failed_step: Optional[str] = None
    ):
        """Mark workflow as failed"""
        if workflow_id not in self.active_workflows:
            return
        
        workflow = self.active_workflows[workflow_id]
        workflow.current_stage = WorkflowStage.FAILED
        workflow.updated_at = datetime.now()
        
        # Mark failed step
        if failed_step:
            for step in workflow.steps:
                if step.name == failed_step:
                    step.status = "failed"
                    step.error_message = error_message
                    step.completed_at = datetime.now()
                    break
    
    def get_workflow_card(self, workflow_id: str) -> Optional[WorkflowCard]:
        """Get workflow card by ID"""
        return self.active_workflows.get(workflow_id)
    
    def list_active_workflows(self) -> List[WorkflowCard]:
        """List all active workflows"""
        return list(self.active_workflows.values())
    
    def format_workflow_for_display(self, workflow_id: str) -> Dict[str, Any]:
        """Format workflow card for UI display"""
        workflow = self.get_workflow_card(workflow_id)
        if not workflow:
            return {}
        
        # Format steps for display
        formatted_steps = []
        for step in workflow.steps:
            formatted_step = {
                "name": step.name.replace("_", " ").title(),
                "description": step.description,
                "status": step.status,
                "progress": step.progress,
                "duration": self._calculate_duration(step.started_at, step.completed_at),
                "icon": self._get_step_icon(step.name, step.status)
            }
            formatted_steps.append(formatted_step)
        
        # Format results based on workflow type
        formatted_results = self._format_results_by_type(workflow)
        
        return {
            "workflow_id": workflow.workflow_id,
            "type": workflow.workflow_type.value,
            "title": workflow.title,
            "description": workflow.description,
            "status": workflow.current_stage.value,
            "progress": {
                "percentage": round(workflow.overall_progress, 1),
                "current_stage": workflow.current_stage.value.replace("_", " ").title(),
                "estimated_completion": workflow.estimated_completion
            },
            "steps": formatted_steps,
            "timing": {
                "created_at": workflow.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": workflow.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": self._calculate_duration(workflow.created_at, workflow.updated_at)
            },
            "input_parameters": workflow.input_parameters,
            "results": formatted_results,
            "quality_metrics": workflow.quality_metrics
        }
    
    def _calculate_duration(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> str:
        """Calculate duration between timestamps"""
        if not start_time:
            return "Not started"
        
        end = end_time or datetime.now()
        duration = end - start_time
        
        if duration.total_seconds() < 60:
            return f"{int(duration.total_seconds())}s"
        elif duration.total_seconds() < 3600:
            return f"{int(duration.total_seconds() / 60)}m {int(duration.total_seconds() % 60)}s"
        else:
            hours = int(duration.total_seconds() / 3600)
            minutes = int((duration.total_seconds() % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def _get_step_icon(self, step_name: str, status: str) -> str:
        """Get icon for workflow step"""
        if status == "completed":
            return "✅"
        elif status == "running":
            return "🔄"
        elif status == "failed":
            return "❌"
        else:
            return "⏳"
    
    def _format_results_by_type(self, workflow: WorkflowCard) -> Dict[str, Any]:
        """Format results based on workflow type"""
        if not workflow.final_results:
            return {}
        
        if workflow.workflow_type == WorkflowType.COMPLETE_RESEARCH:
            return {
                "type": "literature_review",
                "paper_search": {
                    "papers_found": workflow.final_results.get("paper_search_results", {}).get("papers_found", 0),
                    "quality_grade": workflow.final_results.get("paper_search_results", {}).get("quality_grade", "N/A")
                },
                "literature_review": {
                    "word_count": workflow.final_results.get("literature_review", {}).get("word_count", 0),
                    "sections": workflow.final_results.get("literature_review", {}).get("sections_count", 0),
                    "content": workflow.final_results.get("literature_review", {}).get("final_review", "")
                },
                "recommendations": workflow.final_results.get("recommendations", [])
            }
        
        elif workflow.workflow_type == WorkflowType.PAPER_SEARCH_AUDITOR:
            return {
                "type": "paper_search_audit",
                "papers_found": len(workflow.final_results.get("final_papers", [])),
                "quality_grade": workflow.final_results.get("quality_metrics", {}).get("quality_metrics", {}).get("quality_grade", "N/A"),
                "audit_report": workflow.final_results.get("audit_report", ""),
                "papers": workflow.final_results.get("final_papers", [])
            }
        
        elif workflow.workflow_type == WorkflowType.PAPER_SCOUT:
            return {
                "type": "paper_search",
                "papers_found": len(workflow.final_results.get("papers", [])),
                "search_summary": workflow.final_results.get("search_summary", ""),
                "papers": workflow.final_results.get("papers", [])
            }
        
        else:
            return workflow.final_results

# Singleton instance
workflow_status_service = WorkflowStatusService()