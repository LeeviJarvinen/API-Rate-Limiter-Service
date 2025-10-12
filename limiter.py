import time
import threading
from typing import Dict
from dataclasses import dataclass

@dataclass
class WindowRateLimit:
    window_size: int
    max_requests: int

@dataclass
class TokenRateLimit:
    max_token_capacity: int
    refill_rate: int


class RateLimitStorage:
    """Storing and retreiving client data"""
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

class RateLimitValidator:
    @staticmethod
    def validate_client_id(client_id):
        if not client_id or not isinstance(client_id, str):
            return False
        return True

    @staticmethod
    def validate_window_rate_limit(rate_limit):
        if rate_limit.window_size <= 0 or rate_limit.max_requests <= 0:
            return False
        return True

    @staticmethod
    def validate_bucket_rate_limit(rate_limit):
        if rate_limit.max_token_capacity <= 0 or rate_limit.refill_rate <= 0:
            return False
        return True

    @staticmethod
    def validate_client_data(data, required):
        if not isinstance(data, Dict):
            return False

        for key, expected in required.items():
           if key not in data:
               return False
           if not isinstance(data[key], expected):
               return False
           if data[key] < 0:
               return False
           return True

    
class FixedWindowRateLimiter:
    def __init__(self):
        self.storage = RateLimitStorage()

    def is_allowed(self, client_id: str, rate_limit: Dict):
        if not RateLimitValidator.validate_client_id(client_id):
            raise ValueError("Invalid client_id")

        if not RateLimitValidator.validate_window_rate_limit(rate_limit):
            raise ValueError("RateLimit values must be greater than 0")


        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size


        try:
            client_data = self.storage.get_client(client_id)

            if client_data and not RateLimitValidator.validate_client_data(client_data, 
               {"window_start": (int), 
                "count": (int)
               }):

                print("invalid client data") #use logger here at some point instead of a print
                return False
         
            if not client_data:
                data = {
                    "window_start": current_window_start, 
                    "count": 0
                }
                self.storage.add_client(client_id, data)
                client_data = data

            if client_data.get("window_start") != current_window_start:
                data = {
                    "window_start": current_window_start,
                    "count": 0
                }
                self.storage.update_client(client_id, data)

            if client_data.get("count", 0) > rate_limit.max_requests:
                return False
            
            client_data["count"] += 1
            self.storage.update_client(client_id, client_data)
            return True

        except Exception as e:
            print(f"Rate limiter error {e}")
            return True 
        

class SlidingWindowRateLimiter:
    def __init__(self):
        self.storage = RateLimitStorage()

    def is_allowed(self, client_id: str, rate_limit: Dict):
        if not RateLimitValidator.validate_client_id(client_id):
            raise ValueError("Invalid client_id")

        if not RateLimitValidator.validate_window_rate_limit(rate_limit):
            raise ValueError("RateLimit values must be greater than 0")


        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size
        current_window_end = current_window_start + rate_limit.window_size
        client_data = self.storage.get_client(client_id)
        try:
            if client_data and not RateLimitValidator.validate_client_data(client_data, 
               {"window_start": (int),
                "current_count": (int),
                "prev_count": (int)
               }):

                print("invalid client data") #use logger here at some point instead of a print
                return False
         
            if not client_data:
                data = {
                    "window_start": current_window_start, 
                    "current_count": 0, 
                    "prev_count": 0
                }
                w_count = 0
                overlap = 0
                self.storage.add_client(client_id, data)
                client_data = data

            if client_data.get("window_start") != current_window_start:
                windows_passed = (current_window_start - client_data.get("window_start")) // rate_limit.window_size
                if windows_passed >= 2:
                    print("resetting windows")
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
            print(f"Rate limiter error {e}")
            return True 
        

class TokenBucketRateLimiter:
    def __init__(self):
        self.storage = RateLimitStorage()

    def is_allowed(self, client_id: str, rate_limit: Dict, token_cost: float):
        if not RateLimitValidator.validate_client_id(client_id):
            raise ValueError("Invalid client_id")

        if not RateLimitValidator.validate_bucket_rate_limit(rate_limit):
            raise ValueError("RateLimit values must be greater than 0")


        current_time = float(time.time())

        try:
            client_data = self.storage.get_client(client_id)

            if client_data and not RateLimitValidator.validate_client_data(client_data, 
               {"last_refill_time": (int, float), 
                "token": (int, float)
               }):

                print("invalid client data") #use logger here at some point instead of a print
                return False

            if not client_data:
                data = {
                    "last_refill_time": current_time, 
                    "token": rate_limit.max_token_capacity
                }
                self.storage.add_client(client_id, data)
                client_data = data

            passed_time = current_time - client_data["last_refill_time"]
            client_data["token"] = min(
                rate_limit.max_token_capacity, 
                client_data["token"] + passed_time * rate_limit.refill_rate
            )

            client_data["last_refill_time"] = current_time
            print(client_data["token"])
            if client_data.get("token") < token_cost:
                self.storage.update_client(client_id, client_data)
                return False
  
            client_data["token"] -= token_cost
            
            self.storage.update_client(client_id, client_data)
            return True

        except Exception as e:
            print(f"Rate limiter error {e}")
            return True 
 
