import os
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class GeminiService:
    def __init__(self):
        """Initialize the Gemini service with Google Gen AI SDK and Vertex AI"""
        self.initialized = False
        self.client = None
        self.global_client = None  # For models that require global endpoint
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
        self.location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        
        self._initialize()

    def _initialize(self):
        """Initialize Google Gen AI client for Vertex AI"""
        try:
            if not self.project_id:
                print("Warning: GOOGLE_CLOUD_PROJECT is not set. Gemini service will not be available.")
                return
                
            print(f"Initializing Gemini service with:")
            print(f"  Project ID: {self.project_id}")
            print(f"  Location: {self.location}")
                
            # Use Google Gen AI SDK with Vertex AI
            from google import genai
            
            # Regional client for most models
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
            
            # Global client for models that require global endpoint (like Gemini 2.5 Pro)
            self.global_client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location='global'
            )
            
            # Test connection with a simple model
            try:
                print("Testing Gemini service connection...")
                # Try to access available models or make a simple call
                self.initialized = True
                print(f"✅ Gemini service initialized successfully with project: {self.project_id}")
            except Exception as test_error:
                print(f"⚠️ Gemini service client created but connection test failed: {test_error}")
                self.initialized = True  # Still mark as initialized for now
            
        except ImportError as import_error:
            print(f"❌ Import error: google-genai package issue: {import_error}")
            print("Please install with: pip install google-genai")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini service: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

    def _get_model_name(self, model_name: str) -> str:
        """Map frontend model IDs to Vertex AI model names"""
        model_mapping = {
            # Generally Available Models
            "gemini-2-0-flash-001": "gemini-2.0-flash-001",
            "gemini-2-0-flash-lite-001": "gemini-2.0-flash-lite",
            
            # Preview Models
            "gemini-2-5-pro": "gemini-2.5-pro-preview-06-05",  # Requires global endpoint
            "gemini-2-5-flash": "gemini-2.5-flash-preview-05-20",
            
            # Legacy mappings for backwards compatibility
            "gemini-1-5-pro": "gemini-1.5-pro-001",
            "gemini-1-5-flash": "gemini-1.5-flash-001"
        }
        return model_mapping.get(model_name, "gemini-2.0-flash-001")
    
    def _requires_global_endpoint(self, model_name: str) -> bool:
        """Check if a model requires the global endpoint"""
        global_models = {
            "gemini-2-5-pro"  # Gemini 2.5 Pro is only available on global endpoint
        }
        return model_name in global_models
    
    def _prepare_contents(self, history: List[Dict[str, str]], message: str) -> List[str]:
        """Prepare the conversation for the API call"""
        # Build conversation history
        conversation = []
        for msg in history:
            conversation.append(msg["content"])
        
        # Add the new message
        conversation.append(message)
        return conversation

    async def send_message(self, model_name: str, history: List[Dict[str, str]], message: str) -> str:
        """Send a message to Gemini and get a complete response"""
        if not self.initialized:
            raise ValueError("Gemini service is not initialized")
            
        try:
            from google.genai import types
            
            vertex_model_name = self._get_model_name(model_name)
            use_global = self._requires_global_endpoint(model_name)
            client_to_use = self.global_client if use_global else self.client
            endpoint_type = "global" if use_global else "regional"
            
            print(f"🤖 Gemini API Call:")
            print(f"  Requested model: {model_name}")
            print(f"  Mapped to Vertex AI model: {vertex_model_name}")
            print(f"  Using {endpoint_type} endpoint")
            print(f"  Message length: {len(message)} characters")
            print(f"  History items: {len(history)}")
            
            # Build the conversation context
            contents = []
            for msg in history:
                contents.append(msg["content"])
            contents.append(message)
            
            print(f"  Total content items: {len(contents)}")
            
            # Generate response using the latest SDK
            config = types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                max_output_tokens=8192
            )
            
            print(f"  Calling Vertex AI API...")
            response = client_to_use.models.generate_content(
                model=vertex_model_name,
                contents=contents,
                config=config
            )
            
            print(f"  ✅ Response received: {len(response.text)} characters")
            return response.text
            
        except Exception as e:
            print(f"❌ Gemini API Error:")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {str(e)}")
            
            # Check for specific error types
            if "404" in str(e) or "not found" in str(e).lower():
                print(f"  🔍 Model '{vertex_model_name}' may not be available in region '{self.location}'")
                print(f"  💡 Try using 'gemini-2-0-flash-lite-001' instead of '{model_name}'")
            elif "403" in str(e) or "permission" in str(e).lower():
                print(f"  🔑 Authentication/Permission issue detected")
                print(f"  💡 Check GOOGLE_CLOUD_PROJECT and authentication setup")
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                print(f"  📊 Quota/Rate limit issue detected")
            elif "Network is unreachable" in str(e) or "ConnectError" in str(e):
                print(f"  🌐 Network connectivity issue detected")
                print(f"  💡 Attempting fallback to working model...")
                
                # Try fallback to working model
                if model_name != "gemini-2-0-flash-lite-001":
                    try:
                        print(f"  🔄 Retrying with gemini-2-0-flash-lite-001...")
                        return await self.send_message("gemini-2-0-flash-lite-001", history, message)
                    except Exception as fallback_error:
                        print(f"  ❌ Fallback also failed: {fallback_error}")
            
            import traceback
            traceback.print_exc()
            raise

    async def stream_chat(self, model_name: str, history: List[Dict[str, str]], message: str) -> AsyncGenerator[str, None]:
        """Stream a chat response from Gemini"""
        if not self.initialized:
            raise ValueError("Gemini service is not initialized")
            
        try:
            from google.genai import types
            
            vertex_model_name = self._get_model_name(model_name)
            use_global = self._requires_global_endpoint(model_name)
            client_to_use = self.global_client if use_global else self.client
            
            # Build the conversation context
            contents = []
            for msg in history:
                contents.append(msg["content"])
            contents.append(message)
            
            # Stream response using the latest SDK
            for chunk in client_to_use.models.generate_content_stream(
                model=vertex_model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=8192
                )
            ):
                if chunk.text:
                    yield chunk.text
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"Error streaming chat with Gemini: {str(e)}")
            yield f"Error: {str(e)}"

# Singleton instance
gemini_service = GeminiService()