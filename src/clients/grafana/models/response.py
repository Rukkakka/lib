from clients.utility import ResponseModel
from clients.grafana.models.dto import RefIdModel


class GrafanaDsQueryResponseModel(ResponseModel):
    results: dict[str, RefIdModel]