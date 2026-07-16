from pydantic import Field

from clients.utility import ResponseModel

from clients.prometheus.models.dto import (
    DataModel,
    QueryResultModel,
    QueryRangeResultModel
)

from typing import Annotated


class PrometheusQueryV1ResponseModel(ResponseModel):
    status: Annotated[str, Field()]
    data: Annotated[DataModel[QueryResultModel], Field()]


class PrometheusQueryRangeV1ResponseModel(ResponseModel):
    status: Annotated[str, Field()]
    data: Annotated[DataModel[QueryRangeResultModel], Field()]
