from pydantic import Field

from clients.utility import ResponseModel

from typing import (
    Annotated,
    Optional,
    Union,
    Dict,
    List
)


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