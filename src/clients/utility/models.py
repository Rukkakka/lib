from pydantic import (
    BaseModel,
    ConfigDict,
)


class RequestModel(BaseModel):
    """Base request model with strict field validation."""
    model_config = ConfigDict(
        populate_by_name=True,
        extra='forbid',
    )


class ResponseModel(BaseModel):
    """Base response model allowing additional fields from APIs."""
    model_config = ConfigDict(
        populate_by_name=True,
        extra='allow',
    )
