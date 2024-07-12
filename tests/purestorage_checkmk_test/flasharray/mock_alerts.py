import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _AlertRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[str] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class Alert:
    name: Optional[str] = None
    id: Optional[str] = None
    actual: Optional[str] = None
    code: Optional[int] = None
    category: Optional[str] = None
    closed: Optional[int] = None
    component_name: Optional[str] = None
    component_type: Optional[str] = None
    created: Optional[int] = None
    description: Optional[str] = None
    expected: Optional[str] = None
    flagged: Optional[bool] = False
    issue: Optional[str] = None
    knowledge_base_url: Optional[str] = None
    notified: Optional[int] = None
    severity: Optional[str] = None
    state: Optional[str] = None
    summary: Optional[str] = None
    updated: Optional[int] = None


@dataclasses.dataclass
class _AlertsResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Alert]] = None


class AlertsContainer:
    alerts: List[Alert]
    _next_alert: int = 0

    def __init__(self):
        self.alerts = []


class _AlertsRoute(_AuthenticatedJSONRoute):
    _alerts: AlertsContainer
    path = re.compile("^/api/2.21/alerts$")

    def __init__(self, alerts_container: AlertsContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = alerts_container
        self._continuation_token_container = _ContinuationTokenContainer[Alert]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _AlertRequest()
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
                self._container.alerts, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_AlertsResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.alerts),
                items=items
            )
        )
