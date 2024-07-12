import dataclasses
import re
import typing
from typing import Optional, List

from purestorage_checkmk_test.flashblade.mock_blades import _BladesRequest
from purestorage_checkmk_test.flashblade.mock_route import _AuthTokenStorage, _JSONRequest, _JSONResponse, \
    _AuthenticatedJSONRoute, _ContinuationTokenContainer
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _SupportRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None


@dataclasses.dataclass
class _RemoteAssistPaths:
    component_name: typing.Optional[str] = None
    status: typing.Optional[str] = None


@dataclasses.dataclass
class Support:
    name: typing.Optional[str] = None
    id: typing.Optional[str] = None
    phonehome_enabled: typing.Optional[bool] = None
    proxy: typing.Optional[str] = None
    remote_assist_active: typing.Optional[bool] = None
    remote_assist_opened: typing.Optional[str] = None
    remote_assist_expires: typing.Optional[str] = None
    remote_assist_status: typing.Optional[str] = None
    remote_assist_path: Optional[_RemoteAssistPaths] = None


@dataclasses.dataclass
class _SupportResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Support]] = None


class SupportContainer:
    _support: List[Support]
    _next_support: int

    def __init__(self):
        self._support = []
        self._next_support = 0
        self._support.append(
            Support(
                name="Standart Support",
                id="1234ididid",
                phonehome_enabled=True,
                proxy="no_proxy",
                remote_assist_active=False,
                remote_assist_opened="Never",
                remote_assist_expires="Tomorrow",
                remote_assist_status="Disconnected",
            )
        )

    @property
    def support(self) -> List[Support]:
        return self._support


class _SupportRoute(_AuthenticatedJSONRoute):
    _container: SupportContainer
    path = re.compile("^/api/2.9/support")

    def __init__(self, support_container: SupportContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = support_container
        self._continuation_token_container = _ContinuationTokenContainer[Support]()

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
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.support, None, query.limit, query.offset

            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_SupportResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.support),
                items=items,
            )
        )
