"""
LangChain integration service for CRA-Copilot
Provides utilities and tools for LangChain-based agents
"""

import os
from typing import Dict, List, Any, Optional, Type
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models import BaseLanguageModel
from langchain_google_vertexai import ChatVertexAI
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import BaseModel, Field

class LangChainService:
    """Service for managing LangChain integrations"""
    
    def __init__(self):
        self.llm_cache: Dict[str, BaseLanguageModel] = {}
        self.tool_registry: Dict[str, BaseTool] = {}
        self._initialize_default_tools()
    
    def get_llm(
        self, 
        model_name: str = "gemini-2.0-flash-001",
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> BaseLanguageModel:
        """Get or create a language model instance"""
        cache_key = f"{model_name}_{temperature}_{max_tokens}"
        
        if cache_key not in self.llm_cache:
            try:
                from app.core.config import settings
                
                if settings.google_cloud_project:
                    self.llm_cache[cache_key] = ChatVertexAI(
                        model_name=self._map_model_name(model_name),
                        project=settings.google_cloud_project,
                        location=settings.vertex_ai_location,
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    )
                else:
                    raise ValueError("Google Cloud project not configured")
                    
            except Exception as e:
                print(f"❌ Error creating LLM: {str(e)}")
                raise
        
        return self.llm_cache[cache_key]
    
    def _map_model_name(self, model_name: str) -> str:
        """Map frontend model names to Vertex AI model names"""
        model_mapping = {
            "gemini-2-0-flash-001": "gemini-2.0-flash-001",
            "gemini-2-0-flash-lite-001": "gemini-2.0-flash-lite-001",
            "gemini-2-5-pro": "gemini-2.5-pro",
            "gemini-2-5-flash": "gemini-2.5-flash",
            "gemini-1-5-pro": "gemini-1.5-pro-001",
            "gemini-1-5-flash": "gemini-1.5-flash-001"
        }
        return model_mapping.get(model_name, "gemini-2.0-flash-001")
    
    def _initialize_default_tools(self):
        """Initialize default tools available to all agents"""
        try:
            # Web search tool
            search_tool = DuckDuckGoSearchRun()
            self.register_tool("web_search", search_tool)
            
            # Custom CRA-Copilot tools
            self.register_tool("format_response", FormatResponseTool())
            self.register_tool("extract_keywords", ExtractKeywordsTool())
            
        except Exception as e:
            print(f"⚠️ Error initializing default tools: {str(e)}")
    
    def register_tool(self, tool_name: str, tool: BaseTool):
        """Register a tool in the registry"""
        self.tool_registry[tool_name] = tool
        print(f"🔧 Registered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tool_registry.get(tool_name)
    
    def get_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """Get multiple tools by names"""
        tools = []
        for name in tool_names:
            tool = self.get_tool(name)
            if tool:
                tools.append(tool)
            else:
                print(f"⚠️ Tool not found: {name}")
        return tools
    
    def list_available_tools(self) -> Dict[str, str]:
        """List all available tools"""
        return {
            name: tool.description 
            for name, tool in self.tool_registry.items()
        }

# Custom Tools for CRA-Copilot

class FormatResponseInput(BaseModel):
    """Input for format response tool"""
    content: str = Field(description="The content to format")
    format_type: str = Field(description="The format type: 'markdown', 'structured', 'bullet_points'")

class FormatResponseTool(BaseTool):
    """Tool for formatting responses in different styles"""
    name = "format_response"
    description = "Format text content in different styles (markdown, structured, bullet points)"
    args_schema: Type[BaseModel] = FormatResponseInput
    
    def _run(self, content: str, format_type: str) -> str:
        """Format the content according to the specified type"""
        if format_type == "markdown":
            return self._format_markdown(content)
        elif format_type == "structured":
            return self._format_structured(content)
        elif format_type == "bullet_points":
            return self._format_bullet_points(content)
        else:
            return content
    
    async def _arun(self, content: str, format_type: str) -> str:
        """Async version of _run"""
        return self._run(content, format_type)
    
    def _format_markdown(self, content: str) -> str:
        """Format content as markdown"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                if line.startswith('Title:') or line.startswith('Conclusion:'):
                    formatted_lines.append(f"## {line}")
                elif line.startswith('Key Points:') or line.startswith('Summary:'):
                    formatted_lines.append(f"### {line}")
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append('')
        
        return '\n'.join(formatted_lines)
    
    def _format_structured(self, content: str) -> str:
        """Format content in a structured way"""
        return f"""
📋 **Structured Response**

📝 **Content:**
{content}

🎯 **Key Information:**
- Well-organized presentation
- Clear structure and flow
- Professional formatting

✅ **Response Complete**
        """.strip()
    
    def _format_bullet_points(self, content: str) -> str:
        """Format content as bullet points"""
        sentences = content.replace('\n', ' ').split('. ')
        bullet_points = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not sentence.endswith('.'):
                sentence += '.'
            if sentence:
                bullet_points.append(f"• {sentence}")
        
        return '\n'.join(bullet_points)

class ExtractKeywordsInput(BaseModel):
    """Input for extract keywords tool"""
    text: str = Field(description="The text to extract keywords from")
    max_keywords: int = Field(default=10, description="Maximum number of keywords to extract")

class ExtractKeywordsTool(BaseTool):
    """Tool for extracting keywords from text"""
    name = "extract_keywords"
    description = "Extract key terms and phrases from text content"
    args_schema: Type[BaseModel] = ExtractKeywordsInput
    
    def _run(self, text: str, max_keywords: int = 10) -> str:
        """Extract keywords from text"""
        import re
        from collections import Counter
        
        # Simple keyword extraction (can be enhanced with NLP libraries)
        # Remove punctuation and convert to lowercase
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'this', 'that', 'these', 'those'}
        
        # Filter words by length and stop words
        filtered_words = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Count word frequency
        word_counts = Counter(filtered_words)
        
        # Get top keywords
        top_keywords = [word for word, count in word_counts.most_common(max_keywords)]
        
        return ', '.join(top_keywords)
    
    async def _arun(self, text: str, max_keywords: int = 10) -> str:
        """Async version of _run"""
        return self._run(text, max_keywords)

# Custom research tools (placeholders for Phase 3)

@tool
def search_pubmed(query: str, max_results: int = 10) -> str:
    """
    Search PubMed for research papers
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results
    """
    # Placeholder implementation
    return f"PubMed search results for '{query}' (max: {max_results}) - Implementation pending in Phase 3"

@tool
def extract_paper_info(paper_id: str) -> str:
    """
    Extract detailed information from a research paper
    
    Args:
        paper_id: PubMed ID or DOI of the paper
    
    Returns:
        Structured paper information
    """
    # Placeholder implementation
    return f"Paper information for ID '{paper_id}' - Implementation pending in Phase 3"

@tool
def generate_citation(paper_info: dict, style: str = "apa") -> str:
    """
    Generate citation for a research paper
    
    Args:
        paper_info: Paper information dictionary
        style: Citation style (apa, mla, chicago)
    
    Returns:
        Formatted citation
    """
    # Placeholder implementation
    return f"Citation in {style} style - Implementation pending in Phase 3"

# Singleton instance
langchain_service = LangChainService()