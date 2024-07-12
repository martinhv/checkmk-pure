import dataclasses
import time
import typing


@dataclasses.dataclass
class APITokenObject:
    created_at: int
    expires_at: typing.Optional[int] = None
    token: typing.Optional[str] = None


@dataclasses.dataclass
class APIToken:
    name: str
    api_token: APITokenObject


class APITokensContainer:
    api_tokens: typing.List[APIToken] = []

    def __init__(self, api_tokens: typing.Set[str]):
        self.api_tokens = []
        i = 0
        for token in api_tokens:
            i += 1
            self.api_tokens.append(
                APIToken(
                    f"token_{i}",
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
