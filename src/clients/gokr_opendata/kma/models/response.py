from clients.gokr_opendata.kma.models.dto import (
    KMAResponseModel,
    MidFcstItemModel,
    MidLandFcstItemModel,
    MidTaItemModel,
    MidSeaFcstItemModel
)


class KMAGetMidFcstResponseModel(KMAResponseModel[MidFcstItemModel]):
    pass


class KMAGetMidLandFcstResponseModel(KMAResponseModel[MidLandFcstItemModel]):
    pass


class KMAGetMidTaResponseModel(KMAResponseModel[MidTaItemModel]):
    pass


class KMAGetMidSeaFcstResponseModel(KMAResponseModel[MidSeaFcstItemModel]):
    pass
