"""
Command Service for MedAgent-Chat
Manages command discovery, suggestions, and help system
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re

class CommandCategory(Enum):
    """Command categories for organization"""
    RESEARCH = "research"
    PAPER_SEARCH = "paper_search"
    ANALYSIS = "analysis"
    REVIEW_CREATION = "review_creation"
    WORKFLOW = "workflow"
    MEDICAL = "medical"

@dataclass
class CommandInfo:
    """Information about a command"""
    name: str
    category: CommandCategory
    description: str
    usage: str
    examples: List[str]
    parameters: List[Dict[str, str]]
    complexity: str  # "beginner", "intermediate", "advanced"
    estimated_time: str
    prerequisites: List[str]

class CommandService:
    """Service for managing commands and suggestions"""
    
    def __init__(self):
        self.commands: Dict[str, CommandInfo] = {}
        self._register_default_commands()
    
    def _register_default_commands(self):
        """Register all available commands"""
        
        # Research workflow command
        self.commands["@research-workflow"] = CommandInfo(
            name="@research-workflow",
            category=CommandCategory.WORKFLOW,
            description="Complete research pipeline: paper search + quality validation + literature review creation",
            usage="@research-workflow <topic> [type:narrative|systematic] [audience:academic|general] [length:short|medium|long]",
            examples=[
                "@research-workflow machine learning in healthcare",
                "@research-workflow AI ethics type:systematic audience:general",
                "@research-workflow neural networks length:long type:narrative"
            ],
            parameters=[
                {"name": "topic", "type": "string", "required": "true", "description": "Research topic or query"},
                {"name": "type", "type": "enum", "required": "false", "description": "Review type: narrative, systematic", "default": "narrative"},
                {"name": "audience", "type": "enum", "required": "false", "description": "Target audience: academic, general", "default": "academic"},
                {"name": "length", "type": "enum", "required": "false", "description": "Review length: short, medium, long", "default": "medium"}
            ],
            complexity="intermediate",
            estimated_time="3-5 minutes",
            prerequisites=[]
        )
        
        # Paper search auditor command
        self.commands["@paper-scout-auditor"] = CommandInfo(
            name="@paper-scout-auditor",
            category=CommandCategory.PAPER_SEARCH,
            description="Enhanced paper search with multi-agent quality validation and improvement",
            usage="@paper-scout-auditor <query>",
            examples=[
                "@paper-scout-auditor deep learning medical diagnosis",
                "@paper-scout-auditor COVID-19 treatment effectiveness",
                "@paper-scout-auditor renewable energy storage solutions"
            ],
            parameters=[
                {"name": "query", "type": "string", "required": "true", "description": "Search query for academic papers"}
            ],
            complexity="beginner",
            estimated_time="1-2 minutes",
            prerequisites=[]
        )
        
        # Paper scout command
        self.commands["@paper-scout"] = CommandInfo(
            name="@paper-scout",
            category=CommandCategory.PAPER_SEARCH,
            description="Basic paper search and analysis from PubMed database",
            usage="@paper-scout <query>",
            examples=[
                "@paper-scout artificial intelligence",
                "@paper-scout climate change mitigation",
                "@paper-scout quantum computing applications"
            ],
            parameters=[
                {"name": "query", "type": "string", "required": "true", "description": "Search query for papers"}
            ],
            complexity="beginner",
            estimated_time="30 seconds - 1 minute",
            prerequisites=[]
        )
        
        # Review creation command
        self.commands["@review-creation"] = CommandInfo(
            name="@review-creation",
            category=CommandCategory.REVIEW_CREATION,
            description="Create literature review from provided papers (legacy - use @research-workflow for complete pipeline)",
            usage="@review-creation <topic>",
            examples=[
                "@review-creation machine learning applications"
            ],
            parameters=[
                {"name": "topic", "type": "string", "required": "true", "description": "Review topic"}
            ],
            complexity="advanced",
            estimated_time="2-3 minutes",
            prerequisites=["Requires papers to be pre-collected"]
        )
        
        # Paper critic command
        self.commands["@paper-critic"] = CommandInfo(
            name="@paper-critic",
            category=CommandCategory.ANALYSIS,
            description="Analyze and critique paper quality (requires papers from search)",
            usage="@paper-critic (used within workflows)",
            examples=[
                "Used automatically in @paper-scout-auditor and @research-workflow"
            ],
            parameters=[],
            complexity="advanced",
            estimated_time="Varies",
            prerequisites=["Papers from @paper-scout or @paper-scout-auditor"]
        )
        
        # Paper reviser command
        self.commands["@paper-reviser"] = CommandInfo(
            name="@paper-reviser",
            category=CommandCategory.ANALYSIS,
            description="Enhance and improve paper collections based on critic feedback",
            usage="@paper-reviser (used within workflows)",
            examples=[
                "Used automatically in @paper-scout-auditor and @research-workflow"
            ],
            parameters=[],
            complexity="advanced",
            estimated_time="Varies",
            prerequisites=["Paper critic analysis results"]
        )
        
        # Medical research command
        self.commands["@medical-research"] = CommandInfo(
            name="@medical-research",
            category=CommandCategory.MEDICAL,
            description="Evidence-based medical research with PICO framework analysis",
            usage="@medical-research task_type:<clinical_question|systematic_review|meta_analysis> question:\"<research question>\" [population:<population>] [intervention:<intervention>] [comparison:<comparison>] [outcome:<outcome>]",
            examples=[
                "@medical-research task_type:clinical_question question:\"高血圧患者においてACE阻害薬はARBより心血管イベントを減少させるか？\"",
                "@medical-research task_type:systematic_review question:\"Does metformin reduce cardiovascular mortality in type 2 diabetes?\" population:\"type 2 diabetes patients\" intervention:\"metformin\" comparison:\"placebo or other antidiabetics\" outcome:\"cardiovascular mortality\"",
                "@medical-research task_type:meta_analysis question:\"Effectiveness of statins in primary prevention of cardiovascular disease\""
            ],
            parameters=[
                {"name": "task_type", "description": "Type of medical research (clinical_question, systematic_review, meta_analysis)", "required": "true"},
                {"name": "question", "description": "Clinical research question in PICO format", "required": "true"},
                {"name": "population", "description": "Target population (P in PICO)", "required": "false"},
                {"name": "intervention", "description": "Intervention being studied (I in PICO)", "required": "false"},
                {"name": "comparison", "description": "Comparison group or control (C in PICO)", "required": "false"},
                {"name": "outcome", "description": "Primary outcome measures (O in PICO)", "required": "false"}
            ],
            complexity="advanced",
            estimated_time="15-30 minutes",
            prerequisites=["Access to medical databases", "Understanding of evidence-based medicine"]
        )
    
    def get_command_info(self, command_name: str) -> Optional[CommandInfo]:
        """Get information about a specific command"""
        return self.commands.get(command_name)
    
    def list_commands(self, category: Optional[CommandCategory] = None) -> List[CommandInfo]:
        """List all commands, optionally filtered by category"""
        if category:
            return [cmd for cmd in self.commands.values() if cmd.category == category]
        return list(self.commands.values())
    
    def search_commands(self, query: str) -> List[CommandInfo]:
        """Search commands by query in name, description, or examples"""
        query_lower = query.lower()
        results = []
        
        for cmd in self.commands.values():
            # Search in name, description, and examples
            if (query_lower in cmd.name.lower() or 
                query_lower in cmd.description.lower() or
                any(query_lower in example.lower() for example in cmd.examples)):
                results.append(cmd)
        
        return results
    
    def suggest_commands_for_intent(self, user_message: str) -> List[CommandInfo]:
        """Suggest commands based on user intent analysis"""
        message_lower = user_message.lower()
        suggestions = []
        
        # Intent patterns for research workflow
        research_patterns = [
            r'\b(literature review|systematic review|research review)\b',
            r'\b(comprehensive research|complete research)\b',
            r'\b(research on|study on|review on)\b',
            r'\b(create.*review|write.*review|generate.*review)\b'
        ]
        
        # Intent patterns for paper search
        search_patterns = [
            r'\b(find papers|search papers|look for papers)\b',
            r'\b(papers about|papers on|research papers)\b',
            r'\b(scientific literature|academic papers)\b',
            r'\b(pubmed search|database search)\b'
        ]
        
        # Intent patterns for analysis
        analysis_patterns = [
            r'\b(analyze papers|paper analysis|quality analysis)\b',
            r'\b(critique papers|evaluate papers|assess papers)\b',
            r'\b(paper quality|research quality)\b'
        ]
        
        # Check for research workflow intent
        if any(re.search(pattern, message_lower) for pattern in research_patterns):
            suggestions.append(self.commands["@research-workflow"])
        
        # Check for paper search intent
        if any(re.search(pattern, message_lower) for pattern in search_patterns):
            suggestions.append(self.commands["@paper-scout-auditor"])
            suggestions.append(self.commands["@paper-scout"])
        
        # Check for analysis intent
        if any(re.search(pattern, message_lower) for pattern in analysis_patterns):
            suggestions.append(self.commands["@paper-scout-auditor"])
        
        # Keyword-based suggestions
        keywords = {
            "machine learning": ["@research-workflow", "@paper-scout-auditor"],
            "ai": ["@research-workflow", "@paper-scout-auditor"],
            "medical": ["@research-workflow", "@paper-scout-auditor"],
            "healthcare": ["@research-workflow", "@paper-scout-auditor"],
            "covid": ["@paper-scout-auditor", "@paper-scout"],
            "climate": ["@research-workflow", "@paper-scout-auditor"],
            "quantum": ["@research-workflow", "@paper-scout-auditor"]
        }
        
        for keyword, command_names in keywords.items():
            if keyword in message_lower:
                for cmd_name in command_names:
                    if cmd_name in self.commands and self.commands[cmd_name] not in suggestions:
                        suggestions.append(self.commands[cmd_name])
        
        # If no specific intent detected, suggest most commonly used commands
        if not suggestions:
            suggestions = [
                self.commands["@research-workflow"],
                self.commands["@paper-scout-auditor"]
            ]
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def get_help_text(self, command_name: Optional[str] = None) -> str:
        """Generate help text for a command or all commands"""
        if command_name:
            cmd = self.get_command_info(command_name)
            if not cmd:
                return f"Command '{command_name}' not found."
            
            help_text = f"""# {cmd.name}

**Category**: {cmd.category.value.title()}
**Complexity**: {cmd.complexity.title()}
**Estimated Time**: {cmd.estimated_time}

## Description
{cmd.description}

## Usage
```
{cmd.usage}
```

## Parameters
"""
            for param in cmd.parameters:
                required = "Required" if param.get("required") == "true" else "Optional"
                default = f" (default: {param.get('default')})" if param.get('default') else ""
                help_text += f"- **{param['name']}** ({param['type']}, {required}): {param['description']}{default}\n"
            
            help_text += f"""
## Examples
"""
            for example in cmd.examples:
                help_text += f"```\n{example}\n```\n"
            
            if cmd.prerequisites:
                help_text += f"""
## Prerequisites
"""
                for prereq in cmd.prerequisites:
                    help_text += f"- {prereq}\n"
            
            return help_text
        
        else:
            # Generate overview of all commands
            help_text = """# MedAgent-Chat Commands

## Available Commands

### 🔬 Research Workflow
- **@research-workflow** - Complete research pipeline (recommended for most users)

### 📚 Paper Search & Analysis  
- **@paper-scout-auditor** - Enhanced paper search with quality validation
- **@paper-scout** - Basic paper search

### 📝 Specialized Commands (Advanced)
- **@review-creation** - Literature review creation (requires pre-collected papers)
- **@paper-critic** - Paper quality analysis (used in workflows)
- **@paper-reviser** - Paper collection enhancement (used in workflows)

## Quick Start
For most research tasks, try:
```
@research-workflow <your research topic>
```

For help with a specific command:
```
/help @command-name
```
"""
            return help_text
    
    def validate_command_syntax(self, command_text: str) -> Dict[str, Any]:
        """Validate command syntax and return validation result"""
        # Extract command name
        parts = command_text.strip().split()
        if not parts or not parts[0].startswith('@'):
            return {
                "valid": False,
                "error": "Commands must start with @",
                "suggestion": "Try @research-workflow or @paper-scout-auditor"
            }
        
        command_name = parts[0]
        cmd_info = self.get_command_info(command_name)
        
        if not cmd_info:
            # Find similar commands
            similar = self.search_commands(command_name[1:])  # Remove @
            suggestion = f"Did you mean {similar[0].name}?" if similar else "Use /help to see available commands"
            
            return {
                "valid": False,
                "error": f"Unknown command: {command_name}",
                "suggestion": suggestion
            }
        
        # Basic syntax validation (more detailed validation could be added)
        required_params = [p for p in cmd_info.parameters if p.get("required") == "true"]
        provided_args = len(parts) - 1
        
        if required_params and provided_args == 0:
            return {
                "valid": False,
                "error": f"Missing required parameter: {required_params[0]['name']}",
                "suggestion": f"Usage: {cmd_info.usage}"
            }
        
        return {
            "valid": True,
            "command": cmd_info,
            "message": f"Valid {command_name} command"
        }

# Singleton instance
command_service = CommandService()