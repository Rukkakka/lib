from abc import (
    ABC,
    abstractmethod
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from httpx import (
    Client,
    AsyncClient
)

from types import TracebackType

from typing import (
    Annotated,
    Optional,
    Literal,
    Type
)

class BaseClientModel(BaseModel, ABC):
    """Abstract base for pydantic models wrapping an `httpx` client.

    Collects the transport settings shared by the HTTP client wrappers and
    provides `close()`/`aclose()` plus `with`/`async with` support. Subclasses
    implement `_client` and `_async_client` as `@cached_property`, caching the
    built client into `self.__dict__` under those names so the cleanup methods
    here can find and discard it.

    Args:
        url_schema: Transport scheme, 'http' or 'https'. Defaults to 'https'.
        verify: Whether to verify TLS certificates. Defaults to True.
        proxy: Optional proxy URL to route requests through.
        timeout: Request timeout in seconds. Defaults to 120.

    Attributes:
        _client: Cached sync `Client`, built by the subclass on first access.
        _async_client: Cached async `AsyncClient`, built by the subclass on
            first access.
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    url_schema: Annotated[
        Literal['http', 'https'],
        Field()
    ] = 'https'

    verify: Annotated[
        bool,
        Field()
    ] = True

    proxy: Annotated[
        Optional[str],
        Field()
    ] = None

    timeout: Annotated[
        int,
        Field()
    ] = 120

    @property
    @abstractmethod
    def _client(self) -> Client:
        ...

    @property
    @abstractmethod
    def _async_client(self) -> AsyncClient:
        ...

    def close(self) -> None:
        client: Optional[Client] = self.__dict__.pop('_client', None)
        if client is not None:
            client.close()

    async def aclose(self) -> None:
        async_client: Optional[AsyncClient] = self.__dict__.pop('_async_client', None)
        if async_client is not None:
            await async_client.aclose()

    def __enter__(self) -> 'BaseClientModel':
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    async def __aenter__(self) -> 'BaseClientModel':
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()