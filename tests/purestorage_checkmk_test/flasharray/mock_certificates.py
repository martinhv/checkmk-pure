import dataclasses
import re
import time
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _CertificatesRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[List[str]] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class Certificate:
    name: Optional[str] = None
    status: Optional[str] = None
    id: Optional[str] = None
    details: Optional[str] = None
    type: Optional[str] = None
    valid_to: Optional[int] = None


@dataclasses.dataclass
class _CertificatesResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[Certificate]] = None


class CertificatesContainer:
    certificates: List[Certificate]
    _next_certificate: int = 0

    def __init__(self):
        self.certificates = [
            Certificate(
                name="Certificate1",
                status="self-signed",
                valid_to=(int(time.time()) + (120 * 86400)) * 1000
            ),
        ]


class _CertificatesRoute(_AuthenticatedJSONRoute):
    _container: CertificatesContainer
    path = re.compile("^/api/2.21/certificates$")

    def __init__(self, certificates_container: CertificatesContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = certificates_container
        self._continuation_token_container = _ContinuationTokenContainer[Certificate]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _CertificatesRequest()
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

        else:  # noinspection PyProtectedMember
            continuation_token, items, remaining_items, total = self._continuation_token_container.create(
                self._container.certificates, None, query.limit, query.offset
            )
        # noinspection PyProtectedMember
        return _JSONResponse(
            body=_CertificatesResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.certificates),
                items=items
            )
        )
