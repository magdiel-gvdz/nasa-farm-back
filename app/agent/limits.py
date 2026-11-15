"""Límites de uso del chat: por cliente (minuto y día) y presupuesto diario global.

El contador por minuto vive en memoria de cada instancia; los diarios son contadores atómicos
en la tabla del entorno, así que se comparten entre instancias y caducan solos al día siguiente.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.store.base import Repository

logger = logging.getLogger(__name__)
GLOBAL_PARTITION = "__chat__"


@dataclass(frozen=True)
class ChatLimits:
    per_minute: int = 6
    per_day: int = 80
    daily_budget: int = 1500
    max_message_chars: int = 2000
    max_output_tokens: int = 2048


class LimitExceeded(Exception):
    def __init__(self, code: str, status_code: int, retry_after: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.status_code = status_code
        self.retry_after = retry_after
        self.reason = reason


def _short(client_id: str) -> str:
    return client_id[:8]


class RateLimiter:
    def __init__(self, repo: Repository, limits: ChatLimits, clock=time.time):
        self._repo = repo
        self._limits = limits
        self._clock = clock
        self._recent: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _seconds_to_midnight(self, now: float) -> tuple[str, int, int]:
        moment = datetime.fromtimestamp(now, UTC)
        tomorrow = (moment + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            moment.strftime("%Y-%m-%d"),
            int((tomorrow - moment).total_seconds()) + 1,
            int(tomorrow.timestamp()) + 86_400,
        )

    def check(self, client_id: str) -> None:
        """Cuenta un mensaje del cliente o lanza `LimitExceeded` sin contarlo para el modelo."""
        now = self._clock()
        with self._lock:
            recent = self._recent[client_id]
            while recent and now - recent[0] >= 60:
                recent.popleft()
            if len(recent) >= self._limits.per_minute:
                retry = int(60 - (now - recent[0])) + 1
                logger.warning("Chat limitado: cliente %s, motivo per_minute", _short(client_id))
                raise LimitExceeded("rate_limited", 429, retry, "per_minute")
            recent.append(now)
        day, to_midnight, expires = self._seconds_to_midnight(now)
        used = self._repo.increment(client_id, f"chatday#{day}", expires_at=expires)
        if used > self._limits.per_day:
            logger.warning("Chat limitado: cliente %s, motivo per_day", _short(client_id))
            raise LimitExceeded("rate_limited", 429, to_midnight, "per_day")
        total = self._repo.increment(GLOBAL_PARTITION, f"budget#{day}", expires_at=expires)
        logger.info("Chat: mensaje %d del día (presupuesto %d)", total, self._limits.daily_budget)
        if total > self._limits.daily_budget:
            logger.warning("Chat limitado: cliente %s, motivo daily_budget", _short(client_id))
            raise LimitExceeded("chat_budget_exhausted", 503, to_midnight, "daily_budget")
