# import os
# import asyncio
# from typing import List, Dict, Any, AsyncGenerator
# import vertexai
# from vertexai.generative_models import GenerativeModel, ChatSession

# class GeminiService:
#     def __init__(self):
#         """Initialize the Gemini service with Google Cloud Vertex AI"""
#         self.initialized = False
#         # Try both environment variables
#         self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
#         self.location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
#         self.api_key = os.getenv('GOOGLE_CLOUD_API_KEY') or os.getenv('GOOGLE_API_KEY')
#         self.model = None
        
#         # 初期化を試みる
#         self._initialize()
    
#     def _initialize(self):
#         """Initialize Vertex AI client"""
#         try:
#             # Check if we have the necessary credentials
#             print(f"API Key available: {bool(self.api_key)}")
#             print(f"Project ID available: {bool(self.project_id)}")
            
#             if not self.project_id and not self.api_key:
#                 print("Warning: Neither GOOGLE_CLOUD_PROJECT nor GOOGLE_CLOUD_API_KEY is set")
#                 return False
            
#             # Initialize Vertex AI
#             if self.project_id:
#                 vertexai.init(project=self.project_id, location=self.location)
                
#                 # Initialize the default model
#                 self.model = GenerativeModel('gemini-2.0-flash-001')
#                 self.use_genai = False
#                 self.initialized = True
#                 print(f"Gemini service initialized successfully with project: {self.project_id}")
#                 return True
#         except Exception as e:
#             print(f"Failed to initialize Gemini service: {str(e)}")
#             # Fallback to google.generativeai if available
#             if self.api_key:
#                 try:
#                     import google.generativeai as genai
#                     genai.configure(api_key=self.api_key)
#                     self.use_genai = True
#                     self.initialized = True
#                     print("Gemini service initialized with google.generativeai (fallback)")
#                     return True
#                 except Exception as e2:
#                     print(f"Fallback also failed: {e2}")
#             return False
    
#     def _get_model(self, model_name: str) -> GenerativeModel:
#         """Get the appropriate model based on model name"""
#         if not self.initialized:
#             if not self._initialize():
#                 raise ValueError("Gemini service is not initialized")
        
#         # Map model IDs to actual Vertex AI model names
#         model_mapping = {
#             "gemini-2-0-flash-001": "gemini-2.0-flash-001",
#             "gemini-2-0-flash-lite-001": "gemini-2.0-flash-lite-001"
#         }
        
#         # Get the correct model name or use default
#         vertex_model_name = model_mapping.get(model_name, "gemini-2.0-flash-001")
        
#         return GenerativeModel(vertex_model_name)
    
#     async def send_message(self, model_name: str, history: List[Dict[str, str]], message: str) -> str:
#         """Send a message to Gemini and get a complete response"""
#         try:
#             if hasattr(self, 'use_genai') and self.use_genai:
#                 # Use google.generativeai
#                 import google.generativeai as genai
                
#                 # Map model names
#                 model_mapping = {
#                     "gemini-2-0-flash-001": "gemini-2.0-flash-001",
#                     "gemini-2-0-flash-lite-001": "gemini-2.0-flash-001"  # Use flash as fallback
#                 }
#                 genai_model_name = model_mapping.get(model_name, "gemini-2.0-flash-001")
                
#                 model = genai.GenerativeModel(genai_model_name)
                
#                 # Convert history to genai format
#                 genai_history = []
#                 for msg in history:
#                     role = "user" if msg["role"] == "user" else "model"
#                     genai_history.append({"role": role, "parts": msg["content"]})
                
#                 chat = model.start_chat(history=genai_history)
#                 response = chat.send_message(message)
#                 return response.text
#             else:
#                 # Use Vertex AI
#                 model = self._get_model(model_name)
                
#                 # Start a chat session
#                 chat = model.start_chat()
                
#                 # Add history messages to the chat
#                 for msg in history:
#                     role = msg["role"]
#                     content = msg["content"]
                    
#                     if role == "user":
#                         # Add user message to history
#                         chat._history.append({"role": "user", "parts": [{"text": content}]})
#                     elif role == "model":
#                         # Add model response to history
#                         chat._history.append({"role": "model", "parts": [{"text": content}]})
                
#                 # Send the new message
#                 response = chat.send_message(message)
#                 return response.text
            
#         except Exception as e:
#             print(f"Error sending message to Gemini: {str(e)}")
#             raise
    
#     async def stream_chat(self, model_name: str, history: List[Dict[str, str]], message: str) -> AsyncGenerator[str, None]:
#         """Stream a chat response from Gemini"""
#         try:
#             if hasattr(self, 'use_genai') and self.use_genai:
#                 # Use google.generativeai
#                 import google.generativeai as genai
                
#                 # Map model names
#                 model_mapping = {
#                     "gemini-2-0-flash-001": "gemini-2.0-flash-001",
#                     "gemini-2-0-flash-lite-001": "gemini-2.0-flash-001"  # Use flash as fallback
#                 }
#                 genai_model_name = model_mapping.get(model_name, "gemini-2.0-flash-001")
                
#                 model = genai.GenerativeModel(genai_model_name)
                
#                 # Convert history to genai format
#                 genai_history = []
#                 for msg in history:
#                     role = "user" if msg["role"] == "user" else "model"
#                     genai_history.append({"role": role, "parts": msg["content"]})
                
#                 chat = model.start_chat(history=genai_history)
#                 response = chat.send_message(message, stream=True)
                
#                 # Stream each chunk
#                 for chunk in response:
#                     if chunk.text:
#                         yield chunk.text
#                     await asyncio.sleep(0.01)
#             else:
#                 # Use Vertex AI
#                 model = self._get_model(model_name)
                
#                 # Start a chat session
#                 chat = model.start_chat()
                
#                 # Add history messages to the chat
#                 for msg in history:
#                     role = msg["role"]
#                     content = msg["content"]
                    
#                     if role == "user":
#                         # Add user message to history
#                         chat._history.append({"role": "user", "parts": [{"text": content}]})
#                     elif role == "model":
#                         # Add model response to history
#                         chat._history.append({"role": "model", "parts": [{"text": content}]})
                
#                 # Send the message and stream the response
#                 response = chat.send_message(message, stream=True)
                
#                 # Stream each chunk
#                 for chunk in response:
#                     yield chunk.text
#                     # Small delay to simulate streaming
#                     await asyncio.sleep(0.01)
                
#         except Exception as e:
#             print(f"Error streaming chat with Gemini: {str(e)}")
#             yield f"Error: {str(e)}"

# # Create a singleton instance
# gemini_service = GeminiService()
import os
import asyncio
from typing import List, Dict, Any, AsyncGenerator
import vertexai
from vertexai.generative_models import GenerativeModel, Part # Partを追加

class GeminiService:
    def __init__(self):
        """Initialize the Gemini service with Google Cloud Vertex AI"""
        self.initialized = False
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
        self.location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        
        if self.project_id:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                self.initialized = True
                print(f"Gemini service initialized successfully with project: {self.project_id}")
            except Exception as e:
                print(f"Failed to initialize Gemini service: {str(e)}")
        else:
            print("Warning: GOOGLE_CLOUD_PROJECT is not set. Gemini service will not be available.")

    def _get_model(self, model_name: str) -> GenerativeModel:
        """Get the appropriate generative model."""
        if not self.initialized:
            raise ValueError("Gemini service is not initialized.")
        # フロントエンドのIDをVertex AIのモデル名にマッピング
        model_mapping = {
            "gemini-2-0-flash-001": "gemini-1.5-flash-001", # ドキュメントにある安定版に合わせる例
            "gemini-1-5-pro": "gemini-1.5-pro-001",
            # 必要に応じて他のモデルマッピングを追加
        }
        # マッピングにない場合は、受け取ったIDをそのまま使用
        vertex_model_name = model_mapping.get(model_name, model_name)
        return GenerativeModel(vertex_model_name)
    
    def _prepare_contents(self, history: List[Dict[str, str]], message: str) -> List[Dict]:
        """Prepare the contents list for the Gemini API call."""
        # Vertex AIの'contents'パラメータの形式に変換
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [Part.from_text(msg["content"])]})
        
        # 最新のユーザーメッセージを追加
        contents.append({"role": "user", "parts": [Part.from_text(message)]})
        return contents

    async def send_message(self, model_name: str, history: List[Dict[str, str]], message: str) -> str:
        """Send a message to Gemini and get a complete response."""
        try:
            model = self._get_model(model_name)
            contents = self._prepare_contents(history, message)
            
            # generate_contentを直接呼び出す
            response = await model.generate_content_async(contents)
            return response.text
            
        except Exception as e:
            print(f"Error sending message to Gemini: {str(e)}")
            raise

    async def stream_chat(self, model_name: str, history: List[Dict[str, str]], message: str) -> AsyncGenerator[str, None]:
        """Stream a chat response from Gemini."""
        try:
            model = self._get_model(model_name)
            contents = self._prepare_contents(history, message)

            # generate_contentをストリーミングモードで呼び出す
            responses = model.generate_content(contents, stream=True)
            
            for response in responses:
                yield response.text
                await asyncio.sleep(0.01) # わずかな待機時間
                
        except Exception as e:
            print(f"Error streaming chat with Gemini: {str(e)}")
            yield f"Error: {str(e)}"

# Singleton instance
gemini_service = GeminiService()