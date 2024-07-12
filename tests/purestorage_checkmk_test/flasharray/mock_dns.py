import dataclasses
import re
import typing

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class DNSServerSource:
    name: str


@dataclasses.dataclass
class DNSParameters:
    name: str
    domain: str
    nameservers: typing.List[str] = dataclasses.field(default_factory=list)
    services: typing.List[str] = dataclasses.field(default_factory=list)
    source: typing.Optional[DNSServerSource] = None


@dataclasses.dataclass
class _DNSServersRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort: typing.List[str] = None
    total_item_count: bool = False


@dataclasses.dataclass
class _DNSServersResponse:
    more_items_remaining: bool = False
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[typing.List[DNSParameters]] = None


class DNSServersContainer:
    _dns_servers: typing.List[DNSParameters] = []

    def __init__(self):
        self._dns_servers.append(
            DNSParameters(
                name="default",
                domain="example.com",
                nameservers=["127.0.0.1", "127.0.0.2"],
                services=["blablabla", "blublublu"]
            )
        )

    @property
    def dns_servers(self) -> typing.List[DNSParameters]:
        return self._dns_servers


class _DNSServersRoute(_AuthenticatedJSONRoute):
    _container: DNSServersContainer
    path = re.compile("^/api/2.21/dns$")

    def __init__(self, dns_servers_container: DNSServersContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = dns_servers_container
        self._continuation_token_container = _ContinuationTokenContainer[DNSParameters]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _DNSServersRequest()
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
                self._container.dns_servers, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_DNSServersResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.dns_servers),
                items=items
            )
        )
