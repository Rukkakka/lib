from clients.gokr_opendata.base import BaseGoKrOpenDataClientModel

from clients.gokr_opendata.kma import KMAClientModel


class GoKrOpenDataModel(BaseGoKrOpenDataClientModel):
    """공공데이터포털 (data.go.kr) client.

    Owns the httpx clients that carry the base URL and `service_key`, and
    exposes one per-service client (`kma_client`, ...) sharing them. Inherits
    `host`, `service_key`, `url_schema`, `verify`, `proxy`, `timeout`, and the
    close/context-manager surface from `BaseGoKrOpenDataClientModel`.

    Each httpx client is built only when a request first needs it. Use `with`
    when calling only the sync `run_request_*` methods, and `async with` as
    soon as any async `arun_request_*` method is used: `aclose()` closes both
    clients, while `close()` cannot close the async one.

    Args:
        service_key: 공공데이터포털 인증키, in its decoded form — httpx
            percent-encodes it, so an already-encoded key is double-encoded
            and rejected.

    Attributes:
        kma_client: KMA (기상청) client over the shared httpx clients.
            Returns a new instance on every access.

    Example:
        >>> with GoKrOpenDataModel(service_key='...') as model:
        ...     model.kma_client.run_request_get_mid_fcst(parameter)
    """

    @property
    def kma_client(self) -> KMAClientModel:
        return KMAClientModel(owner=self)