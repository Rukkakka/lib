import asyncio
from functools import cached_property
from types import TracebackType

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

from typing import (
    Annotated,
    Any
)


class ClickHouseModel(BaseModel):
    """
    Client model for creating ClickHouse clients with validated connection settings.

    This model centralizes synchronous and asynchronous client creation via
    `clickhouse-connect`.

    Args:
        host (str): ClickHouse host address.
        port (int): ClickHouse HTTP(S) port.
        username (str): Username for authentication.
        password (str): Password for authentication.
        connect_timeout (int): Connection timeout in seconds. Defaults to 120.
        send_receive_timeout (int): Request I/O timeout in seconds.
            Defaults to 300.
        client_options (dict[str, Any]): Extra keyword arguments passed as is
            to `get_client()` / `get_async_client()` (e.g. ``database``,
            ``secure``, ``settings``). Keys that overlap with the fields
            above take precedence over them. Defaults to {}.

    Attributes:
        client (Client): Cached synchronous ClickHouse client.
        async_client (Callable[..., Awaitable[AsyncClient]]): Coroutine method
            returning the asynchronous client cached for the running event loop.

    Example:
        >>> with ClickHouseModel(
        ...     host='clickhouse.example.com',
        ...     port=8443,
        ...     username='user',
        ...     password='secret',
        ... ) as api:
        ...     rows = api.client.query('SELECT 1').result_set

        >>> async def run_query():
        ...     async with ClickHouseModel(
        ...         host='clickhouse.example.com',
        ...         port=8443,
        ...         username='user',
        ...         password='secret',
        ...     ) as api:
        ...         client = await api.async_client()
        ...         result = await client.query('SELECT 1')
        ...         return result.result_rows
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    host: str

    port: int

    username: str

    password: Annotated[
        str,
        Field(repr=False)
    ]

    connect_timeout: Annotated[
        int,
        Field(gt=0)
    ] = 120

    send_receive_timeout: Annotated[
        int,
        Field(gt=0)
    ] = 300

    client_options: Annotated[
        dict[str, Any],
        Field(repr=False)
    ] = {}

    def _client_kwargs(self) -> dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'connect_timeout': self.connect_timeout,
            'send_receive_timeout': self.send_receive_timeout,
            **self.client_options,
        }

    @cached_property
    def client(self) -> Client:
        return get_client(**self._client_kwargs())

    async def async_client(self) -> AsyncClient:
        """
        Return the asynchronous client for the running event loop, creating it
        on first call.

        clickhouse-connect's AsyncClient holds an aiohttp session bound to the
        event loop it was created on, so the client is cached together with
        that loop and rebuilt when called from a different one. It is cached
        manually into `self.__dict__` under `_async_client` because it has to
        be awaited, which `@cached_property` cannot do.

        Note:
            A client left behind by a loop change is dropped without being
            closed, since its loop may already be gone. Close each loop's client
            with `aclose()` or `async with` before that loop ends.
        """
        loop = asyncio.get_running_loop()
        cached: tuple[asyncio.AbstractEventLoop, AsyncClient] | None = (
            self.__dict__.get('_async_client')
        )
        if cached is None or cached[0] is not loop:
            cached = (loop, await get_async_client(**self._client_kwargs()))
            self.__dict__['_async_client'] = cached
        return cached[1]

    def close(self) -> None:
        client: Client | None = self.__dict__.pop('client', None)
        if client is not None:
            client.close()

    async def aclose(self) -> None:
        cached: tuple[asyncio.AbstractEventLoop, AsyncClient] | None = (
            self.__dict__.pop('_async_client', None)
        )
        if cached is not None:
            await cached[1].close()

    def __enter__(self) -> 'ClickHouseModel':
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        self.close()

    async def __aenter__(self) -> 'ClickHouseModel':
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        await self.aclose()
