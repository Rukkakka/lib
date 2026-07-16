from functools import cached_property

from logging import (
    Logger,
    DEBUG
)

from urllib.request import Request

from ssl import SSLContext

from httpx import Client

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from slack_sdk import WebClient
from slack_sdk.errors import SlackRequestError
from slack_sdk.http_retry import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler
)
from slack_sdk.web.file_upload_v2_result import FileUploadV2Result

from typing import (
    Annotated,
    Any,
    Dict,
    Optional
)


class HttpxWebClient(WebClient):
    """A `slack_sdk` `WebClient` that sends its requests through `httpx`.

    Overrides the two `WebClient` hooks that reach for urllib — the internal
    HTTP request and the v2 file upload — so all traffic goes through `httpx`
    and honours its proxy and TLS settings. The public `WebClient` API is
    otherwise unchanged.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _perform_urllib_http_request_internal(
            self, 
            url: str, 
            req: Request
    ) -> Dict[str, Any]:
        if not url.lower().startswith('http'):
            raise SlackRequestError(f'Invalid URL detected: {url}')
        
        headers = dict(req.headers)
        body = req.data
        

        if self._logger.level <= DEBUG:
            self._logger.debug(
                f'Sending request via HTTPX: {req.get_method()} {url}'
            )

        with Client(
            proxy=self.proxy,
            timeout=self.timeout,
            verify=self.ssl if self.ssl else True,
        ) as client:
            response = client.request(
                method=req.get_method(),
                url=url,
                headers=headers,
                content=body
            )

        response_headers = dict(response.headers)

        if response.headers.get('content-type') == 'application/gzip':
            body_content: bytes = response.content
            if self._logger.level <= DEBUG:
                self._logger.debug(
                    f'Received response - status: {response.status_code}, '
                    f'headers: {response_headers}, body: (binary)'
                )
            return {'status': response.status_code, 'headers': response_headers, 'body': body_content}
        
        decoded_body: str = response.text
        if self._logger.level <= DEBUG:
            self._logger.debug(
                    f'Received response - status: {response.status_code}, '
                    f'headers: {response_headers}, body: {decoded_body}'
                )
        return {'status': response.status_code, 'headers': response_headers, 'body': decoded_body}
        
    def _upload_file(
            self, 
            *, 
            url: str, 
            data: bytes, 
            logger: Logger, 
            timeout: int, 
            proxy: Optional[str],
            ssl: Optional[SSLContext],
    ) -> FileUploadV2Result:
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
    """Pydantic model wrapping a Slack Web API client backed by httpx.

    Lazily creates and caches an `HttpxWebClient` on first access via `client`,
    a `WebClient` subclass that performs HTTP requests through httpx instead of
    urllib, with connection- and rate-limit retry handlers pre-configured.

    Args:
        token: Slack API token used to authenticate requests.
        timeout: Request timeout in seconds. Defaults to 120.
        proxy: Optional proxy URL for outbound requests. Defaults to None.

    Attributes:
        client: Cached `HttpxWebClient`, created on first access.

    Example:
        >>> model = SlackModel(token='xoxb-...')
        >>> model.client.chat_postMessage(channel='#general', text='hello')
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    token: Annotated[
        str,
        Field(repr=False)
    ]

    timeout: Annotated[
        int,
        Field()
    ] = 120


    proxy: Annotated[
        Optional[str],
        Field()
    ] = None

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