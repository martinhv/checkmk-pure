import dataclasses
import re
import uuid
from typing import Optional, List

from purestorage_checkmk_test.flashblade.mock_route import _AuthTokenStorage, _JSONRequest, _JSONResponse, \
    _AuthenticatedJSONRoute, _ContinuationTokenContainer
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _BladesRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class Blade:
    raw_capacity: int
    name: Optional[str] = None
    status: Optional[str] = None
    id: Optional[str] = None
    details: Optional[str] = None
    progress: Optional[float] = None
    target: Optional[str] = None


@dataclasses.dataclass
class _BladesResponse:
    total: Blade
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Blade]] = None


class BladesContainer:
    _blades: List[Blade]
    _next_blade: int = 0

    def __init__(self):
        self._blades = []
        for i in range(1, 15):
            self._blades.append(
                Blade(
                    name=f"CH1.FB{i}",
                    status="unused",
                    raw_capacity=0
                ),
            )

    def add(self, raw_capacity: int = 17592186044416):
        if self._next_blade == 16:
            raise Exception("All blade slots have been filled.")
        blade = self._next_blade
        self._next_blade += 1
        self._blades[blade].raw_capacity = raw_capacity
        self._blades[blade].status = "healthy"
        self._blades[blade].id = str(uuid.uuid4())

    @property
    def blades(self) -> List[Blade]:
        return self._blades


class _BladesRoute(_AuthenticatedJSONRoute):
    _container: BladesContainer
    path = re.compile("^/api/2.9/blades$")

    def __init__(self, blades_container: BladesContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = blades_container
        self._continuation_token_container = _ContinuationTokenContainer[Blade]()

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
            for blade in self._container.blades:
                total_capacity += blade.raw_capacity

            # noinspection PyProtectedMember
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.blades, Blade(
                    raw_capacity=total_capacity
                ), query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_BladesResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.blades),
                total=total,
                items=items,
            )
        )
