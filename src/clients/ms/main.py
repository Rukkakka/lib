from functools import cached_property

from abc import (
    ABC,
    abstractmethod
)

from httpx import AsyncClient

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from azure.identity import (
    ClientSecretCredential,
    UsernamePasswordCredential
)

from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider

from msgraph import(
    GraphRequestAdapter,
    GraphServiceClient
)

from clients.ms.utility import _RefreshTokenCredential

from typing import (
    Annotated,
    Dict,
    List,
    Optional
)


class MSBaseClientModel(BaseModel, ABC):
    """Abstract base for Microsoft Graph clients.

    Holds the settings every authentication flow shares and builds the
    `GraphServiceClient` from whatever credential the subclass supplies.

    Args:
        tenant_id: Directory (tenant) id.
        client_id: Application (client) id.
        verify: Whether to verify TLS certificates. Defaults to True.
        proxy: Proxy URL applied to both the Graph client and the token
            requests, e.g. `http://proxy:8080`. Defaults to no proxy.
        scopes: Scopes requested from the auth provider. Defaults to Microsoft
            Graph `.default`.

    Attributes:
        credential: Flow-specific credential, supplied by the subclass.
        client: Cached `GraphServiceClient`, created on first access.
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    tenant_id: Annotated[
        str,
        Field()
    ]

    client_id: Annotated[
        str,
        Field()
    ]

    verify: Annotated[
        bool,
        Field()
    ] = True

    proxy: Annotated[
        Optional[str],
        Field()
    ] = None

    scopes: Annotated[
        List[str],
        Field()
    ] = ['https://graph.microsoft.com/.default']

    @property
    @abstractmethod
    def credential(self):
        ...

    @property
    def _proxies(self) -> Optional[Dict[str, str]]:
        """`proxy` in the requests-style mapping the azure pipeline expects."""
        if self.proxy is None:
            return None
        return {
            'http': self.proxy,
            'https': self.proxy,
        }

    @cached_property
    def client(self) -> GraphServiceClient:
        auth_provider = AzureIdentityAuthenticationProvider(
            self.credential,
            scopes=self.scopes
        )
        http_client = AsyncClient(verify=self.verify, proxy=self.proxy)
        request_adapter = GraphRequestAdapter(
            auth_provider,
            client=http_client
        )
        return GraphServiceClient(request_adapter=request_adapter)
    

class MSAppClientModel(MSBaseClientModel):
    """Graph client authenticating as the application itself.

    Uses the client credentials flow, so the token carries the app's own
    application permissions rather than a user's.

    Args:
        tenant_id: Directory (tenant) id.
        client_id: Application (client) id.
        client_secret: Client secret for the application.
        verify: Whether to verify TLS certificates. Defaults to True.
        proxy: Proxy URL. Defaults to no proxy.
        scopes: Scopes requested. Defaults to Microsoft Graph `.default`.

    Attributes:
        credential: Cached `ClientSecretCredential`, created on first access.
        client: Cached `GraphServiceClient`, created on first access.

    Example:
        >>> model = MSAppClientModel(
        ...     tenant_id='...', client_id='...', client_secret='...'
        ... )
        >>> users = await model.client.users.get()
    """

    client_secret: Annotated[
        str,
        Field(repr=False)
    ]

    @cached_property
    def credential(self) -> ClientSecretCredential:
        return ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
            connection_verify=self.verify,
            proxies=self._proxies
        )
    

class MSDelegateClientModel(MSBaseClientModel):
    """Graph client acting on behalf of a user, via username and password.

    Uses the resource owner password credentials flow, which Microsoft has
    deprecated because it cannot satisfy multifactor authentication. Prefer
    `MSDelegateRefreshTokenClientModel` for new code.

    Args:
        tenant_id: Directory (tenant) id.
        client_id: Application (client) id.
        client_secret: Client secret for the application.
        username: User principal name, e.g. `user@contoso.com`.
        password: The user's password.
        verify: Whether to verify TLS certificates. Defaults to True.
        proxy: Proxy URL. Defaults to no proxy.
        scopes: Scopes requested. Defaults to Microsoft Graph `.default`.

    Attributes:
        credential: Cached `UsernamePasswordCredential`, created on first access.
        client: Cached `GraphServiceClient`, created on first access.

    Example:
        >>> model = MSDelegateClientModel(
        ...     tenant_id='...', client_id='...', client_secret='...',
        ...     username='user@contoso.com', password='...'
        ... )
        >>> me = await model.client.me.get()
    """

    client_secret: Annotated[
        str,
        Field(repr=False)
    ]

    username: Annotated[
        str,
        Field(pattern=r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+$')
    ]

    password: Annotated[
        str,
        Field(repr=False)
    ]

    @cached_property
    def credential(self) -> UsernamePasswordCredential:
        return UsernamePasswordCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_credential=self.client_secret,
            username=self.username,
            password=self.password,
            connection_verify=self.verify,
            proxies=self._proxies
        )
    

class MSDelegateRefreshTokenClientModel(MSBaseClientModel):
    """Graph client acting on behalf of a user, via a refresh token.

    Suits public clients with no secret, and unlike `MSDelegateClientModel` it
    works with multifactor authentication. Obtain the initial token with
    `create_refresh_token`.

    Azure AD may issue a new refresh token on every exchange. The credential
    reports each one back, so `refresh_token` always holds the newest value —
    read it after use and persist it, or the stored token goes stale.

    Args:
        tenant_id: Directory (tenant) id.
        client_id: Application (client) id.
        refresh_token: Refresh token from a prior sign-in.
        verify: Whether to verify TLS certificates. Defaults to True.
        proxy: Proxy URL. Defaults to no proxy.
        scopes: Scopes requested. Defaults to Microsoft Graph `.default`.

    Attributes:
        credential: Cached credential, created on first access.
        client: Cached `GraphServiceClient`, created on first access.

    Example:
        >>> model = MSDelegateRefreshTokenClientModel(
        ...     tenant_id='...', client_id='...', refresh_token='...'
        ... )
        >>> me = await model.client.me.get()
        >>> save(model.refresh_token)  # may differ from the token passed in
    """

    refresh_token: Annotated[
        str,
        Field(repr=False)
    ]

    def _sync_refresh_token(self, refresh_token: str) -> None:
        self.refresh_token = refresh_token

    @cached_property
    def credential(self) -> _RefreshTokenCredential:
        return _RefreshTokenCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            refresh_token=self.refresh_token,
            verify=self.verify,
            proxy=self.proxy,
            on_refresh=self._sync_refresh_token
        )