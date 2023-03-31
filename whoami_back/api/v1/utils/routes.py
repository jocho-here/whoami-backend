from typing import Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import EmailStr

from whoami_back.api.v1.users import commands as user_commands
from whoami_back.api.v1.utils import base_url, commands

router = APIRouter(prefix=f"{base_url}", tags=["utils"])


@router.post("/validate/username")
async def validate_username(
    username: str = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    # Check if the given username is available and in a valid form
    valid, reason = await commands.validate_username(
        username, current_user_username=user["username"]
    )

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)


@router.post("/validate/email")
async def validate_email(
    email: EmailStr = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    # Check if the given email is available
    valid, reason = await commands.validate_email(
        email, current_user_email=user["email"]
    )

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)


def add_router(app):
    app.include_router(router)
