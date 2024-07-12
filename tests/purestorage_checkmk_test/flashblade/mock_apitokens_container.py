import dataclasses
import time
import typing
import uuid


@dataclasses.dataclass
class APITokenObject:
    created_at: int
    token: str
    expires_at: typing.Optional[int] = None


@dataclasses.dataclass
class APITokenAdmin:
    id: str
    name: str
    resource_type: str


@dataclasses.dataclass
class APIToken:
    admin: APITokenAdmin
    api_token: APITokenObject


class APITokensContainer:
    api_tokens: typing.List[APIToken]

    def __init__(self, api_tokens: typing.Set[str]):
        self.api_tokens = []
        i = 0
        for token in api_tokens:
            i += 1
            self.api_tokens.append(
                APIToken(
                    APITokenAdmin(
                        name="pureuser",
                        resource_type="admins",
                        id=uuid.uuid4().__str__(),
                    ),
                    APITokenObject(
                        created_at=int(time.time()),
                        token=token,
                    )
                )
            )

    def __contains__(self, item):
        for token in self.api_tokens:
            if token.api_token.token == item:
                return True
        return False
