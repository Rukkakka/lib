from functools import cached_property

from httpx import (
    Client,
    AsyncClient
)

from pydantic import Field

from clients.utility import (
    create_base_url,
    RequestModel
)
from clients.base import BaseClientModel

from typing import Annotated


class GokrOpenDataRequestParameterModel(RequestModel):
    service_key: Annotated[str, Field(alias='serviceKey')]


class BaseGoKrOpenDataClientModel(BaseClientModel):
    """Abstract base for 공공데이터포털 (data.go.kr) clients.

    Builds sync (`_client`) and async (`_async_client`) httpx clients carrying
    the portal base URL and the `service_key` parameter, so subclasses and the
    per-service clients they hand these to need only supply the endpoint path
    and its own parameters. Inherits `url_schema`, `verify`, `proxy`,
    `timeout`, and the close/context-manager surface from `BaseClientModel`.

    Args:
        host: Portal host, without scheme. Defaults to 'apis.data.go.kr/'.
        service_key: 공공데이터포털 인증키, in its decoded form — httpx
            percent-encodes it, so an already-encoded key is double-encoded
            and rejected.

    Attributes:
        base_url: Full base URL derived from `url_schema` and `host`.
        base_parameter: The `service_key` query parameter sent on every request.
    """

    host: Annotated[
        str,
        Field()
    ] = 'apis.data.go.kr/'

    service_key: Annotated[
        str,
        Field(repr=False)
    ]

    @property
    def base_url(self) -> str:
        return create_base_url(
            schema=self.url_schema,
            host=self.host
        )
    
    @property
    def base_parameter(self) -> GokrOpenDataRequestParameterModel:
        return GokrOpenDataRequestParameterModel(service_key=self.service_key)
    
    @cached_property
    def _client(self) -> Client:
        return Client(
            base_url=self.base_url,
            params=self.base_parameter.model_dump(by_alias=True),
            verify=self.verify,
            timeout=self.timeout,
            proxy=self.proxy
        )
    
    @cached_property
    def _async_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self.base_url,
            params=self.base_parameter.model_dump(by_alias=True),
            verify=self.verify,
            timeout=self.timeout,
            proxy=self.proxy
        )