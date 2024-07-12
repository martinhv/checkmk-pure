import dataclasses
import re
import typing
from typing import Optional, List

from purestorage_checkmk_test.flashblade.mock_blades import _BladesRequest
from purestorage_checkmk_test.flashblade.mock_route import _AuthTokenStorage, _JSONRequest, _JSONResponse, \
    _AuthenticatedJSONRoute, _ContinuationTokenContainer
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _NetworkInterfaceRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None


@dataclasses.dataclass
class Subnet:
    id: str
    name: str
    resource_type: str


@dataclasses.dataclass
class NetworkInterface:
    name: str
    id: str
    address: str
    enabled: bool
    gateway: str
    mtu: int
    netmask: typing.Optional[str]
    services: List[str]
    subnet: Subnet
    type: typing.Optional[str]
    vlan: typing.Optional[int]


@dataclasses.dataclass
class _NetworkInterfacesResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[NetworkInterface]] = None


class NetworkInterfaceContainer:
    _network_interfaces: List[NetworkInterface]
    _next_if: int

    def __init__(self):
        self._network_interfaces = []
        self._next_if = 0

    def add(self, interface: NetworkInterface):
        self._network_interfaces.append(interface)

    @property
    def network_interfaces(self) -> List[NetworkInterface]:
        return self._network_interfaces


class _NetworkInterfacesRoute(_AuthenticatedJSONRoute):
    _container: NetworkInterfaceContainer
    path = re.compile("^/api/2.9/network-interfaces$")

    def __init__(self, network_interfaces_container: NetworkInterfaceContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = network_interfaces_container
        self._continuation_token_container = _ContinuationTokenContainer[NetworkInterface]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _BladesRequest()
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
            total_capacity = 0

            # noinspection PyProtectedMember
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.network_interfaces, None, query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_NetworkInterfacesResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.network_interfaces),
                items=items,
            )
        )
