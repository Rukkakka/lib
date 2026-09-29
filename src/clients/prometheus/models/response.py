from clients.utility import ResponseModel
from clients.prometheus.models.dto import (
    DataModel,
    QueryResultModel,
    QueryRangeResultModel
)


class PrometheusQueryV1ResponseModel(ResponseModel):
    status: str
    data: DataModel[QueryResultModel]


class PrometheusQueryRangeV1ResponseModel(ResponseModel):
    status: str
    data: DataModel[QueryRangeResultModel]
