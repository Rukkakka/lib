import time

from base64 import b64encode
from collections.abc import (
    Callable,
    Mapping,
    MutableMapping
)
from functools import (
    cached_property,
    partial
)
from http import HTTPStatus
from http.client import (
    HTTPConnection,
    HTTPSConnection
)
from types import TracebackType
from urllib.parse import unquote

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from google.auth import transport
from google.auth.transport.requests import (
    AuthorizedSession,
    Request
)
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp  # type: ignore[import-untyped]
from googleapiclient.discovery import build
from googleapiclient.http import build_http
from gspread.client import Client
from gspread.exceptions import APIError
from gspread.http_client import (
    FileType,
    HTTPClient,
    HTTPClientType,
    ParamsType
)
from gspread import authorize
from httplib2 import (
    DEFAULT_MAX_REDIRECTS,
    Http,
    HTTPSConnectionWithTimeout,
    proxy_info_from_url,
    Response as HttpResponse
)
from requests import (
    PreparedRequest,
    Response,
    Session
)
from requests.adapters import HTTPAdapter

from typing import (
    Annotated,
    Any,
    cast,
    Self,
    TYPE_CHECKING
)

if TYPE_CHECKING:
    # pip install google-api-python-client-stubs
    from googleapiclient._apis.drive.v3.resources import DriveResource # type: ignore


class _TokenSyncCredentials(Credentials):
    """
    `Credentials` variant that reports every completed token refresh.

    Google transports (`AuthorizedSession` for gspread,
    `google_auth_httplib2.AuthorizedHttp` for the discovery client) own every
    refresh: they renew the credentials object in place when the token is due or
    after a `401`, so the owning model would otherwise keep serving the token it
    was constructed with. Overriding `refresh` is the only hook that observes
    those in-place renewals.

    The callback is set as an attribute after construction rather than taken
    by `__init__`, so the constructor stays exactly `Credentials`'s own.

    Attributes:
        on_refresh (Callable[[Credentials], None] | None): Called with the
            credentials after every completed refresh. Defaults to None.
    """

    on_refresh: Callable[[Credentials], None] | None = None

    def refresh(self, request: transport.Request) -> None:
        super().refresh(request)
        if self.on_refresh is not None:
            self.on_refresh(self)

    def _make_copy(self) -> '_TokenSyncCredentials':
        credentials: '_TokenSyncCredentials' = super()._make_copy()
        credentials.on_refresh = self.on_refresh
        return credentials


class GoogleCredentialsModel(BaseModel):
    """
    Base credential model for Google OAuth2 integrations.

    Stores OAuth2 token payload and builds a `Credentials` instance that can be
    reused by higher-level Google API client models.

    The credentials carry no token expiry, so they are renewed on demand by the
    Google transport that uses them - proactively once an expiry is known, and
    otherwise after the first `401`. Every such renewal is written back onto this
    model, so `token` (and `refresh_token`, when Google rotates it) keeps
    mirroring the live credentials instead of the values the model was
    constructed with. Persisting the refreshed state is still the caller's job:
    re-serialize the model once the work is done, for example
    `model_dump_json()` back into a secret store.

    Note that a caller driving `credentials` through something other than a
    Google transport gets neither behaviour and has to renew the token itself.

    Args:
        token (str): Current access token.
        refresh_token (str): Refresh token used to renew access token.
        token_uri (str): OAuth2 token endpoint URI.
        client_id (str): OAuth2 client id.
        client_secret (str): OAuth2 client secret.

    Attributes:
        credentials (Credentials): Google OAuth2 credentials object that syncs
            transport-side refreshes back into this model.

    Example:
        >>> model = GoogleCredentialsModel.model_validate_json(
        ...     Path('google_creds.json').read_text()
        ... )
        >>> ...  # long-running Drive or Sheets work
        >>> Path('google_creds.json').write_text(model.model_dump_json())
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    token: Annotated[
        str,
        Field(repr=False)
    ]

    refresh_token: Annotated[
        str,
        Field(repr=False)
    ]

    token_uri: str

    client_id: str

    client_secret: Annotated[
        str,
        Field(repr=False)
    ]

    def _sync_refreshed_token(self, credentials: Credentials) -> None:
        if credentials.token:
            self.token = credentials.token
        if credentials.refresh_token:
            self.refresh_token = credentials.refresh_token

    @cached_property
    def credentials(self) -> Credentials:
        # No eager refresh here: `Credentials.expired` is False whenever no
        # expiry is set, so the token always looks valid at this point and the
        # transports are the ones that renew it.
        credentials = _TokenSyncCredentials(
            token=self.token,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        credentials.on_refresh = self._sync_refreshed_token
        return credentials


class _TunnelHTTPSConnection(HTTPSConnectionWithTimeout):
    """
    httplib2 HTTPS connection that reaches its host through an HTTP proxy
    `CONNECT` tunnel described by the `proxy_info` httplib2 hands it.

    httplib2 leaves proxying to PySocks, which sends the proxy credentials as
    `Proxy-Authorization: basic ...`. RFC 7235 makes the scheme
    case-insensitive, but some proxies only accept `Basic` and answer `407`
    otherwise, and httplib2 drops `proxy_headers` on
    HTTPS, so the header cannot be corrected through it. The tunnel is opened
    with `http.client`'s own `set_tunnel` instead, which sends the header as
    written here and needs no PySocks.

    The tunnel is set up on the first `connect` rather than in `__init__`, so
    the constructor stays exactly httplib2's own. httplib2 reconnects the same
    object after a dropped connection, and the tunnel is kept across those
    reconnects.
    """

    _tunnel_ready: bool = False

    def _set_up_tunnel(self) -> None:
        headers: dict[str, str] = {}
        if self.proxy_info.proxy_user:
            # Percent-decoded as `requests` does, so both transports send the
            # same credentials for the same proxy URL.
            credentials = (
                f'{unquote(self.proxy_info.proxy_user)}:'
                f'{unquote(self.proxy_info.proxy_pass or "")}'
            )
            headers['Proxy-Authorization'] = (
                f'Basic {b64encode(credentials.encode()).decode()}'
            )
        self.set_tunnel(self.host, self.port, headers=headers)
        self.host = self.proxy_info.proxy_host
        self.port = self.proxy_info.proxy_port
        self._tunnel_ready = True

    def connect(self) -> None:
        if not self._tunnel_ready:
            self._set_up_tunnel()
        # Skip httplib2's `connect`, which would hand the proxy to PySocks.
        HTTPSConnection.connect(self)


class _ProxyHttp(Http):
    """
    `Http` that sends every HTTPS request through `_TunnelHTTPSConnection`.

    Google APIs are served over HTTPS only. A plain HTTP request is left to
    httplib2, which fails loudly without PySocks rather than bypassing the
    proxy.
    """

    def request(
        self,
        uri: str,
        method: str = 'GET',
        body: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        redirections: int = DEFAULT_MAX_REDIRECTS,
        connection_type: type[HTTPConnection] | None = None
    ) -> tuple[HttpResponse, bytes]:
        if connection_type is None and uri.startswith('https:'):
            connection_type = _TunnelHTTPSConnection
        return super().request(
            uri, method, body, headers, redirections, connection_type
        )


def _build_proxied_http(proxy: str) -> Http:
    # Seeded from `build_http()` so it keeps the timeout and the `308` handling
    # the discovery client relies on for resumable uploads.
    template = build_http()
    http = _ProxyHttp(
        timeout=template.timeout,
        # An empty `noproxy` keeps `NO_PROXY` from exempting hosts from a proxy
        # the caller asked for explicitly.
        proxy_info=proxy_info_from_url(proxy, noproxy='')
    )
    http.redirect_codes = template.redirect_codes
    return http


class GoogleModel(GoogleCredentialsModel):
    """
    Generic Google API discovery client model.

    Extends `GoogleCredentialsModel` and builds a dynamic client through
    `googleapiclient.discovery.build`.

    Args:
        token (str): Current access token.
        refresh_token (str): Refresh token used to renew access token.
        token_uri (str): OAuth2 token endpoint URI.
        client_id (str): OAuth2 client id.
        client_secret (str): OAuth2 client secret.
        service_name (str): Google API service name (for example, `drive`).
        version (str): API version (for example, `v3`).
        proxy (str | None): HTTP proxy URL for every request the client
            makes, including the discovery document fetch and token refreshes.
            It takes precedence over the proxy environment variables, as it
            does on the `httpx` based clients. Defaults to None.
        static_discovery (bool): Build from the discovery document bundled
            with `googleapiclient` instead of fetching it. Defaults to False.

    Attributes:
        credentials (Credentials): Google OAuth2 credentials, see
            `GoogleCredentialsModel`.
        client (Any): Google API discovery client instance.

    Example:
        >>> api = GoogleModel(
        ...     token='...',
        ...     refresh_token='...',
        ...     token_uri='https://oauth2.googleapis.com/token',
        ...     client_id='...',
        ...     client_secret='...',
        ...     service_name='drive',
        ...     version='v3',
        ... )
        >>> files_api = api.client.files()
        >>> api.close()
    """

    service_name: str

    version: str

    proxy: str | None = None

    static_discovery: bool = False

    @cached_property
    def client(self) -> Any:
        # Same transport `build(credentials=...)` would assemble, spelled out
        # so the proxy can be set on it. Token refreshes go over this `http`
        # too, so they are proxied as well.
        http = build_http() if self.proxy is None else _build_proxied_http(self.proxy)
        return build(
            serviceName=self.service_name,
            version=self.version,
            http=AuthorizedHttp(self.credentials, http=http),
            static_discovery=self.static_discovery,
        )

    def close(self) -> None:
        client: Any | None = self.__dict__.pop('client', None)
        if client is not None:
            client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        self.close()


class GdriveModel(GoogleModel):
    """
    Google Drive client model with default service metadata.

    Defaults to Drive v3; cleanup and context-manager support come from
    `GoogleModel`.

    Args:
        token (str): Current access token.
        refresh_token (str): Refresh token used to renew access token.
        token_uri (str): OAuth2 token endpoint URI.
        client_id (str): OAuth2 client id.
        client_secret (str): OAuth2 client secret.
        proxy (str | None): HTTP proxy URL, see `GoogleModel`. Defaults to
            None.

    Attributes:
        service_name (str): Google API service name (`drive`).
        version (str): Google Drive API version (`v3`).
        client (DriveResource): Google Drive API client.

    Example:
        >>> with GdriveModel(
        ...     token='...',
        ...     refresh_token='...',
        ...     token_uri='https://oauth2.googleapis.com/token',
        ...     client_id='...',
        ...     client_secret='...',
        ... ) as api:
        ...     about = api.client.about().get(fields='user').execute()
    """

    service_name: str = 'drive'

    version: str = 'v3'

    @cached_property
    def client(self) -> 'DriveResource':
        return super().client


class _BoundedBackOffHTTPClient(HTTPClient):
    """
    `HTTPClient` that retries rate-limited requests a bounded number of times.

    gspread ships `BackOffHTTPClient` for this, but its stop condition compares
    an already-capped wait against the very cap that produced it
    (`min(2 ** n, 128) <= 128`), so it never stops: a request that keeps failing
    sleeps 128 seconds between attempts until the recursion limit ends it hours
    later. Retrying here is iterative and gives up once `max_retries` is spent,
    so a caller sees the `APIError` while its job still has time to react.

    Waits double from `_INITIAL_BACKOFF_SECONDS` up to `_MAX_BACKOFF_SECONDS`
    (10s, 20s, 40s, then 60s), so the default budget outlasts the one-minute
    window Google measures its quotas over.

    Only a read (`GET`/`HEAD`) is retried on a timeout or server error. A write
    that fails that way may already have been applied, so resending it could
    apply it twice (an `append_row` adding the same row again); a write is
    retried only on a rate limit, which Google answers before doing any work.

    Args:
        auth (Credentials): Credentials to authorize requests with, as taken by
            `HTTPClient`.
        session (Session | None): Session to use instead of building an
            authorized one. Defaults to `None`.
        max_retries (int): How many times a retryable request is retried after
            its first attempt. Defaults to `0`; `0` disables retrying.
    """

    _INITIAL_BACKOFF_SECONDS: int = 10
    _MAX_BACKOFF_SECONDS: int = 60

    _RETRY_STATUS_CODES: frozenset[int] = frozenset({
        HTTPStatus.REQUEST_TIMEOUT,
        HTTPStatus.TOO_MANY_REQUESTS
    })

    _IDEMPOTENT_METHODS: frozenset[str] = frozenset({
        'GET',
        'HEAD'
    })

    def __init__(
        self,
        auth: Credentials,
        session: Session | None = None,
        max_retries: int = 0
    ) -> None:
        super().__init__(auth, session)
        self.max_retries = max_retries

    @classmethod
    def _is_retryable(cls, method: str, error: APIError) -> bool:
        errors = error.error.get('errors')
        if errors and error.code == HTTPStatus.FORBIDDEN:
            # Drive reports a quota hit as a 403 that only its `usageLimits`
            # domain separates from a genuine permission error.
            return errors[0].get('domain') == 'usageLimits'
        if error.code == HTTPStatus.TOO_MANY_REQUESTS:
            return True
        if method.upper() not in cls._IDEMPOTENT_METHODS:
            return False
        return (
            error.code in cls._RETRY_STATUS_CODES
            or error.code >= HTTPStatus.INTERNAL_SERVER_ERROR
        )

    def _backoff_seconds(self, retry: int) -> int:
        return min(
            self._INITIAL_BACKOFF_SECONDS * 2 ** retry,
            self._MAX_BACKOFF_SECONDS
        )

    def request(
        self,
        method: str,
        endpoint: str,
        params: ParamsType | None = None,
        data: bytes | None = None,
        json: Mapping[str, Any] | None = None,
        files: FileType = None,
        headers: MutableMapping[str, str] | None = None
    ) -> Response:
        send = partial(
            super().request,
            method,
            endpoint,
            params=params,
            data=data,
            json=json,
            files=files,
            headers=headers
        )
        for retry in range(self.max_retries):
            try:
                return send()
            except APIError as error:
                if not self._is_retryable(method, error):
                    raise
                time.sleep(self._backoff_seconds(retry))
        return send()


class _ProxyAdapter(HTTPAdapter):
    """
    `HTTPAdapter` that sends every request through one fixed proxy.

    `Session.proxies` alone is not enough: `requests` lets the proxy
    environment variables override it, so a proxy passed in explicitly would be
    silently replaced on a host that sets `HTTPS_PROXY`. Pinning it here at the
    transport keeps the precedence of the `httpx` based clients, where an
    explicit `proxy` wins over the environment.

    Args:
        proxy (str): Proxy URL used for both `http` and `https` requests.
        max_retries (int): Connection retry budget, passed through to
            `HTTPAdapter`. Defaults to `0`.
    """

    def __init__(self, proxy: str, max_retries: int = 0) -> None:
        super().__init__(max_retries=max_retries)
        self._proxies = {'http': proxy, 'https': proxy}

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float | None, float | None] | None = None,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        proxies: dict[str, str] | None = None
    ) -> Response:
        # `proxies` arrives already merged with the environment; it is
        # replaced rather than consulted.
        return super().send(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=self._proxies
        )


class GspreadModel(GoogleCredentialsModel):
    """
    Google Sheets client model backed by `gspread`.

    Uses OAuth2 credentials from `GoogleCredentialsModel` and returns an
    authorized gspread client for spreadsheet operations.

    The client backs off and retries the rate limits and transient server errors
    the Sheets and Drive APIs raise, then surfaces the `APIError` once
    `max_retries` is spent instead of retrying forever, see
    `_BoundedBackOffHTTPClient`.

    Args:
        token (str): Current access token.
        refresh_token (str): Refresh token used to renew access token.
        token_uri (str): OAuth2 token endpoint URI.
        client_id (str): OAuth2 client id.
        client_secret (str): OAuth2 client secret.
        max_retries (int): How many times a rate-limited or transiently failing
            request is retried after its first attempt. Defaults to `0`; `0`
            disables retrying.
        proxy (str | None): HTTP proxy URL for every request the client
            makes, including token refreshes. It takes precedence over the
            proxy environment variables, as it does on the `httpx` based
            clients. Defaults to None.

    Attributes:
        credentials (Credentials): Google OAuth2 credentials, see
            `GoogleCredentialsModel`.
        client (Client): Authorized gspread client.

    Example:
        >>> with GspreadModel(
        ...     token='...',
        ...     refresh_token='...',
        ...     token_uri='https://oauth2.googleapis.com/token',
        ...     client_id='...',
        ...     client_secret='...',
        ...     max_retries=5,
        ... ) as api:
        ...     sheet = api.client.open('my_sheet')
    """

    max_retries: Annotated[
        int,
        Field(ge=0)
    ] = 0

    proxy: str | None = None

    def _build_proxied_session(self, proxy: str) -> AuthorizedSession:
        # `AuthorizedSession` refreshes the token over a session of its own
        # rather than itself, so that one needs the proxy too or every refresh
        # goes out directly. Its retry budget mirrors the session
        # `AuthorizedSession` would otherwise build for it.
        refresh_session = Session()
        refresh_session.mount('https://', _ProxyAdapter(proxy, max_retries=3))
        refresh_session.mount('http://', _ProxyAdapter(proxy))

        session = AuthorizedSession(
            self.credentials,
            auth_request=Request(refresh_session)
        )
        session.mount('https://', _ProxyAdapter(proxy))
        session.mount('http://', _ProxyAdapter(proxy))
        return session

    @cached_property
    def client(self) -> Client:
        session = None
        if self.proxy is not None:
            session = self._build_proxied_session(self.proxy)
        return authorize(
            credentials=self.credentials,
            session=session,
            # `authorize` only ever calls this as `http_client(auth, session)`,
            # so binding the budget up front is enough to configure it.
            http_client=cast(
                HTTPClientType,
                partial(_BoundedBackOffHTTPClient, max_retries=self.max_retries)
            )
        )

    def close(self) -> None:
        client: Client | None = self.__dict__.pop('client', None)
        if client is None:
            return
        session = client.http_client.session
        # `AuthorizedSession.close` closes a refresh session only when it built
        # that session itself, so the proxied one handed in is closed here.
        auth_request = getattr(session, '_auth_request', None)
        refresh_session = getattr(auth_request, 'session', None)
        session.close()
        if refresh_session is not None:
            refresh_session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        self.close()
