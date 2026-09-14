"""Small retry helper for transient Firestore / Google API errors (e.g. 429 RESOURCE_EXHAUSTED)."""

import logging
import time
from typing import Callable, TypeVar

from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Covers quota/rate spikes and short outages; aligns with Google's retry hints for 429.
_TRANSIENT: tuple[type[BaseException], ...] = (
    google_exceptions.ResourceExhausted,
    google_exceptions.TooManyRequests,
    google_exceptions.ServiceUnavailable,
    google_exceptions.DeadlineExceeded,
    google_exceptions.Aborted,
)


def firestore_call_with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay_sec: float = 0.5,
) -> T:
    """Run ``fn``. On transient errors, backoff and retry."""
    last: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except _TRANSIENT as exc:
            last = exc
            if attempt >= max_attempts:
                logger.warning("Firestore call failed after %s attempts: %s", max_attempts, exc)
                raise
            delay = base_delay_sec * (2 ** (attempt - 1))
            logger.warning(
                "Firestore transient error (attempt %s/%s): %s — retry in %.2fs",
                attempt,
                max_attempts,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last is not None
    raise last
