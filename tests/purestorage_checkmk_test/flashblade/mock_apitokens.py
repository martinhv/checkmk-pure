import dataclasses
import re
import typing

from purestorage_checkmk.common import APIToken
from purestorage_checkmk_test.flashblade.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.flashblade.mock_route import _JSONResponse, _JSONRequest, _ContinuationTokenContainer, \
    _AuthTokenStorage, _AuthenticatedJSONRoute
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _APITokensRequest:
    admin_ids: typing.Optional[typing.List[str]] = None
    admin_names: typing.Optional[typing.List[str]] = None
    continuation_token: typing.Optional[str] = None
    expose_api_token: typing.Optional[bool] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None


@dataclasses.dataclass
class _APITokensResponse:
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[typing.List[APIToken]] = None


class _APITokensRoute(_AuthenticatedJSONRoute):
    _api_tokens: APITokensContainer
    path = re.compile("^/api/2.9/admins/api-tokens")

    def __init__(self, api_tokens_container: APITokensContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = api_tokens_container
        self._continuation_token_container = _ContinuationTokenContainer[APIToken]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _APITokensRequest()
        req.query_to_dataclass(query)

        if query.admin_ids is not None:
            return Response(
                400,
                {},
                "The admin_ids parameter is not supported by the mock.".encode('ascii')
            )
        if query.admin_names is not None:
            return Response(
                400,
                {},
                "The admin_names parameter is not supported by the mock.".encode('ascii')
            )
        if query.expose_api_token is not None:
            return Response(
                400,
                {},
                "The expose_api_token parameter is not supported by the mock.".encode('ascii')
            )
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
                self._container.api_tokens, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_APITokensResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.api_tokens),
                items=items
            )
        )
