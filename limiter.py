import time
import threading
import redis
import json
import logging
from typing import Dict
from dataclasses import dataclass
logger = logging.getLogger(__name__)

@dataclass
class WindowRateLimit:
    window_size: int
    max_requests: int

@dataclass
class TokenRateLimit:
    max_token_capacity: int
    refill_rate: int


class RateLimitStorage:
    """Storing and reteiving client data"""
    def __init__(self):
        self.clients: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def has_client(self, client_id):
        with self.lock:
            return client_id in self.clients

    def get_client(self, client_id):
        with self.lock:
            return self.clients.get(client_id)

    def add_client(self, client_id, data):
        with self.lock:
            self.clients[client_id] = data 

    def update_client(self, client_id, data):
        with self.lock:
            self.clients[client_id] = data 

    def cleanup_expired(self):
        pass


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
    def validate_window_rate_limit(rate_limit):
        if rate_limit.window_size <= 0 or rate_limit.max_requests <= 0:
            raise ValueError("Invalid rate_limit")

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

    
class FixedWindowRateLimiter:
    def __init__(self):
        self.storage = RedisRateLimitStorage()

    def is_allowed(self, client_id: str, rate_limit: WindowRateLimit) -> bool:
        RateLimitValidator.validate_window_rate_limit(rate_limit)
        RateLimitValidator.validate_client_id(client_id)

        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size


        try:
            client_data = self.storage.get_client(client_id)

            if not client_data:
                data = {
                    "window_start": current_window_start, 
                    "count": 0
                }
                self.storage.add_client(client_id, data)
                client_data = data
            else:
                RateLimitValidator.validate_client_data(client_data, 
                   {"window_start": (int,), 
                    "count": (int,)})
           
            if client_data.get("window_start") != current_window_start:
                data = {
                    "window_start": current_window_start,
                    "count": 0
                }
                client_data = data
                self.storage.update_client(client_id, data)
            
            if client_data.get("count", 0) > rate_limit.max_requests:
                return False
            
            client_data["count"] += 1
            self.storage.update_client(client_id, client_data)
            return True

        except Exception as e:
            logger.exception(f"Rate limiter error {e}")
            return False 
        

class SlidingWindowRateLimiter:
    def __init__(self):
        self.storage = RedisRateLimitStorage()

    def is_allowed(self, client_id: str, rate_limit: WindowRateLimit) -> bool:
        RateLimitValidator.validate_window_rate_limit(rate_limit)
        RateLimitValidator.validate_client_id(client_id)

        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size
        current_window_end = current_window_start + rate_limit.window_size

        try:
            client_data = self.storage.get_client(client_id)
            if not client_data:
                data = {
                    "window_start": current_window_start, 
                    "current_count": 0, 
                    "prev_count": 0
                }

                self.storage.add_client(client_id, data)
                client_data = data

            else:
                RateLimitValidator.validate_client_data(client_data, 
                   {"window_start": (int),
                    "current_count": (int),
                    "prev_count": (int)
                   })

            w_count = 0
            overlap = 0

            if client_data.get("window_start") != current_window_start:
                windows_passed = (current_window_start - client_data.get("window_start")) // rate_limit.window_size
                if windows_passed >= 2:
                    data = {
                        "window_start": current_window_start,
                        "current_count": 0, 
                        "prev_count": 0
                    }
                    client_data = data
                    self.storage.update_client(client_id, data)
                else:
                    data = {
                        "window_start": current_window_start,
                        "current_count": 0, 
                        "prev_count": client_data.get("current_count")
                    }
                    client_data = data
                    self.storage.update_client(client_id, data)

            overlap = (current_window_end - current_time) / rate_limit.window_size
            w_count = client_data.get("prev_count") * overlap + client_data.get("current_count")
            
            if w_count >= rate_limit.max_requests:
                return False

            client_data["current_count"] += 1
            self.storage.update_client(client_id, client_data)
            return True

        except Exception as e:
            logger.exception(f"Rate limiter error {e}")
            return False 
        

class TokenBucketRateLimiter:
    def __init__(self):
        self.storage = RedisRateLimitStorage()

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
 
