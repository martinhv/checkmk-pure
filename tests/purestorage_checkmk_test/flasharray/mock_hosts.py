import dataclasses
import re
import typing
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _HostsRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[str] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class _HostCHAP:
    host_password: typing.Optional[str] = None
    host_user: typing.Optional[str] = None
    target_password: typing.Optional[str] = None
    target_user: typing.Optional[str] = None


@dataclasses.dataclass
class _HostGroup:
    name: typing.Optional[str] = None


@dataclasses.dataclass
class _HostPortConnectivity:
    details: typing.Optional[str] = None
    status: typing.Optional[str] = None


@dataclasses.dataclass
class _HostSpace:
    data_reduction: typing.Optional[float] = None
    shared: typing.Optional[int] = None
    snapshots: typing.Optional[int] = None
    system: typing.Optional[int] = None
    thin_provisioning: typing.Optional[float] = None
    total_physical: typing.Optional[int] = None
    total_provisioned: typing.Optional[int] = None
    total_reduction: typing.Optional[float] = None
    unique: typing.Optional[int] = None
    virtual: typing.Optional[int] = None


@dataclasses.dataclass
class _HostPreferredArrays:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None


@dataclasses.dataclass
class Hosts:
    name: typing.Optional[str] = None
    chap: Optional[_HostCHAP] = None
    connection_count: typing.Optional[int] = None
    host_group: Optional[_HostGroup] = None
    iqns: Optional[List[str]] = None
    nqns: Optional[List[str]] = None
    personality: typing.Optional[str] = None
    port_connectivity: Optional[_HostPortConnectivity] = None
    space: Optional[_HostSpace] = None
    preferred_arrays: Optional[_HostPreferredArrays] = None
    wwns: Optional[List[str]] = None
    is_local: typing.Optional[bool] = None
    vlan: typing.Optional[str] = None


@dataclasses.dataclass
class _HostsResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Hosts]] = None


class HostsContainer:
    hosts: List[Hosts] = []
    _next_Hosts: int = 0

    def __init__(self):
        self.hosts.append(
            Hosts(
                name="Host 1",
                connection_count=5,
                iqns=["iqn1", "iqn2"],
                nqns=["nqn1", "nqn2"],
                personality="hpux",
                is_local=False,
                vlan="1112"
            )
        )


class _HostsRoute(_AuthenticatedJSONRoute):
    _Hosts: HostsContainer
    path = re.compile("^/api/2.21/hosts$")

    def __init__(self, Hosts_container: HostsContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = Hosts_container
        self._continuation_token_container = _ContinuationTokenContainer[Hosts]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _HostsRequest()
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
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.hosts, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_HostsResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.hosts),
                items=items
            )
        )
