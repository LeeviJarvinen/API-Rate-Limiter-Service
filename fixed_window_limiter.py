import time
from typing import Dict
from dataclasses import dataclass

@dataclass
class RateLimit:
    window_size: int
    max_requests: int

class FixedWindowRateLimiter:
    def __init__(self):
        self.clients: Dict[str, Dict] = {}

    def is_allowed(self, client_id: str, rate_limit: Dict):
        current_time = time.time()
        current_window_start = (current_time // rate_limit.window_size) * rate_limit.window_size
        current_window_end = current_window_start + rate_limit.window_size

        if client_id not in self.clients:
            self.clients[client_id] = {"window_start": current_window_start, "count": 0} 

        if self.clients[client_id]["window_start"] != current_window_start:
            print("resetting")
            self.clients[client_id] = {"window_start": current_window_start, "count": 0}

        if self.clients[client_id]["count"] >= rate_limit.max_requests:
            return "rate limited by count"

        self.clients[client_id]["count"] += 1 
        return True
