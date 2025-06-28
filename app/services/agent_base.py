from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio
import uuid

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_google_vertexai import ChatVertexAI

from app.models.schemas import TaskProgress, TaskStatus, AgentStep
from app.services.task_service import task_service

class BaseAgent(ABC):
    """Base class for all CRA-Copilot agents"""
    
    def __init__(
        self, 
        name: str, 
        description: str,
        model_name: str = "gemini-2.0-flash-001",
        temperature: float = 0.7
    ):
        self.name = name
        self.description = description
        self.model_name = model_name
        self.temperature = temperature
        self.llm: Optional[BaseLanguageModel] = None
        self.tools: List[BaseTool] = []
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the language model"""
        try:
            from app.core.config import settings
            
            if settings.google_cloud_project:
                self.llm = ChatVertexAI(
                    model_name=self._map_model_name(self.model_name),
                    project=settings.google_cloud_project,
                    location=settings.vertex_ai_location,
                    temperature=self.temperature,
                    max_output_tokens=8192
                )
                print(f"✅ {self.name} agent initialized with Vertex AI")
            else:
                print(f"⚠️ {self.name} agent: Google Cloud not configured, using fallback")
                
        except Exception as e:
            print(f"❌ Error initializing LLM for {self.name}: {str(e)}")
    
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
    
    @abstractmethod
    async def execute(
        self, 
        task_id: str, 
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    @abstractmethod
    def get_prompt_template(self) -> ChatPromptTemplate:
        """Get the agent's prompt template"""
        pass
    
    async def create_step(
        self, 
        task_id: str, 
        action: str, 
        input_data: Dict[str, Any]
    ) -> str:
        """Create a new agent step"""
        step_id = str(uuid.uuid4())
        
        agent_step = AgentStep(
            step_id=step_id,
            task_id=task_id,
            agent_name=self.name,
            action=action,
            input_data=input_data,
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        
        # Save step to database (would be implemented with Firestore)
        print(f"🔧 {self.name}: Starting step '{action}' (ID: {step_id})")
        return step_id
    
    async def complete_step(
        self, 
        task_id: str, 
        step_id: str, 
        output_data: Dict[str, Any],
        status: TaskStatus = TaskStatus.COMPLETED
    ):
        """Complete an agent step"""
        print(f"✅ {self.name}: Completed step {step_id}")
        # Update step in database
    
    async def update_task_progress(
        self, 
        task_id: str, 
        progress_percentage: float,
        current_step: Optional[str] = None
    ):
        """Update the overall task progress"""
        await task_service.update_task_progress(
            task_id=task_id,
            progress_percentage=progress_percentage,
            current_step=current_step
        )
    
    async def invoke_llm(
        self, 
        messages: List[BaseMessage],
        tools: Optional[List[BaseTool]] = None
    ) -> str:
        """Invoke the language model with messages"""
        if not self.llm:
            return f"[Fallback] {self.name} agent response (LLM not initialized)"
        
        try:
            if tools:
                # Use tool calling if tools are provided
                llm_with_tools = self.llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await self.llm.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            print(f"❌ Error invoking LLM in {self.name}: {str(e)}")
            return f"[Error] {self.name} agent encountered an error: {str(e)}"
    
    def add_tool(self, tool: BaseTool):
        """Add a tool to the agent"""
        self.tools.append(tool)
        print(f"🔧 Added tool '{tool.name}' to {self.name} agent")
    
    def get_tools(self) -> List[BaseTool]:
        """Get all tools available to the agent"""
        return self.tools

class SimpleChatAgent(BaseAgent):
    """Simple chat agent for basic conversations"""
    
    def __init__(self):
        super().__init__(
            name="SimpleChatAgent",
            description="A basic conversational agent for simple chat interactions",
            model_name="gemini-2.0-flash-001",
            temperature=0.7
        )
    
    def get_prompt_template(self) -> ChatPromptTemplate:
        """Get the chat agent's prompt template"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant integrated into the CRA-Copilot system.
            
Your role is to provide helpful, accurate, and engaging responses to user queries.
You are part of a research-focused application, so you should be particularly good at:
- Explaining complex concepts clearly
- Providing structured information
- Helping with research-related tasks
- Being precise and factual

Always maintain a professional yet friendly tone."""),
            ("human", "{message}")
        ])
    
    async def execute(
        self, 
        task_id: str, 
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute simple chat interaction"""
        try:
            # Extract input
            message = input_data.get('message', '')
            history = input_data.get('history', [])
            
            # Update progress
            await self.update_task_progress(task_id, 25.0, "Processing message")
            
            # Create step
            step_id = await self.create_step(
                task_id=task_id,
                action="generate_response",
                input_data={"message": message, "history_length": len(history)}
            )
            
            # Prepare messages
            prompt = self.get_prompt_template()
            messages = []
            
            # Add history
            for hist_msg in history:
                if hist_msg.get('role') == 'user' or hist_msg.get('is_user'):
                    messages.append(HumanMessage(content=hist_msg.get('content', '')))
                else:
                    messages.append(AIMessage(content=hist_msg.get('content', '')))
            
            # Add current message
            formatted_prompt = prompt.format_messages(message=message)
            messages.extend(formatted_prompt)
            
            await self.update_task_progress(task_id, 50.0, "Generating response")
            
            # Generate response
            response = await self.invoke_llm(messages)
            
            await self.update_task_progress(task_id, 90.0, "Finalizing response")
            
            # Complete step
            output_data = {
                'response': response,
                'model_used': self.model_name,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.complete_step(task_id, step_id, output_data)
            
            return output_data
            
        except Exception as e:
            await self.complete_step(task_id, step_id, {}, TaskStatus.FAILED)
            raise Exception(f"SimpleChatAgent execution failed: {str(e)}")

class AgentOrchestrator:
    """Orchestrates multiple agents for complex tasks"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register default agents"""
        self.register_agent("simple_chat", SimpleChatAgent())
        
        # Import and register new agents
        try:
            from app.agents.paper_scout_agent import PaperScoutAgent
            self.register_agent("paper_scout", PaperScoutAgent())
        except ImportError as e:
            print(f"⚠️ Could not import PaperScoutAgent: {e}")
        
        try:
            from app.agents.review_creation_agent import ReviewCreationAgent
            self.register_agent("review_creation", ReviewCreationAgent())
        except ImportError as e:
            print(f"⚠️ Could not import ReviewCreationAgent: {e}")
        
        # Register new enhanced agents
        try:
            from app.agents.paper_critic_agent import PaperCriticAgent
            self.register_agent("paper_critic", PaperCriticAgent())
        except ImportError as e:
            print(f"⚠️ Could not import PaperCriticAgent: {e}")
        
        try:
            from app.agents.paper_reviser_agent import PaperReviserAgent
            self.register_agent("paper_reviser", PaperReviserAgent())
        except ImportError as e:
            print(f"⚠️ Could not import PaperReviserAgent: {e}")
        
        try:
            from app.agents.paper_search_auditor import PaperSearchAuditor
            self.register_agent("paper_search_auditor", PaperSearchAuditor())
        except ImportError as e:
            print(f"⚠️ Could not import PaperSearchAuditor: {e}")
    
    def register_agent(self, agent_id: str, agent: BaseAgent):
        """Register a new agent"""
        self.agents[agent_id] = agent
        print(f"🤖 Registered agent: {agent_id} ({agent.name})")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> Dict[str, str]:
        """List all registered agents"""
        return {
            agent_id: agent.description 
            for agent_id, agent in self.agents.items()
        }
    
    async def execute_task(
        self, 
        task_id: str,
        agent_id: str, 
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a task using the specified agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        print(f"🚀 Executing task {task_id} with agent {agent_id}")
        
        try:
            result = await agent.execute(task_id, input_data, config)
            print(f"✅ Task {task_id} completed successfully")
            return result
            
        except Exception as e:
            print(f"❌ Task {task_id} failed: {str(e)}")
            raise

# Singleton instance
agent_orchestrator = AgentOrchestrator()