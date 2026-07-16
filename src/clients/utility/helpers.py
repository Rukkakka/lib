import logging

from httpx import (
    HTTPStatusError,
    TimeoutException,
    TransportError
)

from tenacity import RetryCallState

from typing import Literal


logger = logging.getLogger(__name__)


def create_base_url(schema: Literal['http', 'https'], host: str) -> str:
    return f'{schema}://{host}'

def should_retry_idempotent(exc: Exception) -> bool:
    if isinstance(exc, HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429
    return isinstance(exc, (TimeoutException, TransportError))

def should_retry_non_idempotent(exc: Exception) -> bool:
    if isinstance(exc, HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429
    return False

def log_retry_before_sleep(retry_state: RetryCallState) -> None:
    logger.warning(
        'Attempt %s failed. Error: %s | Retrying in %ss...',
        retry_state.attempt_number,
        retry_state.outcome.exception(),
        retry_state.next_action.sleep,
    )

