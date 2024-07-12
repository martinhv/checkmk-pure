import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flashblade.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _LAGsRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class LAGPort:
    id: Optional[str] = None
    name: Optional[str] = None
    resource_type: Optional[str] = None


@dataclasses.dataclass
class LAG:
    name: Optional[str] = None
    lag_speed: Optional[int] = None
    id: Optional[str] = None
    mac_address: Optional[string] = None
    port_speed: Optional[int] = None
    status: Optional[str] = None
    ports: Optional[List[LAGPort]] = None


@dataclasses.dataclass
class _LAGsResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[LAG]] = None


class LAGsContainer:
    _lags: List[LAG]
    _next_lag: int

    def __init__(self):
        self._lags = []
        self._next_lag = 0
        for i in range(1, 3):
            self._lags.append(
                LAG(
                    name=f"Link Aggregation Group {i}",
                    lag_speed=260000000000,
                    mac_address="24:a9:37:11:f5:21",
                    port_speed=10000000000,
                    status="healthy",
                    ports=[
                        LAGPort(
                            name="CH1.FM1.ETH2.2",
                            resource_type="hardware"
                        ),
                        LAGPort(
                            name="CH2.FM2.ETH3.1",
                            resource_type="hardware",
                        )],
                ),
            )

    @property
    def lags(self) -> List[LAG]:
        return self._lags


class _LAGsRoute(_AuthenticatedJSONRoute):
    _container: LAGsContainer
    path = re.compile("^/api/2.9/hardware_lags$")

    def __init__(self, lags_container: LAGsContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = lags_container
        self._continuation_token_container = _ContinuationTokenContainer[LAG]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _LAGsRequest()
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
                self._container.lags, None, query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_LAGsResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.lags),
                items=items
            )
        )
