from functools import cached_property
from http.client import HTTPMessage
from io import BytesIO
from logging import (
    Logger,
    DEBUG
)
from ssl import SSLContext
from urllib.error import (
    HTTPError,
    URLError
)
from urllib.request import Request

from httpx import (
    Client,
    ConnectError,
    ConnectTimeout,
    ReadError,
    RemoteProtocolError
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from slack_sdk import WebClient
from slack_sdk.errors import SlackRequestError
from slack_sdk.http_retry import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler,
)
from slack_sdk.web.file_upload_v2_result import FileUploadV2Result

from typing import (
    Annotated,
    Any,
)


class HttpxWebClient(WebClient):
    """
    `slack_sdk.WebClient` subclass that swaps the urllib transport for httpx.

    slack_sdk does not expose a public hook to inject a custom transport, so we
    override two private methods (`_perform_urllib_http_request_internal` and
    `_upload_file`) to route requests through httpx. This is fragile by design:
    if slack_sdk renames or changes the signature of either method on upgrade,
    our override stops being called (silent regression) or fails with a
    TypeError (loud regression). Nothing guards against that drift yet, so
    check both overrides against the new slack_sdk source before bumping it.

    slack_sdk's retry handlers are written against urllib's failure modes, so
    the request override reproduces them: a `4xx`/`5xx` is raised as
    `HTTPError`, the branch where slack_sdk wraps each header value in a list
    as `RateLimitErrorRetryHandler` reads it, and a failure to reach or stay
    connected to the server is raised as `URLError`, which
    `ConnectionErrorRetryHandler` retries. A read timeout is left as is and not
    retried, since Slack may already have acted on the request.
    """

    def _perform_urllib_http_request_internal(
        self,
        url: str,
        req: Request,
    ) -> dict[str, Any]:
        if not url.lower().startswith('http'):
            raise SlackRequestError(f'Invalid URL detected: {url}')

        headers = dict(req.headers)
        body = req.data
        if body is not None and not isinstance(body, bytes):
            raise SlackRequestError(
                f'Unsupported request body type: {type(body).__name__}'
            )

        if self._logger.level <= DEBUG:
            self._logger.debug(
                f'Sending request via HTTPX: {req.get_method()} {url}'
            )

        with Client(
            proxy=self.proxy,
            timeout=self.timeout,
            verify=self.ssl if self.ssl else True,
        ) as client:
            try:
                response = client.request(
                    method=req.get_method(),
                    url=url,
                    headers=headers,
                    content=body,
                )
            except (
                ConnectError,
                ConnectTimeout,
                ReadError,
                RemoteProtocolError,
            ) as exc:
                raise URLError(exc) from exc

        if response.status_code >= 400:
            error_headers = HTTPMessage()
            for key, value in response.headers.multi_items():
                error_headers[key] = value
            raise HTTPError(
                url,
                response.status_code,
                response.reason_phrase,
                error_headers,
                BytesIO(response.content),
            )

        response_headers = dict(response.headers)

        if response.headers.get('content-type') == 'application/gzip':
            body_content: bytes = response.content
            if self._logger.level <= DEBUG:
                self._logger.debug(
                    f'Received response - status: {response.status_code}, '
                    f'headers: {response_headers}, body: (binary)'
                )
            return {
                'status': response.status_code,
                'headers': response_headers,
                'body': body_content,
            }

        decoded_body: str = response.text
        if self._logger.level <= DEBUG:
            self._logger.debug(
                f'Received response - status: {response.status_code}, '
                f'headers: {response_headers}, body: {decoded_body}'
            )
        return {
            'status': response.status_code,
            'headers': response_headers,
            'body': decoded_body,
        }

    def _upload_file(
        self,
        *,
        url: str,
        data: bytes,
        logger: Logger,
        timeout: int,
        proxy: str | None,
        ssl: SSLContext | None,
    ) -> FileUploadV2Result:
        """Use HTTPX for files_upload_v2 step2 upload endpoint."""

        with Client(
            proxy=proxy if proxy else self.proxy,
            timeout=timeout,
            verify=ssl if ssl else (self.ssl if self.ssl else True),
        ) as client:
            response = client.request(
                method='POST',
                url=url,
                content=data,
                timeout=timeout,
            )

        try:
            body = response.text
        except Exception:
            body = response.content.decode('utf-8', errors='replace')

        return FileUploadV2Result(
            status=response.status_code,
            body=body,
        )


class SlackModel(BaseModel):
    """
    Client model for creating a synchronous Slack client with validated settings.

    This model provides a synchronous Slack client backed by HTTPX.
    For each request, a short-lived HTTPX client is created and closed
    immediately, so there is no persistent transport or manual close to manage.

    Args:
        token (str): Slack bot token (xoxb-*).
        timeout (int): Request timeout in seconds. Defaults to 120.
        proxy (str | None): Proxy URL for routing requests. Defaults to None.

    Attributes:
        client (HttpxWebClient): Cached synchronous Slack client.

    Example:
        >>> api = SlackModel(token='xoxb-...', proxy=proxy.url)
        >>> response = api.client.chat_postMessage(channel='C123', text='Hello')
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    token: Annotated[
        str,
        Field(repr=False),
    ]

    timeout: Annotated[
        int,
        Field(gt=0),
    ] = 120

    proxy: str | None = None

    @cached_property
    def client(self) -> HttpxWebClient:
        return HttpxWebClient(
            token=self.token,
            timeout=self.timeout,
            proxy=self.proxy,
            retry_handlers=[
                ConnectionErrorRetryHandler(max_retry_count=3),
                RateLimitErrorRetryHandler(max_retry_count=3),
            ],
        )
