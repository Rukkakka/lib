from functools import cached_property

from pydantic import (
    BaseModel,
    Field
)

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from gspread.client import Client
from gspread import authorize

from types import TracebackType

from typing import (
    Annotated,
    Optional,
    Any,
    Callable,
    Type,
    TYPE_CHECKING
)

if TYPE_CHECKING:
    # pip install google-api-python-client-stubs
    from googleapiclient._apis.drive.v3.resources import DriveResource # type: ignore


class SyncingCredentials(Credentials):
    """Credentials that report every refresh back to an owner callback.

    Google's client libraries refresh the access token in-place whenever it
    expires (both the explicit ``refresh`` call below and the implicit ones
    triggered while a Drive/Sheets client is in use). The callback lets the
    owning model persist the newly issued values.
    """

    def __init__(
        self,
        *args: Any,
        on_refresh: Optional[Callable[['SyncingCredentials'], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._on_refresh = on_refresh

    def refresh(self, request: Request) -> None:
        super().refresh(request)
        if self._on_refresh is not None:
            self._on_refresh(self)


class GoogleCredentialsModel(BaseModel):
    """Pydantic model holding refreshable Google OAuth user credentials.

    Lazily builds and caches a `SyncingCredentials` on first access via
    `credentials`, refreshing it immediately if the access token is already
    expired. Refreshes — both that one and the implicit ones the Google client
    libraries perform later — are written back onto this model, so `token` and
    `refresh_token` always reflect the newest issued values and can be
    persisted after use.

    Args:
        token: OAuth access token.
        refresh_token: OAuth refresh token used to mint new access tokens.
        token_uri: Token endpoint the refresh request is sent to.
        client_id: OAuth client ID.
        client_secret: OAuth client secret.

    Attributes:
        credentials: Cached `Credentials`, created on first access.
    """

    token: Annotated[
        str,
        Field(repr=False)
    ]

    refresh_token: Annotated[
        str,
        Field(repr=False)
    ]

    token_uri: Annotated[
        str,
        Field()
    ]

    client_id: Annotated[
        str,
        Field()
    ]

    client_secret: Annotated[
        str,
        Field(repr=False)
    ]

    def _sync_from_credentials(self, creds: Credentials) -> None:
        self.token = creds.token
        if creds.refresh_token:
            self.refresh_token = creds.refresh_token

    @cached_property
    def credentials(self) -> Credentials:
        creds = SyncingCredentials(
            token=self.token,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            client_id=self.client_id,
            client_secret=self.client_secret,
            on_refresh=self._sync_from_credentials
        )
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        return creds
    

class GoogleModel(GoogleCredentialsModel):
    """Builds an arbitrary `googleapiclient` service from Google credentials.

    Lazily creates and caches the discovery-built service client on first
    access via `client`. Inherits the credential fields and refresh-syncing
    behaviour from `GoogleCredentialsModel`.

    Args:
        service_name: Google API service to build (e.g. 'drive', 'sheets').
        version: Service version (e.g. 'v3').
        static_discovery: Whether to build from the bundled static discovery
            document instead of fetching it. Defaults to False.

    Attributes:
        client: Cached service client, created on first access.

    Example:
        >>> model = GoogleModel(
        ...     token='...',
        ...     refresh_token='...',
        ...     token_uri='https://oauth2.googleapis.com/token',
        ...     client_id='...',
        ...     client_secret='...',
        ...     service_name='drive',
        ...     version='v3',
        ... )
        >>> model.client.files().list().execute()
    """

    service_name: Annotated[
        str,
        Field()
    ]

    version: Annotated[
        str,
        Field()
    ]

    static_discovery: Annotated[
        bool,
        Field()
    ] = False

    @cached_property
    def client(self) -> Any:
        return build(
            serviceName=self.service_name,
            version=self.version,
            credentials=self.credentials,
            static_discovery=self.static_discovery
        )

    
class GdriveModel(GoogleModel):
    """Google Drive client, pinned to the Drive v3 API.

    A `GoogleModel` with `service_name`/`version` defaulted to Drive v3 and the
    `client` type narrowed to `DriveResource`, plus `close()` and `with`
    support for cleanup.

    Args:
        service_name: Google API service to build. Defaults to 'drive'.
        version: Service version. Defaults to 'v3'.

    Attributes:
        client: Cached `DriveResource`, created on first access.

    Example:
        >>> with GdriveModel(
        ...     token='...',
        ...     refresh_token='...',
        ...     token_uri='https://oauth2.googleapis.com/token',
        ...     client_id='...',
        ...     client_secret='...',
        ... ) as model:
        ...     model.client.files().list().execute()
    """

    service_name: Annotated[
        str,
        Field()
    ] = 'drive'

    version: Annotated[
        str,
        Field()
    ] = 'v3'

    @cached_property
    def client(self) -> 'DriveResource':
        return super().client
    
    def close(self) -> None:
        client: Optional['DriveResource'] = self.__dict__.pop('client', None)
        if client is not None:
            client.close()

    def __enter__(self) -> 'GdriveModel':
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()


class GspreadModel(GoogleCredentialsModel):
    """Google Sheets client backed by `gspread`.

    Lazily authorizes and caches a `gspread` `Client` on first access via
    `client`. Inherits the credential fields and refresh-syncing behaviour from
    `GoogleCredentialsModel`. Unlike `GdriveModel` there is nothing to close —
    `gspread` manages its own session.

    Attributes:
        client: Cached `gspread` `Client`, created on first access.

    Example:
        >>> model = GspreadModel(
        ...     token='...',
        ...     refresh_token='...',
        ...     token_uri='https://oauth2.googleapis.com/token',
        ...     client_id='...',
        ...     client_secret='...',
        ... )
        >>> model.client.open('My Sheet').sheet1.get_all_records()
    """

    @cached_property
    def client(self) -> Client:
        return authorize(credentials=self.credentials)