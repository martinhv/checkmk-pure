import dataclasses
import re
import time
import typing
import uuid
from typing import Optional, List

from purestorage_checkmk_test.flashblade.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _ArraysSpaceRequest:
    end_time: typing.Optional[int] = None
    resolution: typing.Optional[int] = None
    start_time: typing.Optional[int] = None
    type: typing.Optional[str] = None


@dataclasses.dataclass
class ArraysSpaceSpace:
    data_reduction: float
    snapshots: int
    total_physical: int
    unique: int
    virtual: int


@dataclasses.dataclass
class ArraysSpace:
    name: str
    id: str
    capacity: int
    parity: float
    time: int
    space: ArraysSpaceSpace


@dataclasses.dataclass
class _ArraysSpaceResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[ArraysSpace]] = None


class ArraysSpaceContainer:
    blade: ArraysSpace
    filesystem: ArraysSpace
    objectstore: ArraysSpace
    _next_alert: int = 0

    def __init__(self):
        self.blade = ArraysSpace(
            name="GSE-FB01",
            id=uuid.uuid4().__str__(),
            time=int(time.time() * 1000),
            capacity=100 * 1024 * 1024 * 1024,
            parity=1.0,
            space=ArraysSpaceSpace(
                virtual=50 * 1024 * 1024 * 1024,
                unique=50 * 1024 * 1024 * 1024,
                snapshots=0,
                data_reduction=1,
                total_physical=50 * 1024 * 1024 * 1024
            )
        )
        self.filesystem = ArraysSpace(
            name="GSE-FB01",
            id=uuid.uuid4().__str__(),
            time=int(time.time() * 1000),
            capacity=100 * 1024 * 1024 * 1024,
            parity=1.0,
            space=ArraysSpaceSpace(
                virtual=50 * 1024 * 1024 * 1024,
                unique=50 * 1024 * 1024 * 1024,
                snapshots=0,
                data_reduction=1,
                total_physical=50 * 1024 * 1024 * 1024
            )
        )
        self.objectstore = ArraysSpace(
            name="GSE-FB01",
            id=uuid.uuid4().__str__(),
            time=int(time.time() * 1000),
            capacity=0,
            parity=1.0,
            space=ArraysSpaceSpace(
                virtual=0,
                unique=0,
                snapshots=0,
                data_reduction=0.0,
                total_physical=0
            )
        )


class _ArraysSpaceRoute(_AuthenticatedJSONRoute):
    _space: ArraysSpaceContainer
    path = re.compile("^/api/2.9/arrays/space$")

    def __init__(self, space: ArraysSpaceContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._space = space

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _ArraysSpaceRequest()
        req.query_to_dataclass(query)

        if query.start_time is not None:
            return Response(
                400,
                {},
                "The start_time parameter is not supported by the mock.".encode('ascii')
            )
        if query.end_time is not None:
            return Response(
                400,
                {},
                "The end_time parameter is not supported by the mock.".encode('ascii')
            )
        if query.resolution is not None:
            return Response(
                400,
                {},
                "The resolution parameter is not supported by the mock.".encode('ascii')
            )
        space: ArraysSpace
        if query.type == "array" or query.type is None:
            space = self._space.blade
        elif query.type == "file-system":
            space = self._space.filesystem
        elif query.type == "object-store":
            space = self._space.objectstore
        else:
            return Response(
                400,
                {},
                "Invalid type parameter".encode('ascii')
            )
        return _JSONResponse(
            body=_ArraysSpaceResponse(
                continuation_token=None,
                total_item_count=1,
                items=[
                    space
                ]
            )
        )
