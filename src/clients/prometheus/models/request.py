from datetime import datetime

from pydantic import (
    Field,
    field_serializer,
    field_validator
)

from clients.utility import RequestModel

from typing import (
    Annotated,
    Optional
)


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


class PrometheusQueryV1RequestParameterModel(RequestModel):
    query: Annotated[str, Field()]
    time: Annotated[Optional[datetime], Field()] = None
    timeout: Annotated[Optional[str], Field()] = None

    @field_serializer('time')
    def serialize_time(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return str(v.timestamp())


class PrometheusQueryRangeV1RequestParameterModel(RequestModel):
    query: Annotated[str, Field()]
    start_date: Annotated[datetime, Field(alias='start')]
    end_date: Annotated[datetime, Field(alias='end')]
    step: Annotated[str, Field()]
    timeout: Annotated[Optional[str], Field()] = None

    @field_serializer('start_date', 'end_date')
    def serialize_datetime(self, v: datetime) -> str:
        return str(v.timestamp())
