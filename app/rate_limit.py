from collections import defaultdict, deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._checks = 0

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._checks = 0

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_ip}"
        now = monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            self._checks += 1
            if self._checks % 128 == 0 or len(self._requests) >= 10_000:
                for existing_key in list(self._requests):
                    bucket = self._requests[existing_key]
                    while bucket and bucket[0] <= cutoff:
                        bucket.popleft()
                    if not bucket:
                        del self._requests[existing_key]
            if len(self._requests) >= 10_000 and key not in self._requests:
                raise HTTPException(status_code=503, detail="Rate limiter is at capacity.")

            bucket = self._requests[key]
            if len(bucket) >= self.limit:
                retry_after = ceil(self.window_seconds - (now - bucket[0]))
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(max(retry_after, 1))},
                )
            bucket.append(now)


register_rate_limit = RateLimiter(limit=10, window_seconds=60)
login_rate_limit = RateLimiter(limit=5, window_seconds=60)
