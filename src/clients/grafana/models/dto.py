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
    Union,
    Dict,
    List
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


class TypeInfoModel(ResponseModel):
    frame: Annotated[str, Field()]
    nullable: Annotated[Optional[bool], Field(default=None)]


class FieldModel(ResponseModel):
    name: Annotated[str, Field()]
    type: Annotated[str, Field()]
    type_info: Annotated[TypeInfoModel, Field(alias='typeInfo')]


class SchemaModel(ResponseModel):
    fields: Annotated[List[FieldModel], Field()]


class DataModel(ResponseModel):
    values: Annotated[List[List[Optional[Union[int, float, str]]]], Field()]
    entities: Annotated[Optional[List[Optional[Dict[str, List[int]]]]], Field(default=None)]


class FrameModel(ResponseModel):
    frame_schema: Annotated[SchemaModel, Field(alias='shema')]
    data: Annotated[DataModel, Field()]


class RefIdModel(ResponseModel):
    status: Annotated[int, Field()]
    frames: Annotated[List[FrameModel], Field()]