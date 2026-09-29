from pydantic import Field

from clients.utility import ResponseModel

from typing import (
    TypeVar,
    Generic
)

T = TypeVar('T', bound=ResponseModel)


class ResultModel(ResponseModel):
    metric: dict[str, str]


class QueryResultModel(ResultModel):
    value: list[float | str]


class QueryRangeResultModel(ResultModel):
    values: list[list[float | str]]


class DataModel(ResponseModel, Generic[T]):
    result_type: str = Field(alias='resultType')
    result: list[T]
