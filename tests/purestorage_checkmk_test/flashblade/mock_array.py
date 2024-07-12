import dataclasses
import re
import typing
import uuid

from purestorage_checkmk_test.flashblade.mock_route import _JSONRequest, _JSONResponse, _ContinuationTokenContainer, \
    _AuthTokenStorage, _AuthenticatedJSONRoute
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class EradicationConfig:
    manual_eradication: str
    eradication_delay: int


@dataclasses.dataclass
class DataAtRest:
    algorithms: typing.List[str]
    enabled: bool
    entropy_source: str


@dataclasses.dataclass
class EncryptionConfig:
    data_at_rest: DataAtRest


@dataclasses.dataclass
class Array:
    name: str
    id: str
    os: str
    revision: str
    version: str
    time_zone: str
    idle_timeout: int
    ntp_servers: typing.List[str]
    smb_mode: str
    product_type: str
    eradication_config: EradicationConfig
    encryption: typing.Optional[EncryptionConfig] = None
    security_update: typing.Optional[str] = None
    banner: typing.Optional[str] = None


@dataclasses.dataclass
class _ArraysRequest:
    continuation_token: typing.Optional[str] = None
    filter: typing.Optional[str] = None
    limit: int = 100
    names: typing.Optional[str] = None
    offset: int = 0
    sort: typing.List[str] = None


@dataclasses.dataclass
class _ArraysResponse:
    total_item_count: int = 0
    continuation_token: typing.Optional[str] = None
    items: typing.Optional[typing.List[Array]] = None


class ArraysContainer:
    arrays: typing.List[Array]

    def __init__(self):
        self.arrays = []
        self.arrays.append(
            Array(
                name="GSE-FB01",
                id=uuid.uuid4().__str__(),
                os="Purity//FB",
                revision="e9c821f9",
                version="4.1.5",
                time_zone="US/Eastern",
                banner=None,
                idle_timeout=1800000,
                ntp_servers=[
                    "0.us.pool.ntp.org",
                    "1.us.pool.ntp.org",
                    "2.us.pool.ntp.org",
                    "3.us.pool.ntp.org"
                ],
                smb_mode="native",
                product_type="FlashBlade",
                eradication_config=EradicationConfig(
                    manual_eradication="all-enabled",
                    eradication_delay=86400000,
                ),
                security_update=None,
                encryption=EncryptionConfig(
                    data_at_rest=DataAtRest(
                        algorithms=["AES-256-CTR"],
                        entropy_source="rdseed",
                        enabled=True,
                    ),
                ),
            )
        )


class _ArraysRoute(_AuthenticatedJSONRoute):
    _alerts: ArraysContainer
    path = re.compile("^/api/2.9/arrays$")

    def __init__(self, array_container: ArraysContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = array_container
        self._continuation_token_container = _ContinuationTokenContainer[Array]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _ArraysRequest()
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
                self._container.arrays, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_ArraysResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.arrays),
                items=items
            )
        )
