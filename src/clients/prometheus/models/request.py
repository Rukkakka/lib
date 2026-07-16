from datetime import datetime

from pydantic import (
    Field,
    field_serializer
)

from clients.utility import RequestModel

from typing import (
    Annotated,
    Optional
)


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
