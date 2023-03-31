from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse

from whoami_back.api.v1.users import commands as users_commands_v1
from whoami_back.api.v1.users.models import UserSignUpModel
from whoami_back.api.v2.posts.resources.default_posts import get_default_posts
from whoami_back.api.v2.users import base_url, commands
from whoami_back.api.v2.users.models import UserLoginModel
from whoami_back.utils.config import LOGIN_JWT_EXPIRES_IN_HOURS
from whoami_back.utils.db import database, to_csv, to_ref_csv

router = APIRouter(prefix=f"{base_url}", tags=["users_v2"])


@router.post("/login")
async def user_login(login_credential: UserLoginModel):
    """
    User Login v2.

    One of the followings is allowed:
        1. email & password
        2. username & password
        3. email & auth_service & access_token

    If successful, return the JWT access token.
    """
    login_credential_dict = jsonable_encoder(login_credential)

    try:
        user = await commands.authenticate_user(login_credential_dict)
    except HTTPException as e:
        # Specially handling the case since we still want to commit to DB and raise
        #  the count
        if (
            hasattr(e, "detail")
            and isinstance(e.detail, dict)
            and "failed_login_attempt_count" in e.detail
        ):
            return ORJSONResponse(e.detail, status_code=401)
        else:
            raise

    access_token = await users_commands_v1.create_access_token(
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

    # Reactivate the user if he/she has been deactivated
    if not user["active"]:
        user["active"] = True
        await commands.reactivate_user(user["id"])

    return {"access_token": access_token}


@router.post("/signup")
async def user_signup(
    signup_data: UserSignUpModel, background_tasks: BackgroundTasks
) -> None:
    """
    Sign up a new user.
    If signing up using an email & a password, send a confirmation email.
    """
    signup_data_dict = jsonable_encoder(signup_data)
    user_id = await users_commands_v1.create_user(signup_data_dict)

    if signup_data.password:
        await users_commands_v1.send_confirmation_email(
            signup_data.email, user_id, background_tasks
        )

    # Create 3 default posts
    for create_post_data in get_default_posts():
        create_post_data["user_id"] = user_id
        insert_statement = to_csv(create_post_data.keys())
        value_statement = to_ref_csv(create_post_data.keys())
        query = f"""
INSERT INTO post ({insert_statement})
VALUES ({value_statement})
        """
        await database.execute(query=query, values=create_post_data)

    access_token = await users_commands_v1.create_access_token(
        user_id, LOGIN_JWT_EXPIRES_IN_HOURS
    )
    return {"access_token": access_token}


def add_router(app):
    app.include_router(router)
