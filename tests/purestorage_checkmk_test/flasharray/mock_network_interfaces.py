import dataclasses
import re
import typing
from typing import List
from typing import Optional

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class NetworkInterfaceServices:
    services: typing.Optional[str] = None


@dataclasses.dataclass
class NetworkInterfaceSubnet:
    name: Optional[str] = None


@dataclasses.dataclass
class NetworkSubinterfaces:
    name: typing.Optional[str] = None


@dataclasses.dataclass
class NetworkInterfaceEth:
    address: typing.Optional[str] = None
    gateway: typing.Optional[str] = None
    mac_address: typing.Optional[str] = None
    mtu: typing.Optional[int] = None
    netmask: typing.Optional[str] = None
    subtype: typing.Optional[str] = None
    subinterfaces: List[NetworkSubinterfaces] = None
    subnet: NetworkInterfaceSubnet = None
    vlan: typing.Optional[int] = None


@dataclasses.dataclass
class NetworkInterfaceFC:
    wwn: typing.Optional[str] = None


@dataclasses.dataclass
class NetworkInterface:
    name: typing.Optional[str] = None
    enabled: typing.Optional[bool] = None
    interface_type: typing.Optional[str] = None
    services: Optional[List[str]] = None
    speed: typing.Optional[int] = None
    eth: NetworkInterfaceEth = None
    fc: NetworkInterfaceFC = None


@dataclasses.dataclass
class _NetworkInterfaceRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None
    total_item_count: bool = False


@dataclasses.dataclass
class _NetworkInterfaceResponse:
    more_items_remaining: bool = False
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[List[NetworkInterface]] = None


class NetworkInterfaceContainer:
    _network_interfaces: List[NetworkInterface]

    def __init__(self):
        self._network_interfaces = []
        self._network_interfaces.append(
            NetworkInterface(
                name="eth0",
                enabled=True,
                interface_type="eth",
                speed=1000000000,
                services=["management", "iscsi"],
                eth=NetworkInterfaceEth(
                    address="128.0.0.12",
                    gateway="128.0.0.255",
                    mac_address="00:00:2A:3B:4F:AA",
                    mtu=1500,
                    netmask="255.255.255.0",
                    subtype="virtual",
                    subinterfaces=[NetworkSubinterfaces(
                        name="Subinterface1",
                    )],
                    subnet=NetworkInterfaceSubnet(
                        name="Subnet1",
                    ),
                    vlan=12
                )
            )
        )
        self._network_interfaces.append(
            NetworkInterface(
                name="fc0",
                enabled=True,
                interface_type="fc",
                speed=2000000000,
                services=["iscsi"],
                fc=NetworkInterfaceFC(
                    wwn="AB:CD:EF:12:34:56"
                )
            )
        )
        self._network_interfaces.append(
            NetworkInterface(
                name=None,
                enabled=None,
                interface_type="eth",
                speed=None,
                services=None,
                eth=NetworkInterfaceEth(
                    address=None,
                    gateway=None,
                    mac_address=None,
                    mtu=None,
                    netmask=None,
                    subinterfaces=None,
                    subnet=None,
                    vlan=None
                )
            )
        )

    @property
    def network_interface(self) -> List[NetworkInterface]:
        return self._network_interfaces


class _NetworkInterfaceRoute(_AuthenticatedJSONRoute):
    _container: NetworkInterfaceContainer
    path = re.compile("^/api/2.21/network-interfaces$")

    def __init__(self, network_interface_container: NetworkInterfaceContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = network_interface_container
        self._continuation_token_container = _ContinuationTokenContainer[NetworkInterface]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _NetworkInterfaceRequest()
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
                self._container.network_interface, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_NetworkInterfaceResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.network_interface),
                items=items
            )
        )
