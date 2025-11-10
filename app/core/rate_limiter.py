# app/core/rate_limiter.py
import asyncio
import time
from collections import deque
from typing import Dict


class DomainRateLimiter:

    def __init__(self, default_max_calls: int = 60, window_seconds: int = 60):
        self.default_max_calls = default_max_calls
        self.window_seconds = window_seconds
        self._domain_map: Dict[str, deque] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def acquire(self, domain: str, max_calls: int = None):

        if max_calls is None:
            max_calls = self.default_max_calls

        if domain not in self._domain_map:
            self._domain_map[domain] = deque()
            self._locks[domain] = asyncio.Lock()

        dq = self._domain_map[domain]
        lock = self._locks[domain]

        while True:
            async with lock:
                now = time.monotonic()

                while dq and dq[0] <= now - self.window_seconds:
                    dq.popleft()

                if len(dq) < max_calls:
                    dq.append(now)
                    return

                wait_time = (dq[0] + self.window_seconds) - now

            await asyncio.sleep(wait_time if wait_time > 0 else 0.05)
