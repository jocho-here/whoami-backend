from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr

from whoami_back.api.utils.endpoint_helpers import deprecated_endpoint
from whoami_back.api.v1.posts import commands as post_commands
from whoami_back.api.v1.posts.resources.default_posts import get_default_posts
from whoami_back.api.v1.user_profile import commands as user_profile_commands
from whoami_back.api.v1.users import base_url, commands
from whoami_back.api.v1.users.models import (
    Confirmed,
    Token,
    UserLoginModel,
    UserSignUpModel,
    UserWithProfileModel,
)
from whoami_back.utils.config import LOGIN_JWT_EXPIRES_IN_HOURS

router = APIRouter(prefix=f"{base_url}", tags=["users_v1"])


@router.post("/send-password-reset")
async def send_password_reset_email(
    background_tasks: BackgroundTasks, email: EmailStr = Body(..., embed=True)
):
    user = await commands.get_user(email=email, get_password=True)

    # Do not return an error even when there was no user found
    if user and user["password"]:
        await commands.send_password_reset_email(email, user["id"], background_tasks)


@router.get("/resend-confirmation")
async def resend_confirmation_email(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(commands.get_current_unconfirmed_active_user),
) -> None:
    await commands.send_confirmation_email(
        user["email"], user["id"], background_tasks
    )


@router.get("/confirm", response_model=Confirmed)
async def confirm_user(
    user: Dict = Depends(commands.get_current_unconfirmed_active_user),
) -> Dict:
    confirmed_user_email = await commands.confirm_user(user)

    return {"confirmed_user_email": confirmed_user_email}


@router.post("/signup")
async def user_signup(
    signup_data: UserSignUpModel, background_tasks: BackgroundTasks
) -> None:
    """
    ### Deprecated ###

    Sign up a new user.
    If signing up using an email & a password, send a confirmation email.
    """
    deprecated_endpoint()

    signup_data_dict = jsonable_encoder(signup_data)
    user_id = await commands.create_user(signup_data_dict)

    if signup_data.password:
        await commands.send_confirmation_email(
            signup_data.email, user_id, background_tasks
        )

    # Create 3 default posts
    for create_post_data in get_default_posts():
        await post_commands.create_post(user_id, create_post_data)

    access_token = await commands.create_access_token(
        user_id, LOGIN_JWT_EXPIRES_IN_HOURS
    )
    return {"access_token": access_token}


@router.post("/login", response_model=Token)
async def user_login(login_credential: UserLoginModel) -> Token:
    """
    ### Deprecated ###

    Try to login a user using the given email and either password or
    access_token & auth_service.
    If successful, return the access token (JWT).
    """
    deprecated_endpoint()

    login_credential_dict = jsonable_encoder(login_credential)
    user = await commands.authenticate_user(login_credential_dict)

    access_token = await commands.create_access_token(
        user["id"], LOGIN_JWT_EXPIRES_IN_HOURS
    )

    if not user["confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "User confirmation required",
                "access_token": access_token,
            },
        )
    elif not user["active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Inactive user", "access_token": access_token},
        )

    return {"access_token": access_token}


@router.get("", response_model=UserWithProfileModel)
async def get_user(
    user: Dict = Depends(commands.get_current_active_user_with_password),
):
    """
    Gets JWT, confirms it and returns the user with user_profile data.
    """
    user_profile = await user_profile_commands.get_user_profile(user["id"])
    user.update(user_profile)

    if user.get("auth_attributes"):
        user["auth_service"] = user["auth_attributes"]["auth_service"]

    return user


def add_router(app):
    app.include_router(router)
