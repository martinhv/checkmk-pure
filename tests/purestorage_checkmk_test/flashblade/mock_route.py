import abc
import dataclasses
import json
import re
import uuid
from abc import abstractmethod
from typing import Set, Any, Dict, List, TypeVar, Generic, Optional, Tuple

from purestorage_checkmk_test.flashblade.mock_apitokens_container import APITokensContainer
from purestorage_checkmk_test.httpmock import Route, Request, Response


class _AuthTokenStorage:
    auth_tokens: Set[str] = set()


class _LoginRoute(Route):
    """
    This route simulates the /api/login endpoint where you can exchange an API token for an auth token. This auth token
    can then be used to authenticate against other endpoints using the x-auth-token header.

    Example:

    >>> auth_token_storage = _AuthTokenStorage()
    >>> route = _LoginRoute(APITokensContainer({"valid-api-token"}), auth_token_storage)

    You can now use auth_token_storage
    """

    path = re.compile("^/api/login$")

    def __init__(self, api_tokens: APITokensContainer, auth_token_storage: _AuthTokenStorage):
        self._api_tokens = api_tokens
        self._auth_token_storage = auth_token_storage

    def handle(self, req: Request) -> Response:
        if req.method != "POST":
            return Response(205)
        try:
            api_token = req.headers["api-token"][0]
            if api_token in self._api_tokens:
                auth_token = str(uuid.uuid4())
                self._auth_token_storage.auth_tokens.add(auth_token)
                return Response(
                    200,
                    {
                        "x-auth-token": [auth_token]
                    },
                    "{\"username\":\"dummy\"}".encode('ascii')
                )
            return Response(
                400,
                {},
                "Authentication failed".encode('ascii')
            )
        except KeyError:
            return Response(
                400,
                {},
                "Authentication failed".encode('ascii')
            )


@dataclasses.dataclass
class _JSONRequest(Request):
    decoded_body: Any = None

    def __init__(self, req: Request):
        super().__init__(req.method, req.path, req.headers, req.body)
        if req.method != "GET" and req.body is not None and len(req.body) > 0:
            self.decoded_body = json.loads(req.body)


@dataclasses.dataclass
class _JSONResponse:
    status: int = 200
    headers: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    body: Any = None

    def to_response(self) -> Response:
        headers = self.headers
        headers['Content-Type'] = ['application/json']
        if dataclasses.is_dataclass(self.body):
            body = dataclasses.asdict(self.body)
        else:
            body = self.body
        return Response(
            self.status,
            headers,
            json.dumps(body).encode('ascii')
        )


class _JSONRoute(Route, abc.ABC):
    """
    This route automatically decodes the request from JSON and the response to JSON.
    """

    def handle(self, req: Request) -> Response:
        response = self.handle_json(_JSONRequest(req))
        if isinstance(response, _JSONResponse):
            response = response.to_response()
        return response

    @abstractmethod
    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        pass


class _AuthenticatedJSONRoute(_JSONRoute, abc.ABC):
    """
    This class is a route that automatically authenticates the user and decodes the JSON request. It also encodes the
    response to JSON.
    """

    def __init__(self, auth_token_storage: _AuthTokenStorage):
        self._auth_token_storage = auth_token_storage

    def handle(self, req: Request) -> Response:
        try:
            auth_token = req.headers['x-auth-token'][0]
            if auth_token not in self._auth_token_storage.auth_tokens:
                return Response(401)
        except KeyError:
            return Response(401)
        return super().handle(req)


T = TypeVar("T")


@dataclasses.dataclass
class _ContinuationTokenItem(Generic[T]):
    items: List[T]
    total: Optional[T]


class _ContinuationTokenContainer(Generic[T]):
    _data: Dict[str, _ContinuationTokenItem[T]] = {}

    def create(self, entries: List[T], total: Optional[T], limit: int, offset: int) -> Tuple[str, List[T], List[T], T]:
        continuation_token = str(uuid.uuid4())
        self._data[continuation_token] = _ContinuationTokenItem(
            entries,
            total,
        )
        items, remaining_items, total = self.get(continuation_token, limit, offset)
        if len(remaining_items) == 0:
            continuation_token = None
        return continuation_token, items, remaining_items, total

    def get(self, continuation_token: str, limit: int, offset: int = 0) -> Tuple[List[T], List[T], T]:
        try:
            entry = self._data[continuation_token]
            result = entry.items[offset:limit].copy()
            entry.items = entry.items[offset + limit:].copy()
            remaining_items = entry.items
            total = self._data[continuation_token].total
            if len(entry.items) == 0:
                del self._data[continuation_token]
            else:
                self._data[continuation_token].items = entry.items
            return result, remaining_items, total
        except KeyError as e:
            return [], [], None
