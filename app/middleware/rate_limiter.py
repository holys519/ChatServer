"""
Rate Limiting ミドルウェア
"""
import time
import hashlib
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from threading import Lock
from app.core.config import settings

class TokenBucket:
    """トークンバケット算法によるレート制限"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """トークンを消費し、許可されるかどうかを返す"""
        with self.lock:
            now = time.time()
            
            # トークンを補充
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # トークンが足りるかチェック
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class SlidingWindowRateLimiter:
    """スライディングウィンドウによるレート制限"""
    
    def __init__(self, max_requests: int, window_size: int):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()
    
    def is_allowed(self, identifier: str) -> bool:
        """リクエストが許可されるかチェック"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_size
            
            # 古いリクエストを削除
            user_requests = self.requests[identifier]
            while user_requests and user_requests[0] < window_start:
                user_requests.popleft()
            
            # リクエスト数をチェック
            if len(user_requests) < self.max_requests:
                user_requests.append(now)
                return True
            return False

class RateLimitMiddleware:
    """レート制限ミドルウェア"""
    
    def __init__(self):
        # グローバルレート制限
        self.global_limiter = SlidingWindowRateLimiter(
            max_requests=settings.RATE_LIMIT_REQUESTS,
            window_size=settings.RATE_LIMIT_PERIOD
        )
        
        # ユーザー別レート制限
        self.user_limiters: Dict[str, TokenBucket] = {}
        self.user_limiters_lock = Lock()
        
        # APIエンドポイント別制限
        self.endpoint_limits = {
            "/api/chat/send": {"requests": 30, "window": 60},
            "/api/tasks/execute": {"requests": 10, "window": 60},
            "/api/sessions": {"requests": 50, "window": 60},
        }
        
        self.endpoint_limiters: Dict[str, Dict[str, SlidingWindowRateLimiter]] = defaultdict(dict)
    
    def get_user_limiter(self, user_id: str) -> TokenBucket:
        """ユーザー別のトークンバケットを取得"""
        with self.user_limiters_lock:
            if user_id not in self.user_limiters:
                self.user_limiters[user_id] = TokenBucket(
                    capacity=20,  # 20リクエスト/分
                    refill_rate=20/60  # 1秒あたり0.33トークン
                )
            return self.user_limiters[user_id]
    
    def get_endpoint_limiter(self, endpoint: str, identifier: str) -> Optional[SlidingWindowRateLimiter]:
        """エンドポイント別のレート制限を取得"""
        if endpoint not in self.endpoint_limits:
            return None
        
        if identifier not in self.endpoint_limiters[endpoint]:
            config = self.endpoint_limits[endpoint]
            self.endpoint_limiters[endpoint][identifier] = SlidingWindowRateLimiter(
                max_requests=config["requests"],
                window_size=config["window"]
            )
        
        return self.endpoint_limiters[endpoint][identifier]
    
    def get_client_identifier(self, request: Request) -> str:
        """クライアントの識別子を生成"""
        # 優先順位: User ID > IP Address
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # IPアドレスベース（プロキシ考慮）
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    async def __call__(self, request: Request, call_next):
        """ミドルウェアのメイン処理"""
        
        # ヘルスチェックやドキュメントは除外
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        identifier = self.get_client_identifier(request)
        endpoint = request.url.path
        
        # グローバルレート制限チェック
        if not self.global_limiter.is_allowed(identifier):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Global rate limit exceeded",
                    "retry_after": settings.RATE_LIMIT_PERIOD
                },
                headers={"Retry-After": str(settings.RATE_LIMIT_PERIOD)}
            )
        
        # ユーザー別レート制限チェック（認証済みユーザー）
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            user_limiter = self.get_user_limiter(user_id)
            if not user_limiter.consume():
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "User rate limit exceeded",
                        "retry_after": 60
                    },
                    headers={"Retry-After": "60"}
                )
        
        # エンドポイント別レート制限チェック
        endpoint_limiter = self.get_endpoint_limiter(endpoint, identifier)
        if endpoint_limiter and not endpoint_limiter.is_allowed(identifier):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Endpoint rate limit exceeded for {endpoint}",
                    "retry_after": self.endpoint_limits[endpoint]["window"]
                },
                headers={"Retry-After": str(self.endpoint_limits[endpoint]["window"])}
            )
        
        # リクエストを続行
        response = await call_next(request)
        
        # レート制限情報をヘッダーに追加
        remaining_requests = settings.RATE_LIMIT_REQUESTS - len(self.global_limiter.requests[identifier])
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining_requests))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + settings.RATE_LIMIT_PERIOD)
        
        return response

# シングルトンインスタンス
rate_limiter = RateLimitMiddleware()