import dataclasses
import re
import uuid
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _DrivesRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class Drive:
    capacity: int
    name: Optional[str] = None
    status: Optional[str] = None
    id: Optional[str] = None
    details: Optional[str] = None
    type: Optional[str] = None


@dataclasses.dataclass
class _DrivesResponse:
    total: Drive
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Drive]] = None


class DrivesContainer:
    drives: List[Drive]
    _next_drive: int

    def __init__(self):
        self.drives = []
        self._next_drive = 0
        for i in range(1, 15):
            self.drives.append(
                Drive(
                    name=f"CH0.BAY{i}",
                    status="unused",
                    capacity=0
                ),
            )

    def add(self, capacity: int = 17592186044416):
        if self._next_drive == 15:
            raise Exception("All drive slots have been filled.")
        drive = self._next_drive
        self._next_drive += 1
        self.drives[drive].capacity = capacity
        self.drives[drive].status = "healthy"
        self.drives[drive].id = str(uuid.uuid4())


class _DrivesRoute(_AuthenticatedJSONRoute):
    _container: DrivesContainer
    path = re.compile("^/api/2.21/drives$")

    def __init__(self, drives_container: DrivesContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = drives_container
        self._continuation_token_container = _ContinuationTokenContainer[Drive]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _DrivesRequest()
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
            for drive in self._container.drives:
                total_capacity += drive.capacity

            # noinspection PyProtectedMember
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.drives, Drive(
                    capacity=total_capacity
                ), query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_DrivesResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.drives),
                total=total,
                items=items,
            )
        )
