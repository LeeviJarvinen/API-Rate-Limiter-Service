import time
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

    def get_client(self, client_id):
        if client_id in self.clients:
            return self.clients[client_id]

        return client_id in self.clients

    def add_client(self, client_id, data):
        self.clients[client_id] = data 

    def update_client(self, client_id, data):
        self.clients[client_id] = data 

    def cleanup_expired(self):
        pass

class FixedWindowRateLimiter:
    def __init__(self):
        self.storage = RateLimiterStorage()

    def is_allowed(self, client_id: str, rate_limit: Dict):
        if client_id == None:
            raise ValueError("client_id cannot be None")
        if rate_limit.window_size <= 0 or rate_limit.max_requests <= 0:
            raise ValueError("RateLimit values must be positive")
        
        current_time = int(time.time())
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size

        if not self.storage.get_client(client_id):
            data = {"window_start": current_window_start, "count": 0}
            self.storage.add_client(client_id, data)
        
        if self.storage.get_client(client_id)["window_start"] != current_window_start:
            data = {"window_start": current_window_start, "count": 0}
            self.storage.add_client(client_id, data)

        if self.storage.get_client(client_id)["count"] > rate_limit.max_requests:
            return False

        self.storage.get_client(client_id)["count"] += 1
        return True
