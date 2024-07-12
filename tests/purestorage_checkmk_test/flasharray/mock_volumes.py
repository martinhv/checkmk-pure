import dataclasses
import re
import typing
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _VolumesRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[str] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class _VolumeQOS:
    bandwidth_limit: typing.Optional[int] = None
    iops_limit: typing.Optional[int] = None


@dataclasses.dataclass
class _VolumePrioAdjustment:
    priority_adjustment_operator: typing.Optional[str] = None
    priority_adjustment_value: typing.Optional[int] = None


@dataclasses.dataclass
class _VolumeSpace:
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
    snapshots_effective: typing.Optional[int] = None
    unique_effective: typing.Optional[int] = None
    total_effective: typing.Optional[int] = None


@dataclasses.dataclass
class _VolumePod:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None


@dataclasses.dataclass
class _VolumeSource:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None


@dataclasses.dataclass
class _VolumeGroup:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None


@dataclasses.dataclass
class Volume:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None
    connection_count: typing.Optional[int] = None
    created: typing.Optional[int] = None
    destroyed: typing.Optional[bool] = None
    host_encryption_key_status: typing.Optional[str] = None
    provisioned: typing.Optional[int] = None
    qos: Optional[_VolumeQOS] = None
    priority_adjustment: Optional[_VolumePrioAdjustment] = None
    serial: typing.Optional[str] = None
    space: Optional[_VolumeSpace] = None
    time_remaining: typing.Optional[int] = None
    pod: Optional[_VolumePod] = None
    source: Optional[_VolumeSource] = None
    subtype: typing.Optional[str] = None
    volume_group: Optional[_VolumeGroup] = None
    requested_promotion_state: typing.Optional[str] = None
    promotion_status: typing.Optional[str] = None
    priority: typing.Optional[int] = None


@dataclasses.dataclass
class _VolumesResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Volume]] = None


class VolumesContainer:
    volumes: List[Volume] = []
    _next_Volumes: int = 0

    def __init__(self):
        self.volumes.append(
            Volume(
                id="123454321",
                name="volume 1",
                connection_count=0,
            )
        )


class _VolumesRoute(_AuthenticatedJSONRoute):
    _Volumes: VolumesContainer
    path = re.compile("^/api/2.21/volumes$")

    def __init__(self, Volumes_container: VolumesContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = Volumes_container
        self._continuation_token_container = _ContinuationTokenContainer[Volume]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _VolumesRequest()
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
                self._container.volumes, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_VolumesResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.volumes),
                items=items
            )
        )
