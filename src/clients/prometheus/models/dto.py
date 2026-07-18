from pydantic import Field

from clients.utility import ResponseModel

from typing import (
    Annotated,
    Dict,
    List,
    Union,
    TypeVar,
    Generic
)

T = TypeVar('T', bound=ResponseModel)


class ResultModel(ResponseModel):
    metric: Annotated[Dict[str, str], Field()]


class QueryResultModel(ResultModel):
    value: Annotated[List[Union[float, str]], Field()]


class QueryRangeResultModel(ResultModel):
    values: Annotated[List[List[Union[float, str]]], Field()]


class DataModel(ResponseModel, Generic[T]):
    result_type: Annotated[str, Field(alias='resultType')]
    result: Annotated[List[T], Field()]
