from typing import Annotated, Union

from fastapi import Form
from fastapi.security import OAuth2PasswordRequestForm
from typing_extensions import Doc


class OAuth2PasswordWithDomainRequestForm(OAuth2PasswordRequestForm):
    """Extention of the default OAuth2PasswordRequestForm"""
    def __init__(
        self,
        *,
        grant_type: Annotated[
            Union[str, None],
            Form(pattern="password"),
            Doc(
                """
                The OAuth2 spec says it is required and MUST be the fixed string
                "password". Nevertheless, this dependency class is permissive and
                allows not passing it. If you want to enforce it, use instead the
                `OAuth2PasswordRequestFormStrict` dependency.
                """,
            ),
        ] = None,
        domain: Annotated[
            str,
            Form(),
            Doc(
                """
                `domain` string.
                """,
            ),
        ],
        username: Annotated[
            str,
            Form(),
            Doc(
                """
                `username` string. The OAuth2 spec requires the exact field name
                `username`.
                """,
            ),
        ],
        password: Annotated[
            str,
            Form(),
            Doc(
                """
                `password` string. The OAuth2 spec requires the exact field name
                `password".
                """,
            ),
        ],
        scope: Annotated[
            str,
            Form(),
            Doc(
                """
                A single string with actually several scopes separated by spaces. Each
                scope is also a string.

                For example, a single string with:

                ```python
                "items:read items:write users:read profile openid"
                ````

                would represent the scopes:

                * `items:read`
                * `items:write`
                * `users:read`
                * `profile`
                * `openid`
                """,
            ),
        ] = "",
        client_id: Annotated[
            Union[str, None],
            Form(),
            Doc(
                """
                If there's a `client_id`, it can be sent as part of the form fields.
                But the OAuth2 specification recommends sending the `client_id` and
                `client_secret` (if any) using HTTP Basic auth.
                """,
            ),
        ] = None,
        client_secret: Annotated[
            Union[str, None],
            Form(),
            Doc(
                """
                If there's a `client_password` (and a `client_id`), they can be sent
                as part of the form fields. But the OAuth2 specification recommends
                sending the `client_id` and `client_secret` (if any) using HTTP Basic
                auth.
                """,
            ),
        ] = None,
    ) -> None:
        """Initializes OAuth2PasswordWithDomainRequestForm instance"""
        super().__init__(grant_type=grant_type,
                         username=username,
                         password=password,
                         scope=scope,
                         client_id=client_id,
                         client_secret=client_secret)
        self.domain = domain
