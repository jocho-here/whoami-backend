from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, root_validator

from whoami_back.api.v1.users.models import (
    AuthService,
    validate_password_or_access_token,
)


class UserLoginModel(BaseModel):
    """
    User Login v2.

    One of the followings is allowed:
        1. email & password
        2. username & password
        3. email & auth_service & access_token
    """

    email: Optional[EmailStr] = Field()
    username: Optional[str] = Field()

    password: Optional[str] = Field()

    access_token: Optional[str] = Field()
    auth_service: Optional[AuthService] = Field()
    service_user_id: Optional[str] = Field()

    @root_validator(pre=True)
    def check_login_credential_validty(cls, values):
        if (
            values.get("email")
            and not values.get("username")
            and validate_password_or_access_token(values)
        ):
            return values

        if (
            values.get("username")
            and not values.get("email")
            and values.get("password")
        ):
            return values

        given_values = tuple([key for key in values if values[key]])

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Required field(s) missing. Given values: {given_values}",
        )
