from clients.gokr_opendata.base import BaseGoKrOpenDataClientModel

from clients.gokr_opendata.kma import KMAClientModel


class GoKrOpenDataModel(BaseGoKrOpenDataClientModel):
    """공공데이터포털 (data.go.kr) client.

    Owns the httpx clients that carry the base URL and `service_key`, and
    exposes one lazily created per-service client (`kma_client`, ...) sharing
    them. Inherits `host`, `service_key`, `url_schema`, `verify`, `proxy`,
    `timeout`, and the close/context-manager surface from
    `BaseGoKrOpenDataClientModel`.

    Args:
        service_key: 공공데이터포털 인증키, in its decoded form — httpx
            percent-encodes it, so an already-encoded key is double-encoded
            and rejected.

    Attributes:
        kma_client: Cached KMA (기상청) client, created on first access.

    Example:
        >>> with GoKrOpenDataModel(service_key='...') as model:
        ...     model.kma_client.run_request_get_mid_fcst(parameter)
    """

    @property
    def kma_client(self) -> KMAClientModel:
        return KMAClientModel(
            client=self._client,
            async_client=self._async_client
        )