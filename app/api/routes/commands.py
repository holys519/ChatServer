"""
Commands API for CRA-Copilot
Provides command discovery, suggestions, and help endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.services.command_service import command_service, CommandCategory

router = APIRouter()

class CommandSuggestionRequest(BaseModel):
    """Request for command suggestions"""
    message: str
    context: Optional[Dict[str, Any]] = None

class CommandValidationRequest(BaseModel):
    """Request for command validation"""
    command: str

class CommandInfoResponse(BaseModel):
    """Response with command information"""
    name: str
    category: str
    description: str
    usage: str
    examples: List[str]
    parameters: List[Dict[str, str]]
    complexity: str
    estimated_time: str
    prerequisites: List[str]

class CommandSuggestionResponse(BaseModel):
    """Response with command suggestions"""
    suggestions: List[CommandInfoResponse]
    intent_detected: str
    confidence: float

class CommandValidationResponse(BaseModel):
    """Response with command validation result"""
    valid: bool
    error: Optional[str] = None
    suggestion: Optional[str] = None
    command_info: Optional[CommandInfoResponse] = None

@router.get("/list")
async def list_commands(
    category: Optional[str] = Query(None, description="Filter by category")
) -> List[CommandInfoResponse]:
    """List all available commands, optionally filtered by category"""
    try:
        # Parse category if provided
        filter_category = None
        if category:
            try:
                filter_category = CommandCategory(category.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        commands = command_service.list_commands(filter_category)
        
        return [
            CommandInfoResponse(
                name=cmd.name,
                category=cmd.category.value,
                description=cmd.description,
                usage=cmd.usage,
                examples=cmd.examples,
                parameters=cmd.parameters,
                complexity=cmd.complexity,
                estimated_time=cmd.estimated_time,
                prerequisites=cmd.prerequisites
            )
            for cmd in commands
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def get_categories() -> List[Dict[str, str]]:
    """Get all available command categories"""
    return [
        {"value": category.value, "label": category.value.replace("_", " ").title()}
        for category in CommandCategory
    ]

@router.post("/suggest")
async def suggest_commands(request: CommandSuggestionRequest) -> CommandSuggestionResponse:
    """Get command suggestions based on user message"""
    try:
        suggestions = command_service.suggest_commands_for_intent(request.message)
        
        # Detect intent type
        intent_detected = "research"
        confidence = 0.8
        
        message_lower = request.message.lower()
        if any(word in message_lower for word in ["search", "find", "papers", "pubmed"]):
            intent_detected = "paper_search"
            confidence = 0.9
        elif any(word in message_lower for word in ["review", "literature", "systematic"]):
            intent_detected = "review_creation"
            confidence = 0.9
        elif any(word in message_lower for word in ["analyze", "critique", "quality"]):
            intent_detected = "analysis"
            confidence = 0.85
        elif any(word in message_lower for word in ["workflow", "complete", "comprehensive"]):
            intent_detected = "workflow"
            confidence = 0.95
        
        return CommandSuggestionResponse(
            suggestions=[
                CommandInfoResponse(
                    name=cmd.name,
                    category=cmd.category.value,
                    description=cmd.description,
                    usage=cmd.usage,
                    examples=cmd.examples,
                    parameters=cmd.parameters,
                    complexity=cmd.complexity,
                    estimated_time=cmd.estimated_time,
                    prerequisites=cmd.prerequisites
                )
                for cmd in suggestions
            ],
            intent_detected=intent_detected,
            confidence=confidence
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
async def validate_command(request: CommandValidationRequest) -> CommandValidationResponse:
    """Validate command syntax and parameters"""
    try:
        validation_result = command_service.validate_command_syntax(request.command)
        
        response = CommandValidationResponse(
            valid=validation_result["valid"],
            error=validation_result.get("error"),
            suggestion=validation_result.get("suggestion")
        )
        
        # Add command info if valid
        if validation_result["valid"] and "command" in validation_result:
            cmd = validation_result["command"]
            response.command_info = CommandInfoResponse(
                name=cmd.name,
                category=cmd.category.value,
                description=cmd.description,
                usage=cmd.usage,
                examples=cmd.examples,
                parameters=cmd.parameters,
                complexity=cmd.complexity,
                estimated_time=cmd.estimated_time,
                prerequisites=cmd.prerequisites
            )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_commands(
    q: str = Query(..., description="Search query")
) -> List[CommandInfoResponse]:
    """Search commands by name, description, or examples"""
    try:
        results = command_service.search_commands(q)
        
        return [
            CommandInfoResponse(
                name=cmd.name,
                category=cmd.category.value,
                description=cmd.description,
                usage=cmd.usage,
                examples=cmd.examples,
                parameters=cmd.parameters,
                complexity=cmd.complexity,
                estimated_time=cmd.estimated_time,
                prerequisites=cmd.prerequisites
            )
            for cmd in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/help")
async def get_help(
    command: Optional[str] = Query(None, description="Specific command to get help for")
) -> Dict[str, str]:
    """Get help text for a command or all commands"""
    try:
        help_text = command_service.get_help_text(command)
        return {"help": help_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{command_name}/info")
async def get_command_info(command_name: str) -> CommandInfoResponse:
    """Get detailed information about a specific command"""
    try:
        # Ensure command name starts with @
        if not command_name.startswith('@'):
            command_name = '@' + command_name
        
        cmd = command_service.get_command_info(command_name)
        if not cmd:
            raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")
        
        return CommandInfoResponse(
            name=cmd.name,
            category=cmd.category.value,
            description=cmd.description,
            usage=cmd.usage,
            examples=cmd.examples,
            parameters=cmd.parameters,
            complexity=cmd.complexity,
            estimated_time=cmd.estimated_time,
            prerequisites=cmd.prerequisites
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))