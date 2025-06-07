from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional
from app.models.schemas import Message

class LLMService(ABC):
    """LLMサービスの基底クラス"""
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        model_id: str,
        history: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        LLMからレスポンスを生成する
        
        Args:
            prompt: ユーザーからの入力テキスト
            model_id: 使用するモデルのID
            history: 過去の会話履歴
            stream: ストリーミングレスポンスを使用するかどうか
            
        Yields:
            生成されたテキストの断片
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """利用可能なモデルのリストを取得する"""
        pass