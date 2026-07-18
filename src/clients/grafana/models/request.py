from datetime import datetime

from pydantic import (
    Field,
    field_serializer,
    field_validator
)

from clients.utility import RequestModel

from typing import (
    Annotated,
    Dict,
    List,
    Any
)


class GrafanaRequestHeaderModel(RequestModel):
    authorization: Annotated[str, Field(alias='Authorization')]
    user_agent: Annotated[str, Field(alias='User-Agent')]

    @field_validator('authorization')
    @classmethod
    def validate_authorization(cls, v: str) -> str:
        v = v.strip()
        if v.startswith('Bearer '):
            return v
        return f'Bearer {v}'


class GrafanaDsQueryRequestParameterModel(RequestModel):
    ds_type: Annotated[str, Field()]


class GrafanaDsQueryRequestPayloadModel(RequestModel):
    queries: Annotated[List[Dict[str, Any]], Field()]
    from_date: Annotated[datetime, Field(alias='from')]
    to_date: Annotated[datetime, Field(alias='to')]

    @field_serializer('from_date', 'to_date')
    def serialize_datetime(self, v: datetime) -> str:
        return str(int(v.timestamp()) * 1000)
