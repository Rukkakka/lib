from pydantic import Field

from clients.utility import ResponseModel


class TypeInfoModel(ResponseModel):
    frame: str
    nullable: bool | None = None


class FieldModel(ResponseModel):
    name: str
    type: str
    type_info: TypeInfoModel = Field(alias='typeInfo')


class SchemaModel(ResponseModel):
    fields: list[FieldModel]


class DataModel(ResponseModel):
    values: list[list[int | float | str | None]]
    entities: list[dict[str, list[int]] | None] | None = None


class FrameModel(ResponseModel):
    frame_schema: SchemaModel = Field(alias='schema')
    data: DataModel


class RefIdModel(ResponseModel):
    status: int
    frames: list[FrameModel]