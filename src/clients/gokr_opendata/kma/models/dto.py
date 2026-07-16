from datetime import datetime

from pydantic import (
    Field,
    AliasChoices,
    field_serializer
)

from clients.utility import (
    RequestModel,
    ResponseModel
)

from typing import (
    Annotated,
    Optional,
    Literal,
    List,
    TypeVar,
    Generic
)

T = TypeVar('T', bound=ResponseModel)


class KMARequestParameterModel(RequestModel):
    tm_fc: Annotated[datetime, Field(alias='tmFc')]
    page_no: Annotated[int, Field(alias='pageNo')] = 1
    num_of_rows: Annotated[int, Field(alias='numOfRows')] = 10
    data_type: Annotated[Literal['JSON'], Field(alias='dataType')] = 'JSON'

    @field_serializer('tm_fc')
    def serialize_tm_fc(self, v: datetime) -> str:
        return v.strftime('%Y%m%d%H%M')


class KMAResponseHeaderModel(ResponseModel):
    result_code: Annotated[str, Field(alias='resultCode')]
    result_msg: Annotated[str, Field(alias='resultMsg')]


class MidFcstItemModel(ResponseModel):
    wf_sv: Annotated[str, Field(alias='wfSv')]


class RegIdItemModel(ResponseModel):
    reg_id: Annotated[
        str,
        Field(validation_alias=AliasChoices('regId', 'regid'), serialization_alias='regId')
    ]


class MidLandFcstItemModel(RegIdItemModel):
    rn_st3_am: Annotated[Optional[int], Field(default=None, alias='rnSt3Am')]
    rn_st3_pm: Annotated[Optional[int], Field(default=None, alias='rnSt3Pm')]
    rn_st4_am: Annotated[Optional[int], Field(default=None, alias='rnSt4Am')]
    rn_st4_pm: Annotated[Optional[int], Field(default=None, alias='rnSt4Pm')]
    rn_st5_am: Annotated[int, Field(alias='rnSt5Am')]
    rn_st5_pm: Annotated[int, Field(alias='rnSt5Pm')]
    rn_st6_am: Annotated[int, Field(alias='rnSt6Am')]
    rn_st6_pm: Annotated[int, Field(alias='rnSt6Pm')]
    rn_st7_am: Annotated[int, Field(alias='rnSt7Am')]
    rn_st7_pm: Annotated[int, Field(alias='rnSt7Pm')]
    rn_st8: Annotated[int, Field(alias='rnSt8')]
    rn_st9: Annotated[int, Field(alias='rnSt9')]
    rn_st10: Annotated[int, Field(alias='rnSt10')]
    wf3_am: Annotated[Optional[str], Field(default=None, alias='wf3Am')]
    wf3_pm: Annotated[Optional[str], Field(default=None, alias='wf3Pm')]
    wf4_am: Annotated[Optional[str], Field(default=None, alias='wf4Am')]
    wf4_pm: Annotated[Optional[str], Field(default=None, alias='wf4Pm')]
    wf5_am: Annotated[str, Field(alias='wf5Am')]
    wf5_pm: Annotated[str, Field(alias='wf5Pm')]
    wf6_am: Annotated[str, Field(alias='wf6Am')]
    wf6_pm: Annotated[str, Field(alias='wf6Pm')]
    wf7_am: Annotated[str, Field(alias='wf7Am')]
    wf7_pm: Annotated[str, Field(alias='wf7Pm')]
    wf8: Annotated[str, Field(alias='wf8')]
    wf9: Annotated[str, Field(alias='wf9')]
    wf10: Annotated[str, Field(alias='wf10')]


class MidTaItemModel(RegIdItemModel):
    ta_min3: Annotated[Optional[int], Field(default=None, alias='taMin3')]
    ta_min3_low: Annotated[Optional[int], Field(default=None, alias='taMin3Low')]
    ta_min3_high: Annotated[Optional[int], Field(default=None, alias='taMin3High')]
    ta_max3: Annotated[Optional[int], Field(default=None, alias='taMax3')]
    ta_max3_low: Annotated[Optional[int], Field(default=None, alias='taMax3Low')]
    ta_max3_high: Annotated[Optional[int], Field(default=None, alias='taMax3High')]
    ta_min4: Annotated[Optional[int], Field(default=None, alias='taMin4')]
    ta_min4_low: Annotated[Optional[int], Field(default=None, alias='taMin4Low')]
    ta_min4_high: Annotated[Optional[int], Field(default=None, alias='taMin4High')]
    ta_max4: Annotated[Optional[int], Field(default=None, alias='taMax4')]
    ta_max4_low: Annotated[Optional[int], Field(default=None, alias='taMax4Low')]
    ta_max4_high: Annotated[Optional[int], Field(default=None, alias='taMax4High')]
    ta_min5: Annotated[int, Field(alias='taMin5')]
    ta_min5_low: Annotated[Optional[int], Field(default=None, alias='taMin5Low')]
    ta_min5_high: Annotated[Optional[int], Field(default=None, alias='taMin5High')]
    ta_max5: Annotated[int, Field(alias='taMax5')]
    ta_max5_low: Annotated[Optional[int], Field(default=None, alias='taMax5Low')]
    ta_max5_high: Annotated[Optional[int], Field(default=None, alias='taMax5High')]
    ta_min6: Annotated[int, Field(alias='taMin6')]
    ta_min6_low: Annotated[Optional[int], Field(default=None, alias='taMin6Low')]
    ta_min6_high: Annotated[Optional[int], Field(default=None, alias='taMin6High')]
    ta_max6: Annotated[int, Field(alias='taMax6')]
    ta_max6_low: Annotated[Optional[int], Field(default=None, alias='taMax6Low')]
    ta_max6_high: Annotated[Optional[int], Field(default=None, alias='taMax6High')]
    ta_min7: Annotated[int, Field(alias='taMin7')]
    ta_min7_low: Annotated[Optional[int], Field(default=None, alias='taMin7Low')]
    ta_min7_high: Annotated[Optional[int], Field(default=None, alias='taMin7High')]
    ta_max7: Annotated[Optional[int], Field(default=None, alias='taMax7')]
    ta_max7_low: Annotated[Optional[int], Field(default=None, alias='taMax7Low')]
    ta_max7_high: Annotated[Optional[int], Field(default=None, alias='taMax7High')]
    ta_min8: Annotated[int, Field(alias='taMin8')]
    ta_min8_low: Annotated[Optional[int], Field(default=None, alias='taMin8Low')]
    ta_min8_high: Annotated[Optional[int], Field(default=None, alias='taMin8High')]
    ta_max8: Annotated[int, Field(alias='taMax8')]
    ta_max8_low: Annotated[Optional[int], Field(default=None, alias='taMax8Low')]
    ta_max8_high: Annotated[Optional[int], Field(default=None, alias='taMax8High')]
    ta_min9: Annotated[int, Field(alias='taMin9')]
    ta_min9_low: Annotated[Optional[int], Field(default=None, alias='taMin9Low')]
    ta_min9_high: Annotated[Optional[int], Field(default=None, alias='taMin9High')]
    ta_max9: Annotated[int, Field(alias='taMax9')]
    ta_max9_low: Annotated[Optional[int], Field(default=None, alias='taMax9Low')]
    ta_max9_high: Annotated[Optional[int], Field(default=None, alias='taMax9High')]
    ta_min10: Annotated[int, Field(alias='taMin10')]
    ta_min10_low: Annotated[Optional[int], Field(default=None, alias='taMin10Low')]
    ta_min10_high: Annotated[Optional[int], Field(default=None, alias='taMin10High')]
    ta_max10: Annotated[int, Field(alias='taMax10')]
    ta_max10_low: Annotated[Optional[int], Field(default=None, alias='taMax10Low')]
    ta_max10_high: Annotated[Optional[int], Field(default=None, alias='taMax10High')]


class MidSeaFcstItemModel(RegIdItemModel):
    wf3_am: Annotated[Optional[str], Field(default=None, alias='wf3Am')]
    wf3_pm: Annotated[Optional[str], Field(default=None, alias='wf3Pm')]
    wf4_am: Annotated[Optional[str], Field(default=None, alias='wf4Am')]
    wf4_pm: Annotated[Optional[str], Field(default=None, alias='wf4Pm')]
    wf5_am: Annotated[str, Field(alias='wf5Am')]
    wf5_pm: Annotated[str, Field(alias='wf5Pm')]
    wf6_am: Annotated[str, Field(alias='wf6Am')]
    wf6_pm: Annotated[Optional[str], Field(default=None, alias='wf6Pm')]
    wf7_am: Annotated[Optional[str], Field(default=None, alias='wf7Am')]
    wf7_pm: Annotated[Optional[str], Field(default=None, alias='wf7Pm')]
    wf8: Annotated[Optional[str], Field(default=None, alias='wf8')]
    wf9: Annotated[Optional[str], Field(default=None, alias='wf9')]
    wf10: Annotated[Optional[str], Field(default=None, alias='wf10')]
    wh3_a_am: Annotated[Optional[float], Field(default=None, alias='wh3AAm')]
    wh3_a_pm: Annotated[Optional[float], Field(default=None, alias='wh3APm')]
    wh3_b_am: Annotated[Optional[float], Field(default=None, alias='wh3BAm')]
    wh3_b_pm: Annotated[Optional[float], Field(default=None, alias='wh3BPm')]
    wh4_a_am: Annotated[Optional[float], Field(default=None, alias='wh4AAm')]
    wh4_a_pm: Annotated[Optional[float], Field(default=None, alias='wh4APm')]
    wh4_b_am: Annotated[Optional[float], Field(default=None, alias='wh4BAm')]
    wh4_b_pm: Annotated[Optional[float], Field(default=None, alias='wh4BPm')]
    wh5_a_am: Annotated[float, Field(alias='wh5AAm')]
    wh5_a_pm: Annotated[float, Field(alias='wh5APm')]
    wh5_b_am: Annotated[float, Field(alias='wh5BAm')]
    wh5_b_pm: Annotated[float, Field(alias='wh5BPm')]
    wh6_a_am: Annotated[float, Field(alias='wh6AAm')]
    wh6_a_pm: Annotated[float, Field(alias='wh6APm')]
    wh6_b_am: Annotated[float, Field(alias='wh6BAm')]
    wh6_b_pm: Annotated[float, Field(alias='wh6BPm')]
    wh7_a_am: Annotated[float, Field(alias='wh7AAm')]
    wh7_a_pm: Annotated[float, Field(alias='wh7APm')]
    wh7_b_am: Annotated[float, Field(alias='wh7BAm')]
    wh7_b_pm: Annotated[float, Field(alias='wh7BPm')]
    wh8_a: Annotated[float, Field(alias='wh8A')]
    wh8_b: Annotated[float, Field(alias='wh8B')]
    wh9_a: Annotated[float, Field(alias='wh9A')]
    wh9_b: Annotated[float, Field(alias='wh9B')]
    wh10_a: Annotated[float, Field(alias='wh10A')]
    wh10_b: Annotated[float, Field(alias='wh10B')]


class ItemsModel(ResponseModel, Generic[T]):
    item: Annotated[List[T], Field(default_factory=list)]


class BodyModel(ResponseModel, Generic[T]):
    data_type: Annotated[str, Field(alias='dataType')]
    items: Annotated[ItemsModel[T], Field()]
    page_no: Annotated[int, Field(alias='pageNo')]
    num_of_rows: Annotated[int, Field(alias='numOfRows')]
    total_count: Annotated[int, Field(alias='totalCount')]


class ResponseWrapperModel(ResponseModel, Generic[T]):
    header: Annotated[KMAResponseHeaderModel, Field()]
    # Only success responses carry a body; NODATA and error responses are
    # header-only.
    body: Annotated[Optional[BodyModel[T]], Field(default=None)]


class KMAResponseModel(ResponseModel, Generic[T]):
    response: Annotated[ResponseWrapperModel[T], Field()]
