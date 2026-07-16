from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception
)

from httpx import (
    Client,
    AsyncClient
)

from clients.utility import (
    log_retry_before_sleep,
    should_retry_idempotent
)
from clients.gokr_opendata.kma.models.request import (
    KMAGetMidFcstRequestParameterModel,
    KMAGetMidLandFcstRequestParameterModel,
    KMAGetMidTaRequestParameterModel,
    KMAGetMidSeaFcstRequestParameterModel
)
from clients.gokr_opendata.kma.models.response import (
    KMAGetMidFcstResponseModel,
    KMAGetMidLandFcstResponseModel,
    KMAGetMidTaResponseModel,
    KMAGetMidSeaFcstResponseModel
)

from typing import ClassVar


class KMAClientModel:
    """KMA (기상청) client for `MidFcstInfoService`.

    Wraps httpx clients supplied by `GoKrOpenDataModel`, which already carry
    the base URL and `service_key` query parameter, and exposes
    a `run_request_get_*` method per `MidFcstInfoService` endpoint (plus async
    `arun_*` variants) with idempotent retry. Connection settings and the
    close/context-manager surface belong to the owning `GoKrOpenDataModel`.

    Args:
        client: Sync httpx client bound to the 공공데이터포털 base URL.
        async_client: Async counterpart of `client`.

    The portal reports failure in the body of a `200 OK` via `resultCode`, and
    these methods do not inspect it. Any non-success answer — NODATA ('03', e.g.
    an unknown `reg_id`) and genuine errors alike ('99' when `tm_fc` is outside
    the 24h retention window, a bad `service_key`, ...) — returns normally with
    a header-only `response.body` of None. Callers that need to tell these apart
    must read `response.header.result_code` themselves.

    Attributes:
        mid_fcst_endpoint: 중기전망 path
            ('/1360000/MidFcstInfoService/getMidFcst').
        mid_land_fcst_endpoint: 중기육상예보 path
            ('/1360000/MidFcstInfoService/getMidLandFcst').
        mid_ta_endpoint: 중기기온 path
            ('/1360000/MidFcstInfoService/getMidTa').
        mid_sea_fcst_endpoint: 중기해상예보 path
            ('/1360000/MidFcstInfoService/getMidSeaFcst').

    Example:
        >>> from datetime import datetime
        >>> with GoKrOpenDataModel(service_key='...') as model:
        ...     model.kma_client.run_request_get_mid_land_fcst(
        ...         KMAGetMidLandFcstRequestParameterModel(
        ...             reg_id='11B00000',
        ...             tm_fc=datetime(2025, 12, 1, 6, 0),
        ...         )
        ...     )
    """

    mid_fcst_endpoint: ClassVar[str] = '/1360000/MidFcstInfoService/getMidFcst'
    mid_land_fcst_endpoint: ClassVar[str] = '/1360000/MidFcstInfoService/getMidLandFcst'
    mid_ta_endpoint: ClassVar[str] = '/1360000/MidFcstInfoService/getMidTa'
    mid_sea_fcst_endpoint: ClassVar[str] = '/1360000/MidFcstInfoService/getMidSeaFcst'

    def __init__(self, client: Client, async_client: AsyncClient):
        self._client = client
        self._async_client = async_client

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    def run_request_get_mid_fcst(
        self,
        parameter: KMAGetMidFcstRequestParameterModel
    ) -> KMAGetMidFcstResponseModel:
        """Fetch the mid-term outlook via `GET /1360000/MidFcstInfoService/getMidFcst`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Query parameters — `stn_id` (지점번호) and `tm_fc`
                (발표시각, 06:00/18:00, 최근 24시간 자료만 제공) plus optional
                `page_no`, `num_of_rows` and `data_type`.

        Returns:
            KMAGetMidFcstResponseModel: Parsed response whose body items carry
                the `wf_sv` 기상전망 text.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = self._client.get(
            url=self.mid_fcst_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidFcstResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_get_mid_fcst(
        self,
        parameter: KMAGetMidFcstRequestParameterModel
    ) -> KMAGetMidFcstResponseModel:
        """Async variant of `run_request_get_mid_fcst`.

        Same retry behaviour, `parameter`, and return type as
        `run_request_get_mid_fcst`; see it for details.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = await self._async_client.get(
            url=self.mid_fcst_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidFcstResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    def run_request_get_mid_land_fcst(
        self,
        parameter: KMAGetMidLandFcstRequestParameterModel
    ) -> KMAGetMidLandFcstResponseModel:
        """Fetch the mid-term land forecast via `GET /1360000/MidFcstInfoService/getMidLandFcst`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Query parameters — `reg_id` (예보구역코드) and `tm_fc`
                (발표시각, 06:00/18:00, 최근 24시간 자료만 제공) plus optional
                `page_no`, `num_of_rows` and `data_type`.

        Returns:
            KMAGetMidLandFcstResponseModel: Parsed response whose body items
                carry per-day 강수확률 (`rn_st*`) and 날씨예보 (`wf*`) for days
                3-10 after the announcement.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = self._client.get(
            url=self.mid_land_fcst_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidLandFcstResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_get_mid_land_fcst(
        self,
        parameter: KMAGetMidLandFcstRequestParameterModel
    ) -> KMAGetMidLandFcstResponseModel:
        """Async variant of `run_request_get_mid_land_fcst`.

        Same retry behaviour, `parameter`, and return type as
        `run_request_get_mid_land_fcst`; see it for details.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = await self._async_client.get(
            url=self.mid_land_fcst_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidLandFcstResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    def run_request_get_mid_ta(
        self,
        parameter: KMAGetMidTaRequestParameterModel
    ) -> KMAGetMidTaResponseModel:
        """Fetch the mid-term temperature forecast via `GET /1360000/MidFcstInfoService/getMidTa`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Query parameters — `reg_id` (예보구역코드) and `tm_fc`
                (발표시각, 06:00/18:00, 최근 24시간 자료만 제공) plus optional
                `page_no`, `num_of_rows` and `data_type`.

        Returns:
            KMAGetMidTaResponseModel: Parsed response whose body items carry
                per-day 예상최저/최고기온 (`ta_min*` / `ta_max*`) and their
                하한/상한 범위 for days 3-10 after the announcement.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = self._client.get(
            url=self.mid_ta_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidTaResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_get_mid_ta(
        self,
        parameter: KMAGetMidTaRequestParameterModel
    ) -> KMAGetMidTaResponseModel:
        """Async variant of `run_request_get_mid_ta`.

        Same retry behaviour, `parameter`, and return type as
        `run_request_get_mid_ta`; see it for details.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = await self._async_client.get(
            url=self.mid_ta_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidTaResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    def run_request_get_mid_sea_fcst(
        self,
        parameter: KMAGetMidSeaFcstRequestParameterModel
    ) -> KMAGetMidSeaFcstResponseModel:
        """Fetch the mid-term sea forecast via `GET /1360000/MidFcstInfoService/getMidSeaFcst`.

        Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
        httpx timeout/transport errors; any other error, and the final failed
        attempt, is raised.

        Args:
            parameter: Query parameters — `reg_id` (해상 예보구역코드) and
                `tm_fc` (발표시각, 06:00/18:00, 최근 24시간 자료만 제공) plus
                optional `page_no`, `num_of_rows` and `data_type`.

        Returns:
            KMAGetMidSeaFcstResponseModel: Parsed response whose body items
                carry per-day 날씨예보 (`wf*`) and 예상파고 (`wh*_a` 최저 /
                `wh*_b` 최고, in metres) for days 3-10 after the announcement.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = self._client.get(
            url=self.mid_sea_fcst_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidSeaFcstResponseModel.model_validate(response.json())

    @retry(
        retry=retry_if_exception(should_retry_idempotent),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=log_retry_before_sleep,
    )
    async def arun_request_get_mid_sea_fcst(
        self,
        parameter: KMAGetMidSeaFcstRequestParameterModel
    ) -> KMAGetMidSeaFcstResponseModel:
        """Async variant of `run_request_get_mid_sea_fcst`.

        Same retry behaviour, `parameter`, and return type as
        `run_request_get_mid_sea_fcst`; see it for details.

        See:
            https://www.data.go.kr/data/15059468/openapi.do
        """
        response = await self._async_client.get(
            url=self.mid_sea_fcst_endpoint,
            params=parameter.model_dump(by_alias=True, exclude_none=True)
        )
        response.raise_for_status()
        return KMAGetMidSeaFcstResponseModel.model_validate(response.json())
