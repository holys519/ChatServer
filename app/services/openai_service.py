import os
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from dotenv import load_dotenv
from openai import AsyncOpenAI
load_dotenv()

class OpenAIService:
    def __init__(self):
        """Initialize the OpenAI service"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.initialized = self.api_key is not None
        
        if self.initialized:
            self.client = AsyncOpenAI(api_key=self.api_key)
            print("OpenAI service initialized successfully")
        else:
            print("Warning: OPENAI_API_KEY is not set")
    
    async def send_message(self, model_name: str, history: List[Dict[str, str]], message: str) -> str:
        """Send a message to OpenAI and get a complete response"""
        try:
            if not self.initialized:
                raise ValueError("OpenAI service is not initialized")
            
            # Map model IDs to actual OpenAI model names
            model_mapping = {
                "gpt4o-mini": "gpt-4o-mini",
                "gpt4o": "gpt-4o",
                # Add more mappings as needed
            }
            
            # Get the correct model name or use default
            openai_model_name = model_mapping.get(model_name, "gpt-4o-mini")
            
            # Convert history to OpenAI format
            messages = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
            
            # Add the new message
            messages.append({"role": "user", "content": message})
            
            # Send request to OpenAI
            response = await self.client.chat.completions.create(
                model=openai_model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract and return the response text
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error sending message to OpenAI: {str(e)}")
            raise
    
    async def stream_chat(self, model_name: str, history: List[Dict[str, str]], message: str) -> AsyncGenerator[str, None]:
        """Stream a chat response from OpenAI"""
        try:
            if not self.initialized:
                raise ValueError("OpenAI service is not initialized")
            
            # Map model IDs to actual OpenAI model names
            model_mapping = {
                "gpt4o-mini": "gpt-4o-mini",
                "gpt4o": "gpt-4o",
                # Add more mappings as needed
            }
            
            # Get the correct model name or use default
            openai_model_name = model_mapping.get(model_name, "gpt-4o-mini")
            
            # Convert history to OpenAI format
            messages = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
            
            # Add the new message
            messages.append({"role": "user", "content": message})
            
            # Send streaming request to OpenAI
            stream = await self.client.chat.completions.create(
                model=openai_model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=True
            )
            
            # Stream each chunk
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"Error streaming chat with OpenAI: {str(e)}")
            yield f"Error: {str(e)}"

# Create a singleton instance
openai_service = OpenAIService()