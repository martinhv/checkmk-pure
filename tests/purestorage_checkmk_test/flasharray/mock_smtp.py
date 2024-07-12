import dataclasses
import re
import typing

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class SMTPServer:
    name: str
    description: typing.Optional[str] = None
    password: typing.Optional[str] = None
    relay_host: typing.Optional[str] = None
    sender_domain: typing.Optional[str] = None
    user_name: typing.Optional[str] = None


@dataclasses.dataclass
class _SMTPServersRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None
    total_item_count: bool = False


@dataclasses.dataclass
class _SMTPServersResponse:
    more_items_remaining: bool = False
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[typing.List[SMTPServer]] = None


class SMTPServersContainer:
    smtp_servers: typing.List[SMTPServer] = []

    def __init__(self):
        self.smtp_servers.append(
            SMTPServer(
                name="default",
                relay_host="127.0.0.1:25"
            )
        )


class _SMTPServersRoute(_AuthenticatedJSONRoute):
    _container: SMTPServersContainer
    path = re.compile("^/api/2.21/smtp-servers$")

    def __init__(self, smtp_servers_container: SMTPServersContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = smtp_servers_container
        self._continuation_token_container = _ContinuationTokenContainer[SMTPServer]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _SMTPServersRequest()
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
                self._container.smtp_servers, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_SMTPServersResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.smtp_servers),
                items=items
            )
        )
