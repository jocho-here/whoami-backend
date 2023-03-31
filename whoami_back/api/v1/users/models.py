from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, root_validator

from whoami_back.api.v1.board.models import BoardViewType


def validate_password_or_access_token(values):
    # Only password is present. Using our email & password validation flow.
    if values.get("password") and not (
        values.get("access_token") or values.get("auth_service")
    ):
        return True
    # access_token and auth_service are given. Using a 3rd party service validation flow.
    elif (
        values.get("access_token") and values.get("auth_service")
    ) and not values.get("password"):
        return True

    return False


def _get_given_auth_values(values):
    # Failed to get either password or both access_token and auth_service
    given_values = tuple(
        [
            key
            for key in ("password", "access_token", "auth_service")
            if values.get(key)
        ]
    )
    return given_values


class Confirmed(BaseModel):
    confirmed_user_email: EmailStr = Field(..., example="josephcho@gmail.com")


class Token(BaseModel):
    access_token: str = Field(
        ...,
        example="some_jwt_token",
    )


class AuthService(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"


class UserLoginModel(BaseModel):
    email: EmailStr = Field(..., example="josephcho@gmail.com")

    # When signed up using our email authentication
    password: Optional[str] = Field(example="some_secret_password")

    # When signed up using a 3rd party signup service
    access_token: Optional[str] = Field(example="some_jwt_token")
    auth_service: Optional[AuthService] = Field(example="whoami")
    service_user_id: Optional[str] = Field(example="123123123")

    @root_validator(pre=True)
    def check_password_or_access_token(cls, values):
        if validate_password_or_access_token(values):
            return values

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Required field(s) missing. "
                f"Given values: {_get_given_auth_values(values)}"
            ),
        )


class UserSignUpModel(UserLoginModel):
    first_name: str = Field(..., example="Joseph")
    last_name: str = Field(..., example="Cho")


class UserModel(BaseModel):
    id: UUID = Field(..., example="da085a8c-3970-45fb-975c-0d7e1f9fd14a")
    first_name: str = Field(..., example="Joseph")
    last_name: str = Field(..., example="Cho")
    username: str = Field(..., example="some_username")
    board_view_type: BoardViewType = Field(..., example="stack")
    email: EmailStr = Field(..., example="josephcho@gmail.com")
    created_at: datetime = Field(..., example="2020-01-01 00:00:00+00")
    updated_at: datetime = Field(..., example="2020-01-01 00:00:00+00")
    public: bool = Field(..., example=True)
    confirmed: bool = Field(..., example=False)
    active: bool = Field(..., example=True)

    unconfirmed_new_email: Optional[EmailStr] = Field(example="josephcho@gmail.com")


class UserWithProfileModel(UserModel):
    bio: Optional[str] = Field(example="some_bio")
    profile_image_s3_uri: Optional[str] = Field(example="some_s3_uri")
    profile_background_s3_uri: Optional[str] = Field(example="some_s3_uri")
    auth_service: Optional[str] = Field(example="google")
