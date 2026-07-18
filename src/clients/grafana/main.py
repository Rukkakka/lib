from functools import cached_property

from httpx import (
    Client,
    AsyncClient
)

from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception
)

from pydantic import Field

from clients.utility import (
    log_retry_before_sleep,
    create_base_url,
    should_retry_idempotent
)
from clients.base import BaseClientModel
from clients.grafana.models.request import (
    GrafanaRequestHeaderModel,
    GrafanaDsQueryRequestParameterModel,
    GrafanaDsQueryRequestPayloadModel
)
from clients.grafana.models.response import GrafanaDsQueryResponseModel

from typing import (
    Annotated,
    ClassVar
)


class GrafanaClientModel(BaseClientModel):
    """Grafana HTTP client for the datasource query API.

    Lazily creates and caches sync (`_client`) and async (`_async_client`)
    httpx clients built from the connection settings, and exposes
    `run_request_ds_query` / `arun_request_ds_query` to POST datasource
    queries with idempotent retry. Inherits `url_schema`, `verify`, `proxy`,
    `timeout`, and the close/context-manager surface from `BaseClientModel`.

    Args:
        host: Grafana host, without scheme (e.g. 'grafana.acme.com').
        token: API token; sent as a Bearer `Authorization` header.
        user_agent: Value for the `User-Agent` request header.

    Attributes:
        ds_query_endpoint: Datasource query API path ('/api/ds/query').
        base_url: Full base URL derived from `url_schema` and `host`.
        base_header: Request headers built from `token` and `user_agent`.

    Example:
        >>> with GrafanaClientModel(
        ...     host='grafana.acme.com',
        ...     token='glsa_...',
        ...     user_agent='my-app/1.0',
        ... ) as client:
        ...     client.run_request_ds_query(parameter, payload)
    """

    ds_query_endpoint: ClassVar[str] = '/api/ds/query'

    host: Annotated[
        str,
        Field()
    ]

    token: Annotated[
        str,
        Field(repr=False)
    ]

    user_agent: Annotated[
        str,
        Field()
    ]

    @property
    def base_url(self) -> str:
        return create_base_url(
            schema=self.url_schema,
            host=self.host
        )
    
    @property
    def base_header(self) -> GrafanaRequestHeaderModel:
        return GrafanaRequestHeaderModel(
            authorization=self.token,
            user_agent=self.user_agent
        )
    
    @cached_property
    def _client(self) -> Client:
        return Client(
            base_url=self.base_url,
            headers=self.base_header.model_dump(by_alias=True),
            verify=self.verify,
            timeout=self.timeout,
            proxy=self.proxy
        )
    
    @cached_property
    def _async_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self.base_url,
            headers=self.base_header.model_dump(by_alias=True),
            verify=self.verify,
            timeout=self.timeout,
            proxy=self.proxy
        )
    
    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    def run_request_ds_query(
        self,
        parameter: GrafanaDsQueryRequestParameterModel,
        payload: GrafanaDsQueryRequestPayloadModel
    ) -> GrafanaDsQueryResponseModel:
        """Run a datasource query via `POST /api/ds/query`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Query-string parameters (e.g. `ds_type`), sent as `params`.
            payload: Request body — `queries` (list of per-datasource query
                dicts) plus the `from`/`to` time range.

        Returns:
            GrafanaDsQueryResponseModel: Parsed response, keyed by query `refId`.

        See:
            https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/#query-a-data-source
        """
        response = self._client.post(
            url=self.ds_query_endpoint,
            params=parameter.model_dump(by_alias=True),
            json=payload.model_dump(by_alias=True)
        )
        response.raise_for_status()
        return GrafanaDsQueryResponseModel.model_validate(response.json())
    
    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_ds_query(
        self,
        parameter: GrafanaDsQueryRequestParameterModel,
        payload: GrafanaDsQueryRequestPayloadModel
    ) -> GrafanaDsQueryResponseModel:
        """Async variant of `run_request_ds_query` (`POST /api/ds/query`).

        Same retry behaviour, `parameter`/`payload`, and return type as
        `run_request_ds_query`; see it for details.

        See:
            https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/#query-a-data-source
        """
        response = await self._async_client.post(
            url=self.ds_query_endpoint,
            params=parameter.model_dump(by_alias=True),
            json=payload.model_dump(by_alias=True)
        )
        response.raise_for_status()
        return GrafanaDsQueryResponseModel.model_validate(response.json())