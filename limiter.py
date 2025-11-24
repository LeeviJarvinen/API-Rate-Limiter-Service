import time
import threading
import redis
import json
import logging
from typing import Dict
from dataclasses import dataclass
logger = logging.getLogger(__name__)


@dataclass
class TokenRateLimit:
    max_token_capacity: int
    refill_rate: int


class RedisRateLimitStorage:
    """Storing and retreiving client data from redis"""
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def has_client(self, client_id):
        return self.redis.exists(f"client{client_id}")

    def get_client(self, client_id):
        data = self.redis.get(f"client:{client_id}")
        return json.loads(data) if data else None

    def add_client(self, client_id, data):
        self.redis.set(f"client:{client_id}", json.dumps(data))

    def update_client(self, client_id, data):
        self.redis.set(f"client:{client_id}", json.dumps(data))

    def cleanup_expired(self):
        pass


class RateLimitValidator:
    @staticmethod
    def validate_client_id(client_id):
        if not client_id or not isinstance(client_id, str):
            raise ValueError("Invalid client_id")

    @staticmethod
    def validate_bucket_rate_limit(rate_limit):
        if rate_limit.max_token_capacity <= 0 or rate_limit.refill_rate <= 0:
            raise ValueError("Invalid rate_limit")

    @staticmethod
    def validate_client_data(data, required):
        valid = True

        if not isinstance(data, Dict):
            valid = False

        for key, expected in required.items():
            if key not in data:
               valid = False
            if not isinstance(data[key], expected):
               valid = False
            if data[key] < 0:
               valid = False
            if not valid:
                raise ValueError("Invalid client_data")


class TokenBucketRateLimiter:
    def __init__(self):
        self.storage = RedisRateLimitStorage()

    def limit(self, max_token_capacity: int, refill_rate: int, token_cost: float = 1.0):
        """Decorator for rate limiting endpoints"""
        from functools import wraps
        from fastapi import HTTPException, Request
        
        rate_limit = TokenRateLimit(max_token_capacity=max_token_capacity, refill_rate=refill_rate)
        
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                request = kwargs.get('request')
                if not request:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                client_id = request.client.host if request and request.client else "unknown"
                
                if not self.is_allowed(client_id, rate_limit, token_cost):
                    raise HTTPException(status_code=429, detail="Too Many Requests")
                
                return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                request = kwargs.get('request')
                if not request:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                client_id = request.client.host if request and request.client else "unknown"
                
                if not self.is_allowed(client_id, rate_limit, token_cost):
                    raise HTTPException(status_code=429, detail="Too Many Requests")
                
                return func(*args, **kwargs)
            
            import inspect
            return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
        
        return decorator

    def is_allowed(self, client_id: str, rate_limit: TokenRateLimit, token_cost: float) -> bool:
        RateLimitValidator.validate_bucket_rate_limit(rate_limit)
        RateLimitValidator.validate_client_id(client_id)
        
        current_time = float(time.time())
        
        
        try:
            client_data = self.storage.get_client(client_id)
            if not client_data:
                data = {
                    "last_refill_time": current_time, 
                    "token": rate_limit.max_token_capacity
                }
                self.storage.add_client(client_id, data)
                client_data = data
                
            else:
                RateLimitValidator.validate_client_data(client_data, 
                   {"last_refill_time": (int, float), 
                    "token": (int, float)
                   })
                
            passed_time = current_time - client_data["last_refill_time"]
            
            client_data["token"] = min(
                rate_limit.max_token_capacity, 
                client_data["token"] + passed_time * rate_limit.refill_rate
            )
            
            client_data["last_refill_time"] = current_time
            
            if client_data.get("token") <= token_cost:
                self.storage.update_client(client_id, client_data)
                return False
  
            client_data["token"] -= token_cost
            self.storage.update_client(client_id, client_data)
            
            return True
        
        except Exception as e:
            logger.exception(f"Rate limiter error {e}")
            return False