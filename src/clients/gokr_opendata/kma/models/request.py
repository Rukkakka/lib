from functools import partial

from pydantic import (
    BeforeValidator,
    Field
)

from clients.gokr_opendata.kma.constants import (
    MidFcstStnId,
    MidFcstStnName,
    MidLandFcstRegId,
    MidLandFcstRegName,
    MidTaRegId,
    MidTaRegName,
    MidSeaFcstRegId,
    MidSeaFcstRegName,
    MID_FCST_STN_ID_BY_NAME,
    MID_LAND_FCST_REG_ID_BY_NAME,
    MID_TA_REG_ID_BY_NAME,
    MID_SEA_FCST_REG_ID_BY_NAME
)
from clients.gokr_opendata.kma.models.dto import KMARequestParameterModel

from typing import (
    Annotated,
    Any,
    Mapping,
    Union
)


def to_code(codes_by_name: Mapping[str, str], v: Any) -> Any:
    """Resolve a 한글 구역명 to its code, passing anything else through.

    A value that is already a code — or is neither a name nor a code — is
    returned untouched, leaving the field's Literal to accept or reject it.
    """
    return codes_by_name.get(v, v) if isinstance(v, str) else v


class KMAGetMidFcstRequestParameterModel(KMARequestParameterModel):
    stn_id: Annotated[
        Union[MidFcstStnId, MidFcstStnName],
        BeforeValidator(partial(to_code, MID_FCST_STN_ID_BY_NAME)),
        Field(alias='stnId')
    ]


class KMAGetMidLandFcstRequestParameterModel(KMARequestParameterModel):
    reg_id: Annotated[
        Union[MidLandFcstRegId, MidLandFcstRegName],
        BeforeValidator(partial(to_code, MID_LAND_FCST_REG_ID_BY_NAME)),
        Field(alias='regId')
    ]


class KMAGetMidTaRequestParameterModel(KMARequestParameterModel):
    reg_id: Annotated[
        Union[MidTaRegId, MidTaRegName],
        BeforeValidator(partial(to_code, MID_TA_REG_ID_BY_NAME)),
        Field(alias='regId')
    ]


class KMAGetMidSeaFcstRequestParameterModel(KMARequestParameterModel):
    reg_id: Annotated[
        Union[MidSeaFcstRegId, MidSeaFcstRegName],
        BeforeValidator(partial(to_code, MID_SEA_FCST_REG_ID_BY_NAME)),
        Field(alias='regId')
    ]
