from pydantic import (
    Field,
    field_validator
)

from clients.utility import (
    RequestModel,
    ResponseModel
)

from typing import (
    Annotated,
    Optional,
    Dict,
    List,
    Union,
    TypeVar,
    Generic
)

T = TypeVar('T', bound=ResponseModel)


class PrometheusRequestHeaderModel(RequestModel):
    authorization: Annotated[Optional[str], Field(alias='Authorization')] = None
    user_agent: Annotated[str, Field(alias='User-Agent')]

    @field_validator('authorization')
    @classmethod
    def validate_authorization(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if v.startswith('Bearer '):
            return v
        return f'Bearer {v}'


class ResultModel(ResponseModel):
    metric: Annotated[Dict[str, str], Field()]


class QueryResultModel(ResultModel):
    value: Annotated[List[Union[float, str]], Field()]


class QueryRangeResultModel(ResultModel):
    values: Annotated[List[List[Union[float, str]]], Field()]


class DataModel(ResponseModel, Generic[T]):
    result_type: Annotated[str, Field(alias='resultType')]
    result: Annotated[List[T], Field()]
