import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _ArrayRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[str] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class ArrayStorage:
    data_reduction: Optional[float] = None
    total_effective: Optional[int] = None
    total_physical: Optional[int] = None
    total_provisioned: Optional[int] = None
    shared: Optional[int] = None
    snapshots: Optional[int] = None
    system: Optional[int] = None
    thin_provisioning: Optional[float] = None
    total_reduction: Optional[float] = None
    unique: Optional[int] = None
    virtual: Optional[int] = None
    replication: Optional[int] = None
    shared_effective: Optional[int] = None
    snapshots_effective: Optional[int] = None
    unique_effective: Optional[int] = None
    used_provisioned: Optional[int] = None


@dataclasses.dataclass
class Array:
    name: Optional[str] = None
    id: Optional[str] = None
    capacity: Optional[int] = None
    space: Optional[ArrayStorage] = None
    os: Optional[str] = None
    version: Optional[str] = None
    ntp_servers: Optional[List[str]] = None
    parity: Optional[float] = None
    scsi_timeout: Optional[int] = None


@dataclasses.dataclass
class _ArraysResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Array]] = None


class ArraysContainer:
    arrays: List[Array]
    _next_array: int = 0

    def __init__(self):
        self.arrays = [
            Array(
                name="Array 1",
                id="c2515cb1-c2ee-4a96-94e1-17795ae102c3",
                capacity=159471088056548,
                os="Purity//FA",
                parity=1.0,
                space=ArrayStorage(
                    data_reduction=1.9988064002916572,
                    shared=927816681,
                    snapshots=1672052155168,
                    system=0,
                    thin_provisioning=0.32957752017943587,
                    total_reduction=2.9814131543241658,
                    unique=18989280431108,
                    virtual=41281129198080,
                    replication=0,
                    shared_effective=0,
                    snapshots_effective=1803927576064,
                    unique_effective=39599435348992,
                    used_provisioned=0,
                    total_effective=41403361190400,
                    total_physical=20662260402957,
                    total_provisioned=61574798639104),
                ntp_servers=[
                    "time1.purestorage.com",
                    "time2.purestorage.com",
                    "time3.purestorage.com"
                ],
                version="6.4.5",
                scsi_timeout=600,
            )
        ]


class _ArraysRoute(_AuthenticatedJSONRoute):
    _arrays: ArraysContainer
    path = re.compile("^/api/2.21/arrays$")

    def __init__(self, arrays_container: ArraysContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = arrays_container
        self._continuation_token_container = _ContinuationTokenContainer[Array]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _ArrayRequest()
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
                self._container.arrays, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_ArraysResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.arrays),
                items=items
            )
        )
