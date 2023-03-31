from typing import Dict

from fastapi import HTTPException, status

from whoami_back.api.v1.users import commands as users_commands_v1
from whoami_back.utils.config import (  # noqa: F401
    ADMIN_EMAIL,
    CONFIRMATION_JWT_EXPIRES_IN_HOURS,
    GOOGLE_CLIENT_ID,
    JWT_ALGORITHM,
    JWT_SIGNATURE,
    PASSWORD_RESET_JWT_EXPIRES_IN_HOURS,
    SENDGRID_API_KEY,
)
from whoami_back.utils.db import database


async def authenticate_user(login_credential: Dict):
    get_user_kwargs = {
        "email": login_credential.get("email"),
        "username": login_credential.get("username"),
        "get_password": True,
    }
    user = await users_commands_v1.get_user(**get_user_kwargs)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user found with the given credentials",
        )

    # Login using password
    if login_credential.get("password"):
        # Check if the user exists with 3rd party authentication
        if not user.get("password"):
            auth_service = user["auth_attributes"]["auth_service"].capitalize()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User signed up with {auth_service} OAuth",
            )

        # If failed 5 times already, let FE know that the account has been locked
        if user["failed_login_attempt_count"] >= 5:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed login attempts",
            )

        if not users_commands_v1.verify_password(
            login_credential["password"], user["password"]
        ):
            new_failed_attempt_count = (
                await users_commands_v1.increment_failed_login_attempt(user["id"])
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"failed_login_attempt_count": new_failed_attempt_count},
            )

        await users_commands_v1.reset_failed_login_attempt(user["id"])

    # Login using the access_token and auth_service
    if login_credential.get("access_token") and login_credential.get("auth_service"):
        if not user.get("auth_attributes"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User signed up with password",
            )

        new_auth_attributes = users_commands_v1.validate_access_token(
            login_credential["service_user_id"],
            login_credential["email"],
            login_credential["access_token"],
            login_credential["auth_service"],
            target_auth_attributes=user["auth_attributes"],
        )

        # update the user.auth_attributes
        query = """
UPDATE
    \"user\"
SET
    auth_attributes = :new_auth_attributes,
    updated_at = NOW()
WHERE
    id = :user_id
        """
        values = {
            "new_auth_attributes": new_auth_attributes,
            "user_id": user["id"],
        }
        await database.execute(query=query, values=values)

    return user


async def reactivate_user(user_id: str) -> None:
    query = """
UPDATE \"user\"
SET
    active = TRUE,
    updated_at = NOW()
WHERE id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})
