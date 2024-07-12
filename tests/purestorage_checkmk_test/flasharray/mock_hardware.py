import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_controllers import ControllersContainer
from purestorage_checkmk_test.flasharray.mock_drives import DrivesContainer
from purestorage_checkmk_test.flasharray.mock_port_details import PortContainer
from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _HardwareRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: [List[str]] = None
    total_item_count: bool = False


@dataclasses.dataclass
class Hardware:
    status: str
    index: Optional[int] = None
    name: Optional[str] = None
    details: Optional[str] = None
    model: Optional[str] = None
    slot: Optional[str] = None
    speed: Optional[int] = None
    temperature: Optional[int] = None
    type: Optional[str] = None
    voltage: Optional[int] = None
    serial: Optional[str] = None


@dataclasses.dataclass
class _HardwaresResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Hardware]] = None


class HardwaresContainer:
    _drives: DrivesContainer
    _controllers: ControllersContainer
    _ports: PortContainer
    hardware_items: List[Hardware]
    _next_hardware: int

    def __init__(self, drives: DrivesContainer, controllers: ControllersContainer, ports: PortContainer):
        self._next_hardware = 0
        self._drives = drives
        self._controllers = controllers
        self._ports = ports
        self.hardware_items = []
        self.hardware_items.append(Hardware(
            index=0,
            name="CH0",
            type="chassis",
            model="M_SERIES",
            status="ok",
            serial="asdf",
        ))
        for i in range(1, 5):
            self.hardware_items.append(
                Hardware(
                    index=i,
                    status="ok",
                    name=f"CT0.FAN{i}",
                    type="cooling",
                )
            )
        for i in range(0, 2):
            self.hardware_items.append(
                Hardware(
                    index=i,
                    type="power_supply",
                    name=f"CH0.PWR{i}",
                    status="ok",
                    model="DPS-1600AB-13 U",
                    serial="asdf",
                    voltage=236
                )
            )
        for i in range(5, 7):
            self.hardware_items.append(
                Hardware(
                    index=i,
                    status="ok",
                    name=f"CT1.DCA{i}",
                    slot=f"{i}",
                    type="direct_compress_accelerator",
                    serial="asdf",
                    model="asdf"
                )
            )

    def basic_items_by_type(self, type: str) -> List[Hardware]:
        return list(filter(lambda hw: hw.type == type, self.hardware_items))

    @property
    def hardwares(self) -> List[Hardware]:
        hardwares = []

        drive_to_drive_bay_status_map = {
            "empty": "healthy",
            "failed": "critical",
            "healthy": "ok",
            "identifying": "identifying",
            "missing": "critical",
            "recovering": "unhealthy",
            "unadmitted": "identifying",
            "unhealthy": "unhealthy",
            "unrecognized": "unknown",
            "updating": "healthy"
        }

        i = 0
        for drive in self._drives.drives:
            drive_bay = Hardware(
                index=i,
                status="not_installed",
                name=f"CH0.BAY{i}",
                type="drive_bay",
                serial=None,
                model=None
            )
            try:
                drive_bay.status = drive_to_drive_bay_status_map[drive.status]
                drive_bay.serial = "asdf"
            except KeyError:
                pass

            hardwares.append(
                drive_bay
            )
            i += 1
        i = 0
        for ct in self._controllers.controllers:
            controller_status_map = {
                "not ready": "unhealthy",
                "ready": "healthy",
                "unknown": "unknown",
                "updating": "healthy"
            }
            controller = Hardware(
                index=i,
                status=controller_status_map[ct.status],
                name=f"CT{i}",
                type="controller",
                serial="asdf",
                model=ct.model
            )
            hardwares.append(controller)
            i += 1
        i = 0
        for port in self._ports.ports:
            if port.interface_type == "eth":
                hardwares.append(
                    Hardware(
                        index=i,
                        status=port.get_status(),
                        name=port.name,
                        type="eth_port",
                        details="eth details, speed, mac, etc."
                    )
                )
                i+=1

        for hw in self.hardware_items:
            hardwares.append(hw)

        return hardwares


class _HardwaresRoute(_AuthenticatedJSONRoute):
    _container: HardwaresContainer
    path = re.compile('^/api/2.21/hardware$')

    def __init__(self, hardwares_container: HardwaresContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = hardwares_container
        self._continuation_token_container = _ContinuationTokenContainer[Hardware]()

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
                "The filter parameter is not supported by the mock".encode('ascii')
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
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.hardwares, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_HardwaresResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.hardwares),
                items=items
            )
        )
