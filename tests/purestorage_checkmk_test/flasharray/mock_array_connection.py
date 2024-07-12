import dataclasses
import re
import typing
from typing import List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class ArrayConnectionThrottleWindow:
    start: typing.Optional[int] = None
    end: typing.Optional[int] = None


@dataclasses.dataclass
class ArrayConnectionThrottle:
    window: ArrayConnectionThrottleWindow
    default_limit: typing.Optional[int] = None
    window_limit: typing.Optional[int] = None


@dataclasses.dataclass
class ArrayConnection:
    name: typing.Optional[str] = None
    status: typing.Optional[str] = None
    management_address: typing.Optional[str] = None
    replication_addresses: typing.Optional[List[str]] = None
    type: typing.Optional[str] = None
    replication_transport: typing.Optional[str] = None
    version: typing.Optional[str] = None
    throttle: ArrayConnectionThrottle = None


@dataclasses.dataclass
class _ArrayConnectionRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None
    total_item_count: bool = False


@dataclasses.dataclass
class _ArrayConnectionResponse:
    more_items_remaining: bool = False
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[typing.List[ArrayConnection]] = None


class ArrayConnectionContainer:
    _array_connections: typing.List[ArrayConnection] = []

    def __init__(self):
        self._array_connections.append(
            ArrayConnection(
                name="Array Connection 1",
                management_address="192.168.233.244",
                replication_addresses="123.456.789.012",
                type="async-replication",
                replication_transport="ip",
                version="0.9beta",
                status="connected"
            )
        )

    @property
    def array_connection(self) -> typing.List[ArrayConnection]:
        return self._array_connections


class _ArrayConnectionRoute(_AuthenticatedJSONRoute):
    _container: ArrayConnectionContainer
    path = re.compile("^/api/2.21/array-connections$")

    def __init__(self, array_connection_container: ArrayConnectionContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = array_connection_container
        self._continuation_token_container = _ContinuationTokenContainer[ArrayConnection]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _ArrayConnectionRequest()
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
                self._container.array_connection, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_ArrayConnectionResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.array_connection),
                items=items
            )
        )
