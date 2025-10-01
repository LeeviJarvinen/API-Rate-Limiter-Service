import time
import threading
from typing import Dict
from dataclasses import dataclass

@dataclass
class RateLimit:
    window_size: int
    max_requests: int

class RateLimiterStorage:
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

class FixedWindowRateLimiter:
    def __init__(self):
        self.storage = RateLimiterStorage()

    def is_allowed(self, client_id: str, rate_limit: Dict):
        if not client_id or not isinstance(client_id, str):
            raise ValueError("Invalid client_id")

        if rate_limit.window_size <= 0 or rate_limit.max_requests <= 0:
            raise ValueError("RateLimit values must be greater than 0")


        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size


        try:
            client_data = self.storage.get_client(client_id)

            if client_data and not self._validate_client_data(client_data):
                print("invalid client data")
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
        
    def _validate_client_data(self, client_data):
        if not isinstance(client_data, dict):
            return False
        required = {
            "window_start": (int),
            "count": (int)
        }

        for key, expected in required.items():
            if key not in client_data:
                return False
            if not isinstance(client_data[key], expected):
                return False
            if client_data[key] < 0:
                return False
            return True

class SlidingWindowRateLimiter:
    def __init__(self):
        self.storage = RateLimiterStorage()

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

