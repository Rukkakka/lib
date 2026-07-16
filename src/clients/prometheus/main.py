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
from clients.prometheus.models.dto import PrometheusRequestHeaderModel
from clients.prometheus.models.request import (
    PrometheusQueryV1RequestParameterModel,
    PrometheusQueryRangeV1RequestParameterModel
)
from clients.prometheus.models.response import (
    PrometheusQueryV1ResponseModel,
    PrometheusQueryRangeV1ResponseModel
)

from typing import (
    Annotated,
    ClassVar,
    Optional
)


class PrometheusClientModel(BaseClientModel):
    """Prometheus HTTP client for the query API.

    Lazily creates and caches sync (`_client`) and async (`_async_client`)
    httpx clients built from the connection settings, and exposes
    `run_request_query_v1` / `run_request_query_range_v1` (plus their async
    `arun_*` variants) to call `/api/v1/query` and `/api/v1/query_range` with
    idempotent retry. Inherits `url_schema`, `verify`, `proxy`, `timeout`, and
    the close/context-manager surface from `BaseClientModel`.

    Args:
        host: Prometheus host, without scheme (e.g. 'prometheus.acme.com').
        user_agent: Value for the `User-Agent` request header.
        token: Optional API token; sent as a Bearer `Authorization` header
            when set. Defaults to None (no auth header).

    Attributes:
        query_v1_endpoint: Instant query API path ('/api/v1/query').
        query_range_v1_endpoint: Range query API path ('/api/v1/query_range').
        base_url: Full base URL derived from `url_schema` and `host`.
        base_header: Request headers built from `token` and `user_agent`.

    Example:
        >>> with PrometheusClientModel(
        ...     host='prometheus.acme.com',
        ...     user_agent='my-app/1.0',
        ... ) as client:
        ...     client.run_request_query_v1(parameter)
    """

    query_v1_endpoint: ClassVar[str] = '/api/v1/query'
    query_range_v1_endpoint: ClassVar[str] = '/api/v1/query_range'

    host: Annotated[
        str,
        Field()
    ]

    user_agent: Annotated[
        str,
        Field()
    ]

    token: Annotated[
        Optional[str],
        Field(default=None, repr=False)
    ]

    @property
    def base_url(self) -> str:
        return create_base_url(
            schema=self.url_schema,
            host=self.host
        )

    @property
    def base_header(self) -> PrometheusRequestHeaderModel:
        return PrometheusRequestHeaderModel(
            authorization=self.token,
            user_agent=self.user_agent
        )

    @cached_property
    def _client(self) -> Client:
        return Client(
            base_url=self.base_url,
            headers=self.base_header.model_dump(by_alias=True, exclude_none=True),
            verify=self.verify,
            timeout=self.timeout,
            proxy=self.proxy
        )

    @cached_property
    def _async_client(self) -> AsyncClient:
        return AsyncClient(
            base_url=self.base_url,
            headers=self.base_header.model_dump(by_alias=True, exclude_none=True),
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
    def run_request_query_v1(
        self,
        parameter: PrometheusQueryV1RequestParameterModel
    ) -> PrometheusQueryV1ResponseModel:
        """Run an instant query via `GET /api/v1/query`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Instant-query parameters — `query` (PromQL, required)
                plus optional `time` and `timeout`.

        Returns:
            PrometheusQueryV1ResponseModel: Parsed response (`status` + `data`).

        See:
            https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries
        """
        response = self._client.get(
            url=self.query_v1_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return PrometheusQueryV1ResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_query_v1(
        self,
        parameter: PrometheusQueryV1RequestParameterModel
    ) -> PrometheusQueryV1ResponseModel:
        """Async variant of `run_request_query_v1` (`GET /api/v1/query`).

        Same retry behaviour, `parameter`, and return type as
        `run_request_query_v1`; see it for details.

        See:
            https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries
        """
        response = await self._async_client.get(
            url=self.query_v1_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return PrometheusQueryV1ResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    def run_request_query_range_v1(
        self,
        parameter: PrometheusQueryRangeV1RequestParameterModel
    ) -> PrometheusQueryRangeV1ResponseModel:
        """Run a range query via `GET /api/v1/query_range`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Range-query parameters — `query` (PromQL), `start`,
                `end` and `step` (all required) plus optional `timeout`.

        Returns:
            PrometheusQueryRangeV1ResponseModel: Parsed response
                (`status` + `data`).

        See:
            https://prometheus.io/docs/prometheus/latest/querying/api/#range-queries
        """
        response = self._client.get(
            url=self.query_range_v1_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return PrometheusQueryRangeV1ResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_query_range_v1(
        self,
        parameter: PrometheusQueryRangeV1RequestParameterModel
    ) -> PrometheusQueryRangeV1ResponseModel:
        """Async variant of `run_request_query_range_v1` (`GET /api/v1/query_range`).

        Same retry behaviour, `parameter`, and return type as
        `run_request_query_range_v1`; see it for details.

        See:
            https://prometheus.io/docs/prometheus/latest/querying/api/#range-queries
        """
        response = await self._async_client.get(
            url=self.query_range_v1_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return PrometheusQueryRangeV1ResponseModel.model_validate(response.json())
