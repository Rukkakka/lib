from datetime import datetime

from pydantic import (
    Field,
    field_serializer
)

from clients.utility import RequestModel

from typing import (
    Annotated,
    Dict,
    List,
    Any
)


class GrafanaDsQueryRequestParameterModel(RequestModel):
    ds_type: Annotated[str, Field()]


class GrafanaDsQueryRequestPayloadModel(RequestModel):
    queries: Annotated[List[Dict[str, Any]], Field()]
    from_date: Annotated[datetime, Field(alias='from')]
    to_date: Annotated[datetime, Field(alias='to')]

    @field_serializer('from_date', 'to_date')
    def serialize_datetime(self, v: datetime) -> str:
        return str(int(v.timestamp()) * 1000)
