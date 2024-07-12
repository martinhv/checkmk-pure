import dataclasses
import re
from typing import Optional, List

from purestorage_checkmk_test.flasharray.mock_route import _AuthenticatedJSONRoute, _AuthTokenStorage, \
    _ContinuationTokenContainer, _JSONRequest, _JSONResponse
from purestorage_checkmk_test.httpmock import Response


@dataclasses.dataclass
class _AdminSettingsRequest:
    continuation_token: Optional[str] = None
    filter: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: int = 100
    names: Optional[str] = None
    offset: int = 0
    sort: List[str] = None
    total_only: bool = False


@dataclasses.dataclass
class AdminSettings:
    lockout_duration: Optional[int] = None
    max_login_attempts: Optional[int] = None
    min_password_length: Optional[int] = None
    single_sign_on_enabled: Optional[bool] = None


@dataclasses.dataclass
class _AdminSettingsResponse:
    total_item_count: int = 0
    continuation_token: Optional[str] = None
    items: Optional[List[AdminSettings]] = None


class AdminSettingsContainer:
    _admin_settings: List[AdminSettings] = []

    def __init__(self):
        self._admin_settings.append(
            AdminSettings(
                lockout_duration=3600000,
                max_login_attempts=10,
                min_password_length=8,
                single_sign_on_enabled=True
            )
        )

    @property
    def admin_settings(self) -> List[AdminSettings]:
        return self._admin_settings


class _AdminSettingsRoute(_AuthenticatedJSONRoute):
    _container: AdminSettingsContainer
    path = re.compile("^/api/2.21/admins/settings$")

    def __init__(self, admin_settings_container: AdminSettingsContainer, auth_token_storage: _AuthTokenStorage):
        super().__init__(auth_token_storage)
        self._container = admin_settings_container
        self._continuation_token_container = _ContinuationTokenContainer[AdminSettings]()

    def handle_json(self, req: _JSONRequest) -> Response | _JSONResponse:
        query = _AdminSettingsRequest()
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
                self._container.admin_settings, None, query.limit, query.offset
            )

        return _JSONResponse(
            body=_AdminSettingsResponse(
                continuation_token=continuation_token,
                total_item_count=len(self._container.admin_settings),
                items=items
            )
        )
