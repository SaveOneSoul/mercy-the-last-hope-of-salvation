from __future__ import annotations
from collections import defaultdict, deque
from threading import Lock
import time


class SlidingWindowRateLimiter:
    def __init__(self, requests_per_minute: int):
        self.limit = requests_per_minute
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - 60.0
        with self.lock:
            q = self.events[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True
