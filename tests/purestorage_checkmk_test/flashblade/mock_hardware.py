import dataclasses
import re
import typing
import uuid

from purestorage_checkmk_test.flashblade.mock_blades import BladesContainer
from purestorage_checkmk_test.flashblade.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class HardwareItem:
    name: str
    status: str
    type: str
    id: typing.Optional[str] = None
    part_number: typing.Optional[str] = None
    temperature: typing.Optional[int] = None
    serial: typing.Optional[str] = None
    slot: typing.Optional[int] = None
    speed: typing.Optional[int] = None
    details: typing.Optional[str] = None
    identify_enabled: bool = False
    index: typing.Optional[int] = None
    model: typing.Optional[str] = None


@dataclasses.dataclass
class _HardwareRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None
    ids: typing.Optional[typing.List[str]] = None
    names: typing.Optional[typing.List[str]] = None


@dataclasses.dataclass
class _HardwareResponse:
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[typing.List[HardwareItem]] = None


class HardwareContainer:
    base_hardware_items: typing.List[HardwareItem]

    def __init__(self, blades: BladesContainer):
        self._blades = blades
        self.base_hardware_items = []
        self.base_hardware_items.append(
            HardwareItem(
                index=1,
                model="CH-FB",
                name="CH1",
                serial="asdfasdf",
                status="healthy",
                type="ch",
                id=str(uuid.uuid4()),
            ),
        )
        self.base_hardware_items.append(
            HardwareItem(
                index=1,
                model="EFM-310",
                name="CH1.FM1",
                serial="asdfasdf",
                slot=1,
                status="healthy",
                type="fm",
                id=str(uuid.uuid4())
            )
        )
        self.base_hardware_items.append(
            HardwareItem(
                index=2,
                model="EFM-310",
                name="CH1.FM2",
                serial="asdfasdf",
                slot=1,
                status="healthy",
                type="fm",
                id=str(uuid.uuid4()),
            )
        )
        for i in range(1, 7):
            self.base_hardware_items.append(
                HardwareItem(
                    index=i,
                    name=f"CH1.FM1.FAN{i}",
                    slot=i,
                    status="healthy",
                    type="fan",
                    id=str(uuid.uuid4()),
                )
            )
        for i in range(1, 5):
            self.base_hardware_items.append(
                HardwareItem(
                    index=i,
                    name=f"CH1.PWR{i}",
                    slot=i,
                    model="DS1600SPE-3",
                    status="healthy",
                    serial="asdfasdf",
                    type="pwr",
                    id=str(uuid.uuid4()),
                )
            )
        k = 0
        for i in range(1, 5):
            for j in range(1, 5):
                k += 1
                self.base_hardware_items.append(
                    HardwareItem(
                        index=k,
                        model="QSFP-SR4-40G",
                        name=f"CH1.FM1.ETH{i}.{j}",
                        serial="asdf" if i == 1 and j == 1 else None,
                        slot=i,
                        status="healthy" if i == 1 and j == 1 else "unused",
                        type="eth",
                    )
                )

    @property
    def hardware_items(self) -> typing.List[HardwareItem]:
        result = []
        for item in self.base_hardware_items:
            result.append(item)
        for i, blade in enumerate(self._blades.blades):
            item = HardwareItem(
                id=blade.id,
                status=blade.status,
                type="fb",
                slot=i,
                name=blade.name,
            )
            if blade.status != "unused":
                item.serial = "asdfasdf"
                item.model = "FB-17TB"

            result.append(
                item
            )
        return result

    def basic_items_by_type(self, type: str) -> typing.List[HardwareItem]:
        return list(filter(lambda hw: hw.type == type, self.hardware_items))


class _HardwareRoute(_AuthenticatedJSONRoute):
    _container: HardwareContainer
    path = re.compile("^/api/2.9/hardware$")

    def __init__(self, hardware: HardwareContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = hardware
        self._continuation_token_container = _ContinuationTokenContainer[HardwareItem]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _HardwareRequest()
        req.query_to_dataclass(query)

        if query.sort is not None:
            return Response(
                400,
                {},
                "The sort parameter is not supported by the mock.".encode('ascii')
            )
        if query.filter is not None:
            return Response(
                400,
                {},
                "The filter parameter is not supported by the mock.".encode('ascii')
            )
        if query.ids is not None:
            return Response(
                400,
                {},
                "The ids parameter is not supported by the mock.".encode('ascii')
            )
        if query.names is not None:
            return Response(
                400,
                {},
                "The names parameter is not supported by the mock.".encode('ascii')
            )

        if query.continuation_token:
            items, remaining_items, total = self._continuation_token_container.get(
                query.continuation_token,
                query.limit,
                query.offset
            )
            if len(remaining_items) > 0:
                continuation_token = query.continuation_token
            else:
                continuation_token = None
        else:
            # noinspection PyProtectedMember
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.hardware_items, None, query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_HardwareResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.hardware_items),
                items=items,
            )
        )
