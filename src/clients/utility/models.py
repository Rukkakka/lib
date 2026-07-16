from pydantic import (
    BaseModel,
    ConfigDict
)


class RequestModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra='forbid',
    )


class ResponseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra='allow',
    )