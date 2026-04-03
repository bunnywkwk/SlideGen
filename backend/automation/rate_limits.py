from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock


@dataclass(frozen=True)
class LimitStatus:
    limit: int
    used: int
    remaining: int
    week_key: str


class WeeklyExportLimiter:
    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}
        self._lock = Lock()

    def consume(self, client_id: str, limit: int) -> LimitStatus:
        if limit <= 0 or self._is_local_client(client_id):
            return LimitStatus(limit=limit, used=0, remaining=max(limit, 0), week_key=self._week_key())

        week_key = self._week_key()
        cache_key = (client_id, week_key)

        with self._lock:
            self._prune_unlocked(active_week_key=week_key)
            used = self._counts.get(cache_key, 0)
            if used >= limit:
                raise WeeklyLimitExceeded(limit=limit, used=used, week_key=week_key)
            used += 1
            self._counts[cache_key] = used

        return LimitStatus(limit=limit, used=used, remaining=max(limit - used, 0), week_key=week_key)

    def _prune_unlocked(self, active_week_key: str) -> None:
        stale_keys = [key for key in self._counts if key[1] != active_week_key]
        for key in stale_keys:
            self._counts.pop(key, None)

    @staticmethod
    def _week_key() -> str:
        now = datetime.now(UTC)
        iso_year, iso_week, _ = now.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    @staticmethod
    def _is_local_client(client_id: str) -> bool:
        return client_id in {"127.0.0.1", "::1", "localhost"}


class WeeklyLimitExceeded(Exception):
    def __init__(self, *, limit: int, used: int, week_key: str) -> None:
        super().__init__(f"Weekly export limit reached ({used}/{limit}) for {week_key}.")
        self.limit = limit
        self.used = used
        self.week_key = week_key


weekly_export_limiter = WeeklyExportLimiter()
