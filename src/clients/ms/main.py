from functools import cached_property
from inspect import isawaitable
from types import TracebackType
from abc import (
    ABC,
    abstractmethod
)

from httpx import AsyncClient
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from azure.identity import (
    ClientSecretCredential,
    UsernamePasswordCredential,
)
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider
from msgraph import (
    GraphRequestAdapter,
    GraphServiceClient,
)

from clients.ms.utility import _RefreshTokenCredential

from typing import (
    Annotated,
    Self,
)


class MSBaseClientModel(BaseModel, ABC):
    """
    Shared base for Microsoft Graph SDK client models.

    Holds common Azure AD fields used by both application and delegated
    credential subclasses. Each subclass provides its own ``credential``
    and ``client`` via `cached_property`.

    All Graph SDK calls are asynchronous -- use ``await`` when calling
    methods on ``client``.

    Args:
        tenant_id (str): Azure AD tenant id.
        client_id (str): Azure AD application (client) id.
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): HTTP proxy URL applied to both Graph API
            requests and token acquisition (Azure AD authentication).
            Defaults to None.
        timeout (int): Graph API request timeout in seconds. Defaults to 120.
        scopes (list[str]): OAuth scopes requested for the token.
            Defaults to ['https://graph.microsoft.com/.default'].

    See:
        https://github.com/microsoftgraph/msgraph-sdk-python
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    tenant_id: str

    client_id: str

    verify: bool = True

    proxy: str | None = None

    timeout: int = 120

    scopes: list[str] = ['https://graph.microsoft.com/.default']

    @property
    @abstractmethod
    def credential(self):
        """
        Azure credential used by the Graph SDK auth provider. Subclasses
        must override this with ``@cached_property`` so the credential
        (and any token cache it owns) survives across Graph calls within
        a single client instance.

        ``@property`` + ``@abstractmethod`` is used here purely to mark
        the attribute abstract. ``@cached_property`` cannot be combined
        with ``@abstractmethod`` -- the abstract marker fails to
        propagate, so ABC stops blocking incomplete subclasses from
        instantiating. Keep the abstract declaration as a plain property
        and let the concrete subclass apply the caching decorator.
        """
        ...

    @property
    def _proxies(self) -> dict[str, str] | None:
        """`proxy` in the requests-style mapping the azure pipeline expects."""
        if self.proxy is None:
            return None
        return {
            'http': self.proxy,
            'https': self.proxy,
        }

    @cached_property
    def _http_client(self) -> AsyncClient:
        return AsyncClient(
            verify=self.verify,
            proxy=self.proxy,
            timeout=self.timeout,
        )

    @cached_property
    def client(self) -> GraphServiceClient:
        auth_provider = AzureIdentityAuthenticationProvider(
            self.credential,
            scopes=self.scopes,
        )
        request_adapter = GraphRequestAdapter(
            auth_provider,
            client=self._http_client,
        )
        return GraphServiceClient(request_adapter=request_adapter)

    async def aclose(self) -> None:
        """
        Close the Graph transport and the credential, dropping both from the
        cache so the next access rebuilds them.
        """
        self.__dict__.pop('client', None)
        http_client: AsyncClient | None = self.__dict__.pop('_http_client', None)
        if http_client is not None:
            await http_client.aclose()
        credential = self.__dict__.pop('credential', None)
        if credential is not None:
            # azure.identity credentials close synchronously; the refresh-token
            # credential's close is a coroutine.
            closed = credential.close()
            if isawaitable(closed):
                await closed

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        await self.aclose()


class MSAppClientModel(MSBaseClientModel):
    """
    Microsoft Graph client using application permissions.

    Authenticates via ``ClientSecretCredential`` (client credentials grant).
    The token is acquired as the application itself, not on behalf of a user.

    Args:
        tenant_id (str): Azure AD tenant id.
        client_id (str): Azure AD application (client) id.
        client_secret (str): Azure AD application client secret.
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): HTTP proxy URL applied to both Graph API
            requests and token acquisition (Azure AD authentication).
            Defaults to None.
        timeout (int): Graph API request timeout in seconds. Defaults to 120.
        scopes (list[str]): OAuth scopes requested for the token.
            Defaults to ['https://graph.microsoft.com/.default'].

    Attributes:
        credential (ClientSecretCredential): Cached Azure credential.
        client (GraphServiceClient): Cached Graph SDK client.

    See:
        https://github.com/microsoftgraph/msgraph-sdk-python

    Example:
        >>> import asyncio
        >>> api = MSAppClientModel(
        ...     tenant_id='<tenant>',
        ...     client_id='<client>',
        ...     client_secret='<secret>',
        ...     verify=False,
        ... )
        >>> async def main():
        ...     messages = await api.client.teams.by_team_id(
        ...         '<team-id>',
        ...     ).channels.by_channel_id(
        ...         '<channel-id>',
        ...     ).messages.get()
        ...     for msg in messages.value:
        ...         print(msg.body.content)
        >>> asyncio.run(main())
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
            proxies=self._proxies,
        )


class MSDelegatedClientModel(MSBaseClientModel):
    """
    Microsoft Graph client using delegated permissions via ROPC.

    Authenticates via ``UsernamePasswordCredential`` (ROPC grant).
    The token is acquired on behalf of the specified user, enabling
    delegated-only permissions such as ``ChatMessage.Send``.
    Requires admin consent or prior user consent for the requested scopes.

    Use this only for accounts that authenticate purely with a
    username and password. Any other delegated-permission scenario --
    accounts with MFA or Conditional Access, non-interactive runtimes
    that cannot show a device code prompt -- should use
    ``MSDelegatedRefreshTokenClientModel`` instead. Bootstrap a refresh
    token once via ``clients.ms.create_refresh_token`` and store
    it for the runtime client to consume.

    Args:
        tenant_id (str): Azure AD tenant id.
        client_id (str): Azure AD application (client) id.
        client_secret (str): Azure AD application client secret.
        username (str): User email address for delegated authentication.
        password (str): User password for delegated authentication.
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): HTTP proxy URL applied to both Graph API
            requests and token acquisition (Azure AD authentication).
            Defaults to None.
        timeout (int): Graph API request timeout in seconds. Defaults to 120.
        scopes (list[str]): OAuth scopes requested for the token.
            Defaults to ['https://graph.microsoft.com/.default'].

    Attributes:
        credential (UsernamePasswordCredential): Cached Azure credential.
        client (GraphServiceClient): Cached Graph SDK client.

    See:
        https://github.com/microsoftgraph/msgraph-sdk-python

    Example:
        >>> import asyncio
        >>> from msgraph.generated.models.chat_message import ChatMessage
        >>> from msgraph.generated.models.item_body import ItemBody
        >>> from msgraph.generated.models.body_type import BodyType
        >>> api = MSDelegatedClientModel(
        ...     tenant_id='<tenant>',
        ...     client_id='<client>',
        ...     client_secret='<secret>',
        ...     username='user@domain.com',
        ...     password='<password>',
        ...     verify=False,
        ... )
        >>> async def main():
        ...     message = ChatMessage(
        ...         body=ItemBody(
        ...             content_type=BodyType.Text,
        ...             content='Hello from Graph SDK',
        ...         ),
        ...     )
        ...     await api.client.chats.by_chat_id(
        ...         '<chat-id>',
        ...     ).messages.post(message)
        >>> asyncio.run(main())
    """

    client_secret: Annotated[
        str,
        Field(repr=False)
    ]

    username: Annotated[
        str,
        Field(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
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
            connection_verify=self.verify,
            username=self.username,
            password=self.password,
            proxies=self._proxies,
        )


class MSDelegatedRefreshTokenClientModel(MSBaseClientModel):
    """
    Microsoft Graph client using delegated permissions via a
    pre-acquired OAuth2 refresh token.

    Like ``MSDelegatedClientModel``, the token is acquired on behalf of
    a specific user and supports delegated-only permissions such as
    ``ChatMessage.Send``. The difference is the credential type: this
    variant skips ``UsernamePasswordCredential`` (ROPC) entirely and
    relies on a refresh token that was minted out-of-band by a prior
    interactive flow (e.g. device code via
    ``clients.ms.create_refresh_token``).

    Use this instead of ``MSDelegatedClientModel`` when:
        * The user account enforces MFA or Conditional Access policies.
          ROPC does not support MFA, so ``MSDelegatedClientModel`` fails
          with ``AADSTS50076`` / ``AADSTS50079`` for those accounts; a
          refresh token issued by a flow that did satisfy MFA continues
          to work here.
        * The runtime environment is non-interactive (cron, batch
          schedulers, serverless) and cannot prompt for device codes.
        * Delegated permissions are required and ``MSAppClientModel``
          (application permissions) is not an acceptable substitute.

    On every call the credential exchanges the stored refresh token at
    the OAuth2 token endpoint. No prompt is ever shown; if the refresh
    token is invalid or expired, ``credential.get_token`` raises.

    Microsoft rotates the refresh token on every grant. Each rotation is
    written back onto this model, so ``refresh_token`` keeps mirroring the
    latest issued value rather than the one the model was constructed with.
    Persisting it is still the caller's job: re-serialize the model once the
    work is done, for example ``model.model_dump_json()`` back into a secret
    store, or the stored token goes stale and a later rotation invalidates it.

    Args:
        tenant_id (str): Azure AD tenant id.
        client_id (str): Azure AD application (client) id.
        refresh_token (str): OAuth2 refresh token previously obtained
            via an interactive flow (e.g. device code). Use
            ``clients.ms.create_refresh_token`` to mint one.
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): HTTP proxy URL applied to both Graph API
            requests and token acquisition (Azure AD authentication).
            Defaults to None.
        timeout (int): Graph API request timeout in seconds. Defaults to 120.
        scopes (list[str]): OAuth scopes requested for the token.
            Defaults to ['https://graph.microsoft.com/.default'].

    Attributes:
        credential (_RefreshTokenCredential): Cached refresh-token-backed
            credential. Rotations are mirrored back onto ``refresh_token``.
        client (GraphServiceClient): Cached Graph SDK client.

    See:
        https://github.com/microsoftgraph/msgraph-sdk-python
        https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow#refresh-the-access-token

    Example:
        >>> import asyncio
        >>> from msgraph.generated.models.chat_message import ChatMessage
        >>> from msgraph.generated.models.item_body import ItemBody
        >>> from msgraph.generated.models.body_type import BodyType
        >>> api = MSDelegatedRefreshTokenClientModel(
        ...     tenant_id='<tenant>',
        ...     client_id='<client>',
        ...     refresh_token='<refresh-token>',
        ...     verify=False,
        ... )
        >>> async def main():
        ...     message = ChatMessage(
        ...         body=ItemBody(
        ...             content_type=BodyType.Text,
        ...             content='Hello from Graph SDK',
        ...         ),
        ...     )
        ...     await api.client.teams.by_team_id(
        ...         '<team-id>',
        ...     ).channels.by_channel_id(
        ...         '<channel-id>',
        ...     ).messages.post(message)
        >>> asyncio.run(main())
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
            on_refresh=self._sync_refresh_token,
        )
