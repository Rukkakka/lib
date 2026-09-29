from datetime import datetime

from pydantic import (
    Field,
    AliasChoices,
    computed_field
)

from clients.utility import (
    RequestModel,
    ResponseModel
)

from typing import (
    Annotated,
    Literal,
    TypeVar,
    Generic
)

T = TypeVar('T', bound=ResponseModel)


class KMARequestParameterModel(RequestModel):
    page_no: Annotated[int, Field(ge=1)] = Field(default=1, alias='pageNo')
    num_of_rows: Annotated[int, Field(ge=1)] = Field(default=10, alias='numOfRows')
    data_type: Literal['JSON'] = Field(default='JSON', alias='dataType')
    forecast_date: Annotated[
        datetime,
        Field(
            exclude=True,
            description=(
                'Forecast announcement date. Combined with `forecast_time` '
                'to build the `tmFc` query parameter as YYYYMMDDHHMM. '
                'Time component is ignored; only the date portion is used.'
            )
        )
    ]
    forecast_time: Annotated[
        Literal['0600', '1800'],
        Field(
            exclude=True,
            description=(
                'Forecast announcement hour. KMA mid-term forecasts are '
                'issued twice daily; only "0600" (AM) and "1800" (PM) are '
                'accepted by the API.'
            )
        )
    ]

    @computed_field(alias='tmFc')
    @property
    def tm_fc(self) -> str:
        return f'{self.forecast_date:%Y%m%d}{self.forecast_time}'


class KMAResponseHeaderModel(ResponseModel):
    result_code: str = Field(alias='resultCode')
    result_msg: str = Field(alias='resultMsg')


class MidFcstItemModel(ResponseModel):
    wf_sv: str = Field(alias='wfSv')


class RegIdItemModel(ResponseModel):
    reg_id: str = Field(
        validation_alias=AliasChoices('regId', 'regid'),
        serialization_alias='regId'
    )


class MidLandFcstItemModel(RegIdItemModel):
    rn_st3_am: int | None = Field(default=None, alias='rnSt3Am')
    rn_st3_pm: int | None = Field(default=None, alias='rnSt3Pm')
    rn_st4_am: int | None = Field(default=None, alias='rnSt4Am')
    rn_st4_pm: int | None = Field(default=None, alias='rnSt4Pm')
    rn_st5_am: int | None = Field(default=None, alias='rnSt5Am')
    rn_st5_pm: int | None = Field(default=None, alias='rnSt5Pm')
    rn_st6_am: int | None = Field(default=None, alias='rnSt6Am')
    rn_st6_pm: int | None = Field(default=None, alias='rnSt6Pm')
    rn_st7_am: int | None = Field(default=None, alias='rnSt7Am')
    rn_st7_pm: int | None = Field(default=None, alias='rnSt7Pm')
    rn_st8: int | None = Field(default=None, alias='rnSt8')
    rn_st9: int | None = Field(default=None, alias='rnSt9')
    rn_st10: int | None = Field(default=None, alias='rnSt10')
    wf3_am: str | None = Field(default=None, alias='wf3Am')
    wf3_pm: str | None = Field(default=None, alias='wf3Pm')
    wf4_am: str | None = Field(default=None, alias='wf4Am')
    wf4_pm: str | None = Field(default=None, alias='wf4Pm')
    wf5_am: str | None = Field(default=None, alias='wf5Am')
    wf5_pm: str | None = Field(default=None, alias='wf5Pm')
    wf6_am: str | None = Field(default=None, alias='wf6Am')
    wf6_pm: str | None = Field(default=None, alias='wf6Pm')
    wf7_am: str | None = Field(default=None, alias='wf7Am')
    wf7_pm: str | None = Field(default=None, alias='wf7Pm')
    wf8: str | None = Field(default=None, alias='wf8')
    wf9: str | None = Field(default=None, alias='wf9')
    wf10: str | None = Field(default=None, alias='wf10')


class MidTaItemModel(RegIdItemModel):
    ta_min3: int | None = Field(default=None, alias='taMin3')
    ta_min3_low: int | None = Field(default=None, alias='taMin3Low')
    ta_min3_high: int | None = Field(default=None, alias='taMin3High')
    ta_max3: int | None = Field(default=None, alias='taMax3')
    ta_max3_low: int | None = Field(default=None, alias='taMax3Low')
    ta_max3_high: int | None = Field(default=None, alias='taMax3High')
    ta_min4: int | None = Field(default=None, alias='taMin4')
    ta_min4_low: int | None = Field(default=None, alias='taMin4Low')
    ta_min4_high: int | None = Field(default=None, alias='taMin4High')
    ta_max4: int | None = Field(default=None, alias='taMax4')
    ta_max4_low: int | None = Field(default=None, alias='taMax4Low')
    ta_max4_high: int | None = Field(default=None, alias='taMax4High')
    ta_min5: int | None = Field(default=None, alias='taMin5')
    ta_min5_low: int | None = Field(default=None, alias='taMin5Low')
    ta_min5_high: int | None = Field(default=None, alias='taMin5High')
    ta_max5: int | None = Field(default=None, alias='taMax5')
    ta_max5_low: int | None = Field(default=None, alias='taMax5Low')
    ta_max5_high: int | None = Field(default=None, alias='taMax5High')
    ta_min6: int | None = Field(default=None, alias='taMin6')
    ta_min6_low: int | None = Field(default=None, alias='taMin6Low')
    ta_min6_high: int | None = Field(default=None, alias='taMin6High')
    ta_max6: int | None = Field(default=None, alias='taMax6')
    ta_max6_low: int | None = Field(default=None, alias='taMax6Low')
    ta_max6_high: int | None = Field(default=None, alias='taMax6High')
    ta_min7: int | None = Field(default=None, alias='taMin7')
    ta_min7_low: int | None = Field(default=None, alias='taMin7Low')
    ta_min7_high: int | None = Field(default=None, alias='taMin7High')
    ta_max7: int | None = Field(default=None, alias='taMax7')
    ta_max7_low: int | None = Field(default=None, alias='taMax7Low')
    ta_max7_high: int | None = Field(default=None, alias='taMax7High')
    ta_min8: int | None = Field(default=None, alias='taMin8')
    ta_min8_low: int | None = Field(default=None, alias='taMin8Low')
    ta_min8_high: int | None = Field(default=None, alias='taMin8High')
    ta_max8: int | None = Field(default=None, alias='taMax8')
    ta_max8_low: int | None = Field(default=None, alias='taMax8Low')
    ta_max8_high: int | None = Field(default=None, alias='taMax8High')
    ta_min9: int | None = Field(default=None, alias='taMin9')
    ta_min9_low: int | None = Field(default=None, alias='taMin9Low')
    ta_min9_high: int | None = Field(default=None, alias='taMin9High')
    ta_max9: int | None = Field(default=None, alias='taMax9')
    ta_max9_low: int | None = Field(default=None, alias='taMax9Low')
    ta_max9_high: int | None = Field(default=None, alias='taMax9High')
    ta_min10: int | None = Field(default=None, alias='taMin10')
    ta_min10_low: int | None = Field(default=None, alias='taMin10Low')
    ta_min10_high: int | None = Field(default=None, alias='taMin10High')
    ta_max10: int | None = Field(default=None, alias='taMax10')
    ta_max10_low: int | None = Field(default=None, alias='taMax10Low')
    ta_max10_high: int | None = Field(default=None, alias='taMax10High')


class MidSeaFcstItemModel(RegIdItemModel):
    wf3_am: str | None = Field(default=None, alias='wf3Am')
    wf3_pm: str | None = Field(default=None, alias='wf3Pm')
    wf4_am: str | None = Field(default=None, alias='wf4Am')
    wf4_pm: str | None = Field(default=None, alias='wf4Pm')
    wf5_am: str | None = Field(default=None, alias='wf5Am')
    wf5_pm: str | None = Field(default=None, alias='wf5Pm')
    wf6_am: str | None = Field(default=None, alias='wf6Am')
    wf6_pm: str | None = Field(default=None, alias='wf6Pm')
    wf7_am: str | None = Field(default=None, alias='wf7Am')
    wf7_pm: str | None = Field(default=None, alias='wf7Pm')
    wf8: str | None = Field(default=None, alias='wf8')
    wf9: str | None = Field(default=None, alias='wf9')
    wf10: str | None = Field(default=None, alias='wf10')
    wh3_a_am: float | None = Field(default=None, alias='wh3AAm')
    wh3_a_pm: float | None = Field(default=None, alias='wh3APm')
    wh3_b_am: float | None = Field(default=None, alias='wh3BAm')
    wh3_b_pm: float | None = Field(default=None, alias='wh3BPm')
    wh4_a_am: float | None = Field(default=None, alias='wh4AAm')
    wh4_a_pm: float | None = Field(default=None, alias='wh4APm')
    wh4_b_am: float | None = Field(default=None, alias='wh4BAm')
    wh4_b_pm: float | None = Field(default=None, alias='wh4BPm')
    wh5_a_am: float | None = Field(default=None, alias='wh5AAm')
    wh5_a_pm: float | None = Field(default=None, alias='wh5APm')
    wh5_b_am: float | None = Field(default=None, alias='wh5BAm')
    wh5_b_pm: float | None = Field(default=None, alias='wh5BPm')
    wh6_a_am: float | None = Field(default=None, alias='wh6AAm')
    wh6_a_pm: float | None = Field(default=None, alias='wh6APm')
    wh6_b_am: float | None = Field(default=None, alias='wh6BAm')
    wh6_b_pm: float | None = Field(default=None, alias='wh6BPm')
    wh7_a_am: float | None = Field(default=None, alias='wh7AAm')
    wh7_a_pm: float | None = Field(default=None, alias='wh7APm')
    wh7_b_am: float | None = Field(default=None, alias='wh7BAm')
    wh7_b_pm: float | None = Field(default=None, alias='wh7BPm')
    wh8_a: float | None = Field(default=None, alias='wh8A')
    wh8_b: float | None = Field(default=None, alias='wh8B')
    wh9_a: float | None = Field(default=None, alias='wh9A')
    wh9_b: float | None = Field(default=None, alias='wh9B')
    wh10_a: float | None = Field(default=None, alias='wh10A')
    wh10_b: float | None = Field(default=None, alias='wh10B')


class ItemsModel(ResponseModel, Generic[T]):
    item: list[T] = Field(default_factory=list)


class BodyModel(ResponseModel, Generic[T]):
    data_type: str = Field(alias='dataType')
    items: ItemsModel[T]
    page_no: int = Field(alias='pageNo')
    num_of_rows: int = Field(alias='numOfRows')
    total_count: int = Field(alias='totalCount')


class ResponseWrapperModel(ResponseModel, Generic[T]):
    header: KMAResponseHeaderModel
    # Only success responses carry a body; NODATA and error responses are
    # header-only.
    body: BodyModel[T] | None = None


class KMAResponseModel(ResponseModel, Generic[T]):
    response: ResponseWrapperModel[T]
