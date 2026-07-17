from functools import cached_property

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from clickhouse_connect import (
    get_client,
    get_async_client
)
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.asyncclient import AsyncClient

from types import TracebackType

from typing import (
    Annotated,
    Optional,
    Type
)

class ClickHouseModel(BaseModel):
    """Pydantic model wrapping a ClickHouse sync/async client connection.

    Lazily creates and caches a `Client`/`AsyncClient` on first access via
    `client`/`async_client`, and supports both `with`/`async with` and
    explicit `close()`/`aclose()` for cleanup.

    Unlike `client` (a `@cached_property`), `async_client` is a coroutine
    method — call it as `await model.async_client()`. An async client must be
    built with `await get_async_client(...)`, which `@cached_property` cannot
    do, so it is cached manually into `self.__dict__`.

    Args:
        host: ClickHouse server hostname.
        port: ClickHouse server port.
        username: Username used for authentication.
        password: Password used for authentication.
        connect_timeout: Connection timeout in seconds. Defaults to 120.
        send_receive_timeout: Send/receive timeout in seconds. Defaults to 300.

    Attributes:
        client: Cached sync `Client`, created on first access.
        async_client: Coroutine method returning the cached async
            `AsyncClient`; awaited and cached on first call.

    Example:
        >>> with ClickHouseModel(
        ...     host='localhost',
        ...     port=8123,
        ...     username='default',
        ...     password='',
        ... ) as model:
        ...     model.client.query('SELECT 1')
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    host: Annotated[
        str,
        Field()
    ]

    port: Annotated[
        int,
        Field()
    ]

    username: Annotated[
        str,
        Field()
    ]

    password: Annotated[
        str,
        Field(repr=False)
    ]

    connect_timeout: Annotated[
        int,
        Field()
    ] = 120

    send_receive_timeout: Annotated[
        int,
        Field()
    ] = 300

    @cached_property
    def client(self) -> Client:
        return get_client(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            connect_timeout=self.connect_timeout,
            send_receive_timeout=self.send_receive_timeout
        )
    
    async def async_client(self) -> AsyncClient:
        """Return the cached async client, creating it on first call.

        A coroutine method rather than a property because the client is built
        with `await get_async_client(...)`, which `@cached_property` cannot do;
        the result is cached manually into `self.__dict__`.
        """
        if 'async_client' not in self.__dict__:
            self.__dict__['async_client'] = await get_async_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                connect_timeout=self.connect_timeout,
                send_receive_timeout=self.send_receive_timeout
            )
        return self.__dict__['async_client']

    def close(self) -> None:
        client: Optional[Client] = self.__dict__.pop('client', None)
        if client is not None:
            client.close()

    async def aclose(self) -> None:
        async_client: Optional[AsyncClient] = self.__dict__.pop('async_client', None)
        if async_client is not None:
            await async_client.close()

    def __enter__(self) -> 'ClickHouseModel':
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    async def __aenter__(self) -> 'ClickHouseModel':
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()