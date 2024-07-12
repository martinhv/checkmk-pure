import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flashblade.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _ConnectorsRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class Connector:
    name: Optional[str] = None
    connector_type: Optional[str] = None
    id: Optional[str] = None
    lane_speed: Optional[int] = None
    port_count: Optional[int] = None
    transceiver_type: Optional[str] = None


@dataclasses.dataclass
class _ConnectorsResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Connector]] = None


class ConnectorsContainer:
    _connectors: List[Connector]
    _next_connector: int = 0

    def __init__(self):
        self._connectors = []
        for i in range(1, 3):
            self._connectors.append(
                Connector(
                    name=f"CON{i}",
                    connector_type="QSFP",
                    lane_speed=10000000000,
                    port_count=1,
                    transceiver_type="40GBASE-LR4"
                ),
            )

    @property
    def connectors(self) -> List[Connector]:
        return self._connectors


class _ConnectorsRoute(_AuthenticatedJSONRoute):
    _container: ConnectorsContainer
    path = re.compile("^/api/2.9/hardware_connectors$")

    def __init__(self, connectors_container: ConnectorsContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = connectors_container
        self._continuation_token_container = _ContinuationTokenContainer[Connector]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _ConnectorsRequest()
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
                self._container.connectors, None, query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_ConnectorsResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.connectors),
                items=items
            )
        )
