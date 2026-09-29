import json
import logging
import re
from datetime import (
    datetime,
    timezone,
)
from email.utils import parsedate_to_datetime
from math import isfinite
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from httpx import (
    HTTPStatusError,
    Response,
    TimeoutException,
    TransportError,
)

from tenacity import RetryCallState

from typing import Literal


logger = logging.getLogger(__name__)

BODY_PREVIEW_LIMIT = 2048
RETRY_BODY_PREVIEW_LIMIT = 200
SENSITIVE_KEY_PATTERN = re.compile(
    r'(token|secret|password|passwd|api[-_]?key|access[-_]?key|'
    r'private[-_]?key|service[-_]?key|authorization|cookie|credential)',
    re.IGNORECASE,
)
SENSITIVE_TEXT_PATTERN = re.compile(
    r'([\w-]*(?:token|secret|password|passwd|api[-_]?key|access[-_]?key|'
    r'private[-_]?key|service[-_]?key|authorization|cookie|credential)'
    r'[\w-]*\s*[=:]\s*)'
    r'([^,\s&}\n]+)',
    re.IGNORECASE,
)


def _redact_json(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: '<redacted>'
            if SENSITIVE_KEY_PATTERN.search(str(key))
            else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(value: str) -> str:
    return SENSITIVE_TEXT_PATTERN.sub(r'\1<redacted>', value)


def _safe_request_url(url: object) -> str:
    parts = urlsplit(str(url))
    netloc = parts.netloc.rsplit('@', 1)[-1]
    return urlunsplit((parts.scheme, netloc, parts.path, '', ''))


def create_base_url(schema: Literal['https', 'http'], host: str) -> str:
    return f'{schema}://{host}'


def bearer_authorization(token: str) -> str:
    """Render `token` as an `Authorization` header value.

    Accepts either the bare token or one already carrying the `Bearer ` prefix,
    so a caller copying the header value verbatim does not end up sending
    `Bearer Bearer ...`.
    """
    token = token.strip()
    if token.startswith('Bearer '):
        return token
    return f'Bearer {token}'


class ResponseStatusError(HTTPStatusError):
    """`HTTPStatusError` whose message carries a truncated response body."""


def _request_origin(exc: HTTPStatusError) -> str:
    """Name the request behind a status error without assuming one was attached.

    `HTTPStatusError.request` raises rather than returning None when the error
    was built without one, which a hand-constructed error in a retry predicate
    can be, so the attribute is never read unguarded.
    """
    try:
        request = exc.request
    except RuntimeError:
        return '<unknown request>'
    return f'{request.method} {_safe_request_url(request.url)}'


def _body_preview(response: Response, limit: int = BODY_PREVIEW_LIMIT) -> str:
    """Render a response body short enough to sit inside an exception message.

    A body that was never read raises rather than returning text, and an error
    that hides why it was raised is worse than a coarse placeholder, so every
    failure here resolves to a marker instead of propagating.
    """
    try:
        body = response.text
    except Exception:
        return '<unread>'

    body = body.strip()
    if not body:
        return '<empty>'

    try:
        body = json.dumps(
            _redact_json(json.loads(body)),
            ensure_ascii=False,
        )
    except (json.JSONDecodeError, TypeError):
        body = _redact_text(body)

    if len(body) > limit:
        return f'{body[:limit]}... (truncated, {len(body)} chars)'
    return body


def raise_for_status(response: Response, limit: int = BODY_PREVIEW_LIMIT) -> None:
    """`Response.raise_for_status` that keeps the error body in the message.

    httpx states only the status and the URL, so an upstream rejection arrives
    with the `code`/`description` pair that explains it stripped out, and the
    caller has to reproduce the request to learn what was wrong with it. The
    body is truncated at `limit`, and headers are deliberately left out because
    that is where the credentials sit.

    Raises:
        ResponseStatusError: If the response carries a `4xx` or `5xx` status.
            It subclasses `HTTPStatusError`, so callers and the retry
            predicates that match on that type are unaffected.
    """
    try:
        response.raise_for_status()
    except HTTPStatusError as exc:
        raise ResponseStatusError(
            f'{_request_origin(exc)} -> '
            f'{response.status_code} {response.reason_phrase}\n'
            f'Response body: {_body_preview(response, limit)}',
            request=exc.request,
            response=exc.response,
        ) from None


def describe_failed_attempt(
    exc: BaseException | None,
    limit: int = RETRY_BODY_PREVIEW_LIMIT,
) -> str:
    """Render a failed attempt as one line for the retry log.

    The body is previewed far shorter here than in the raised error and its
    whitespace is collapsed. A retry line answers "why are we going round
    again", and it is written once per attempt, so a full body would repeat
    the same kilobytes across every attempt of every retrying call.

    `exc` is optional because tenacity types the failed outcome as optional, and
    a retry line must not raise on the way to reporting a failure.
    """
    if exc is None:
        return '<no exception recorded>'
    if not isinstance(exc, HTTPStatusError):
        return f'{type(exc).__name__}: {exc}'

    body = ' '.join(_body_preview(exc.response, limit).split())
    return (
        f'{_request_origin(exc)} -> '
        f'{exc.response.status_code} {exc.response.reason_phrase} '
        f'| body: {body}'
    )


def should_retry_idempotent(exc: BaseException) -> bool:
    if isinstance(exc, HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429
    return isinstance(exc, (TimeoutException, TransportError))


def should_retry_non_idempotent(exc: BaseException) -> bool:
    if isinstance(exc, HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429
    return False


def retry_after_seconds(header: str) -> float | None:
    """
    Reads a `Retry-After` value in either form RFC 9110 allows.

    Factored out of `wait_retry_after` so callers with their own rate-limit
    headers to fall back on (for a platform that answers 429 with
    `RateLimit-Reset` alone) can reuse the same RFC 9110 parsing instead of
    duplicating it.

    Args:
        header (str): Raw header value, as delay-seconds or an HTTP-date.

    Returns:
        float | None: Seconds to wait, or None when the value parses as
            neither form.
    """
    try:
        seconds = float(header)
    except ValueError:
        pass
    else:
        return seconds if isfinite(seconds) else None

    try:
        deadline = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    if deadline is None:
        return None
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return (deadline - datetime.now(timezone.utc)).total_seconds()


def wait_retry_after(
    retry_state: RetryCallState,
    default: float = 1.0,
    maximum: float = 60.0,
) -> float:
    """Honour a rate-limit `Retry-After` header, capped at `maximum` seconds.

    APIs that publish a retry delay (Zendesk returns 60s or more on 429) make a
    fixed one-second wait useless: every attempt is spent before the window
    reopens. The cap keeps a hostile header from blocking the caller for hours.

    RFC 9110 allows either delay-seconds or an HTTP-date, and both are read
    here. A date whose deadline has already passed waits zero seconds rather
    than the default, since its window is open; an unparseable header falls
    back to `default` so the retry machinery never raises.
    """
    outcome = retry_state.outcome
    if outcome is None:
        return default

    exc = outcome.exception()
    if not isinstance(exc, HTTPStatusError):
        return default

    header = exc.response.headers.get('Retry-After')
    if not header:
        return default

    seconds = retry_after_seconds(header)
    if seconds is None:
        return default

    return min(max(seconds, 0.0), maximum)


def log_retry_before_sleep(retry_state: RetryCallState) -> None:
    outcome = retry_state.outcome
    next_action = retry_state.next_action
    if outcome is None or next_action is None:
        return

    logger.warning(
        'Attempt %s failed: %s | Retrying in %ss...',
        retry_state.attempt_number,
        describe_failed_attempt(outcome.exception()),
        next_action.sleep,
    )
