from pydantic import Field

from clients.utility import ResponseModel
from clients.grafana.models.dto import RefIdModel

from typing import (
    Annotated,
    Dict
)


class GrafanaDsQueryResponseModel(ResponseModel):
    results: Annotated[Dict[str, RefIdModel], Field()]