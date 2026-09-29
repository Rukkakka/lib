from functools import cached_property
from types import TracebackType

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from jira import JIRA

from clients.utility import create_base_url

from typing import (
    Annotated,
    Any,
    Literal,
)


class JiraClientModel(BaseModel):
    """
    Thin SDK-backed client model for Jira-compatible issue tracking APIs.

    This wrapper centralizes connection settings and exposes the underlying
    `jira.JIRA` client through `client`; issue operations are called on it
    directly.

    Args:
        url_schema (Literal['http', 'https']): URL scheme to use. Defaults to 'https'.
        host (str): Jira host address, without scheme.
        token (str | None): API token or bearer token used for authentication.
            Defaults to None.
        id (str | None): Login ID for basic-auth style Jira access.
            Defaults to None.
        password (str | None): Password for basic-auth style Jira access.
            Defaults to None.
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): Optional proxy URL for HTTP and HTTPS requests.
            Defaults to None.

    Attributes:
        server (str): Computed Jira server URL.
        client (JIRA): Cached SDK client instance.

    Example:
        >>> with JiraClientModel(
        ...     host='jira.example.com',
        ...     token='your_token',
        ... ) as jira:
        ...     issues = jira.client.search_issues("project = 'PROJ'", maxResults=10)
        ...     print(len(issues))
    """

    model_config = ConfigDict(
        extra='forbid',
        arbitrary_types_allowed=True,
    )

    url_schema: Literal['http', 'https'] = 'https'

    host: str

    token: Annotated[
        str | None,
        Field(repr=False),
    ] = None

    id: str | None = None

    password: Annotated[
        str | None,
        Field(repr=False),
    ] = None

    verify: bool = True

    proxy: str | None = None

    @model_validator(mode='after')
    def validate_auth(self) -> 'JiraClientModel':
        if self.token is not None:
            return self
        if self.id is not None and self.password is not None:
            return self
        raise ValueError('Either token or both id and password must be provided.')

    @property
    def server(self) -> str:
        return create_base_url(schema=self.url_schema, host=self.host)

    @property
    def options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            'verify': self.verify,
        }
        if self.proxy is not None:
            options['proxies'] = {
                'http': self.proxy,
                'https': self.proxy,
            }
        return options

    @cached_property
    def client(self) -> JIRA:
        if self.token is not None:
            return JIRA(
                server=self.server,
                token_auth=self.token,
                options=self.options,
            )
        if self.id is None or self.password is None:
            raise ValueError('Either token or both id and password must be provided.')
        return JIRA(
            server=self.server,
            basic_auth=(self.id, self.password),
            options=self.options,
        )

    def close(self) -> None:
        client: JIRA | None = self.__dict__.pop('client', None)
        if client is not None and hasattr(client, 'close'):
            client.close()

    def __enter__(self) -> 'JiraClientModel':
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        self.close()
