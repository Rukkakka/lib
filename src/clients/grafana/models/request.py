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

from typing import Any


class GrafanaRequestHeaderModel(RequestModel):
    authorization: str = Field(alias='Authorization')
    user_agent: str = Field(alias='User-Agent')

    @field_validator('authorization')
    @classmethod
    def validate_authorization(cls, v: str) -> str:
        return bearer_authorization(v)


class GrafanaDsQueryRequestParameterModel(RequestModel):
    ds_type: str


class GrafanaDsQueryRequestPayloadModel(RequestModel):
    queries: list[dict[str, Any]]
    from_date: datetime = Field(alias='from')
    to_date: datetime = Field(alias='to')

    @field_serializer('from_date', 'to_date')
    def serialize_datetime(self, v: datetime) -> str:
        return str(int(v.timestamp() * 1000))
