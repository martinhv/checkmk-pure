import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _ControllersRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class Controller:
    name: Optional[str] = None
    status: Optional[str] = None
    id: Optional[str] = None
    details: Optional[str] = None
    type: Optional[str] = None
    mode: Optional[str] = None
    model: Optional[str] = None


@dataclasses.dataclass
class _ControllersResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Controller]] = None


class ControllersContainer:
    _controllers: List[Controller]
    _next_controller: int = 0

    def __init__(self):
        self._controllers = []
        for i in range(1, 3):
            self._controllers.append(
                Controller(
                    name=f"CT{i}",
                    status="ready",
                    mode="primary",
                    model="FA-C40R3"
                ),
            )

    def add(self):
        if self._next_controller == 2:
            raise Exception("All controller slots have been filled.")
        controller = self._next_controller
        self._next_controller += 1
        self._controllers[controller].status = "ready"
        self._controllers[controller].mode = "secondary"
        self._controllers[controller].model = "FA-C40R3"

    @property
    def controllers(self) -> List[Controller]:
        return self._controllers


class _ControllersRoute(_AuthenticatedJSONRoute):
    _container: ControllersContainer
    path = re.compile("^/api/2.21/controllers$")

    def __init__(self, controllers_container: ControllersContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = controllers_container
        self._continuation_token_container = _ContinuationTokenContainer[Controller]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _ControllersRequest()
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
                self._container.controllers, None, query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_ControllersResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.controllers),
                items=items
            )
        )
