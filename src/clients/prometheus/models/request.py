from datetime import datetime

from pydantic import (
    Field,
    field_serializer,
    field_validator
)

from clients.utility import (
    bearer_authorization,
    RequestModel
)


class PrometheusRequestHeaderModel(RequestModel):
    authorization: str | None = Field(default=None, alias='Authorization')
    user_agent: str = Field(alias='User-Agent')

    @field_validator('authorization')
    @classmethod
    def validate_authorization(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return bearer_authorization(v)


class PrometheusQueryV1RequestParameterModel(RequestModel):
    query: str
    time: datetime | None = None
    timeout: str | None = None

    @field_serializer('time')
    def serialize_time(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        return str(v.timestamp())


class PrometheusQueryRangeV1RequestParameterModel(RequestModel):
    query: str
    start_date: datetime = Field(alias='start')
    end_date: datetime = Field(alias='end')
    step: str
    timeout: str | None = None

    @field_serializer('start_date', 'end_date')
    def serialize_datetime(self, v: datetime) -> str:
        return str(v.timestamp())
