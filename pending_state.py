"""
Conversation state shared by every worker process.

Language selection and registration confirmation are stored on disk so a
later Telegram update can be handled by a different worker than the one
that asked the question.
"""
import fcntl
import json
import os
import time
from pathlib import Path

from config import DATABASE_PATH

PENDING_TTL_SECONDS = 30 * 60


def pending_state_path() -> Path:
    db_path = Path(DATABASE_PATH)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    return db_path.with_name("bot_pending_state.json")


class SharedDict:
    """Process-safe mapping persisted in one JSON file, keyed by bucket."""

    def __init__(self, path: Path, bucket: str, ttl_seconds: int = PENDING_TTL_SECONDS):
        self.path = path
        self.bucket = bucket
        self.ttl_seconds = ttl_seconds

    def get(self, key, default=None):
        key = str(key)

        def read(bucket: dict):
            stored = bucket.get(key)
            if not isinstance(stored, dict):
                return default
            saved_at = stored.get("_saved_at", 0)
            if self.ttl_seconds and time.time() - saved_at > self.ttl_seconds:
                bucket.pop(key, None)
                return default
            return {item_key: item_value for item_key, item_value in stored.items() if item_key != "_saved_at"}

        return self._mutate(read)

    def __setitem__(self, key, value):
        key = str(key)
        stored = dict(value)
        stored["_saved_at"] = time.time()

        def write(bucket: dict):
            bucket[key] = stored

        self._mutate(write)

    def __delitem__(self, key):
        key = str(key)

        def remove(bucket: dict):
            if key not in bucket:
                raise KeyError(key)
            del bucket[key]

        self._mutate(remove)

    def __contains__(self, key) -> bool:
        return self.get(key) is not None

    def _mutate(self, fn):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                handle.seek(0)
                raw = handle.read()
                data = json.loads(raw) if raw.strip() else {}
                if not isinstance(data, dict):
                    data = {}
                bucket = data.get(self.bucket)
                if not isinstance(bucket, dict):
                    bucket = {}
                    data[self.bucket] = bucket
                result = fn(bucket)
                handle.seek(0)
                handle.truncate()
                json.dump(data, handle)
                handle.flush()
                os.fsync(handle.fileno())
                return result
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
