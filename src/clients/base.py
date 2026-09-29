from abc import (
    ABC,
    abstractmethod
)
from types import TracebackType

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from httpx import (
    Client,
    AsyncClient
)

from typing import (
    Annotated,
    Literal,
    TypeVar
)


_T = TypeVar('_T', bound='BaseClientModel')


class BaseClientModel(BaseModel, ABC):
    """
    Shared base model for HTTP API clients.

    This class defines shared connection options (`url_schema`, `verify`,
    `proxy`, `timeout`) and a unified lifecycle interface for sync/async clients.
    Subclasses declare their own `host`.

    Args:
        url_schema (Literal['http', 'https']): URL scheme used to build `base_url`.
            Defaults to 'https'.
        verify (bool): TLS certificate verification flag used by HTTP clients.
            Defaults to True.
        proxy (str | None): Optional proxy URL passed to HTTP clients.
            Defaults to None.
        timeout (int): Request timeout in seconds. Defaults to 120.

    Attributes:
        _client (Client): Cached synchronous HTTP client (implemented by subclass).
        _async_client (AsyncClient): Cached asynchronous HTTP client
            (implemented by subclass).
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    url_schema: Literal['http', 'https'] = 'https'

    verify: bool = True

    proxy: str | None = None

    timeout: Annotated[
        int,
        Field(gt=0)
    ] = 120

    @property
    @abstractmethod
    def _client(self) -> Client:
        """
        Synchronous HTTP client. Subclasses must override this with
        ``@cached_property`` so the underlying transport is reused across
        calls and `BaseClientModel.close()` can locate it via
        ``__dict__.pop('_client', None)``.

        ``@property`` + ``@abstractmethod`` is used here purely to mark the
        attribute abstract. ``@cached_property`` cannot be combined with
        ``@abstractmethod`` -- the abstract marker fails to propagate, so
        ABC stops blocking incomplete subclasses from instantiating. Keep
        the abstract declaration as a plain property and let the concrete
        subclass apply the caching decorator.
        """
        ...

    @property
    @abstractmethod
    def _async_client(self) -> AsyncClient:
        """
        Asynchronous HTTP client. Subclasses must override this with
        ``@cached_property`` so the underlying transport is reused across
        calls and `BaseClientModel.aclose()` can locate it via
        ``__dict__.pop('_async_client', None)``.

        See ``_client`` for why ``@property`` + ``@abstractmethod`` is used
        instead of ``@cached_property`` + ``@abstractmethod``.
        """
        ...

    def close(self) -> None:
        client: Client | None = self.__dict__.pop('_client', None)
        if client is not None:
            client.close()

    async def aclose(self) -> None:
        async_client: AsyncClient | None = self.__dict__.pop('_async_client', None)
        if async_client is not None:
            await async_client.aclose()

    def __enter__(self: _T) -> _T:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        self.close()

    async def __aenter__(self: _T) -> _T:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        await self.aclose()
