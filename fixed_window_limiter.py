import time
import threading
from typing import Dict
from dataclasses import dataclass

@dataclass
class RateLimit:
    window_size: int
    max_requests: int

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
    def validate_client_id():
        pass

    @staticmethod
    def validate_rate_limit():
        pass

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
        if not client_id or not isinstance(client_id, str):
            raise ValueError("Invalid client_id")

        if rate_limit.window_size <= 0 or rate_limit.max_requests <= 0:
            raise ValueError("RateLimit values must be greater than 0")


        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size


        try:
            client_data = self.storage.get_client(client_id)

            if client_data and not RateLimitValidator.validate_client_data(client_data, 
               {"window_start": (int, float), 
                "count": (int, float)
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
        if client_id == None:
            raise ValueError("client_id cannot be None")
        if rate_limit.window_size <= 0 or rate_limit.max_requests <= 0:
            raise ValueError("RateLimit values must be positive")
        
        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size
        current_window_end = current_window_start + rate_limit.window_size
        client_data = self.storage.get_client(client_id)

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

