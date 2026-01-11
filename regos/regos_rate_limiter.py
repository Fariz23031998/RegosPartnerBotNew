import asyncio
import time

class RegosRateLimiter:
    def __init__(self, rate: float = 2.0, burst: int = 50):
        """
        rate: tokens added per second (2 = 2 requests/second)
        burst: max tokens stored (50 = burst capacity)
        """
        self.rate = rate
        self.capacity = burst
        self.tokens = burst
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            # Refill bucket based on time passed
            elapsed = now - self.updated_at
            self.updated_at = now
            self.tokens = min(self.capacity, int(self.tokens + elapsed * self.rate))

            # If bucket empty → wait for enough tokens
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0  # prevent overshoot
            else:
                self.tokens -= 1
