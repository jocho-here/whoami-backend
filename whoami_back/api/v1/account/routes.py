from typing import Dict

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr

from whoami_back.api.v1.account import base_url, commands
from whoami_back.api.v1.account.models import UpdateLinkedProfilesModel
from whoami_back.api.v1.users import commands as user_commands

router = APIRouter(prefix=f"{base_url}", tags=["account"])


@router.patch("/privacy")
async def update_account_prviacy(
    public: bool = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.update_account_privacy(user["id"], public)


@router.get("/linked-profiles")
async def get_linked_profiles(
    user: Dict = Depends(user_commands.get_current_active_user),
):
    linked_profiles = await commands.get_linked_profiles(user["id"])

    return linked_profiles


@router.post("/linked-profiles")
async def update_linked_profiles(
    linked_profiles: UpdateLinkedProfilesModel,
    *,
    user: Dict = Depends(user_commands.get_current_active_user),
):
    body_dict = jsonable_encoder(linked_profiles)
    await commands.update_linked_profiles(user["id"], body_dict["linked_profiles"])


@router.delete("")
async def delete_account_with_password(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(user_commands.get_current_active_user_with_password),
    password: str = Body(..., embed=True),
):
    commands.confirm_password(password, user["password"])

    await commands.delete_user(user["id"])
    commands.send_account_deleted_email(user["email"], background_tasks)


@router.patch("/deactivate")
async def deactivate_account_with_password(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(user_commands.get_current_active_user_with_password),
    password: str = Body(..., embed=True),
):
    commands.confirm_password(password, user["password"])

    await commands.deactivate_user(user["id"])
    commands.send_account_deactivated_email(user["email"], background_tasks)


@router.get("/send-delete-confirmation")
async def send_delete_confirmation(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(user_commands.get_current_active_user),
):
    """
    This endpoint sends a confirmation email to delete the account only to be used
      by 3rd party OAuth users
    """
    await commands.send_delete_account_confirmation_email(
        user["id"], user["email"], background_tasks
    )


@router.get("/send-deactivate-confirmation")
async def send_deactivate_confirmation(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(user_commands.get_current_active_user),
):
    """
    This endpoint sends a confirmation email to deactivate the account only to be
      used by 3rd party OAuth users
    """
    await commands.send_deactivate_account_confirmation_email(
        user["id"], user["email"], background_tasks
    )


@router.delete("/delete-without-password")
async def delete_account_without_password(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(user_commands.get_current_active_user_with_password),
):
    await commands.delete_user(user["id"])
    commands.send_account_deleted_email(user["email"], background_tasks)


@router.patch("/deactivate-without-password")
async def deactivate_account_without_password(
    background_tasks: BackgroundTasks,
    user: Dict = Depends(user_commands.get_current_active_user_with_password),
):
    await commands.deactivate_user(user["id"])
    commands.send_account_deactivated_email(user["email"], background_tasks)


@router.patch("/email")
async def initiate_email_update(
    background_tasks: BackgroundTasks,
    new_email: EmailStr = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.initiate_email_update(user["id"], user["email"], new_email)
    await user_commands.send_new_email_confirmation_email(
        new_email, user["id"], background_tasks
    )


@router.patch("/confirm-new-email")
async def confirm_new_email(
    confirmed_new_email: EmailStr = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    if user["unconfirmed_new_email"] != confirmed_new_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unconfirmed new email address ({user['unconfirmed_new_email']}) does not match with the given confirmed new email address ({confirmed_new_email}).",
        )

    try:
        await commands.confirm_new_email(user["id"])
    except UniqueViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/cancel-email-update")
async def cancel_email_update(
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.cancel_email_update(user["id"])


@router.patch("/update-password")
async def update_password(
    old_password: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user_with_password),
):
    """
    This is updating password from the settings
    """
    commands.confirm_password(old_password, user["password"])

    await commands.update_password(user["id"], new_password)


@router.patch("/reset-password")
async def reset_password(
    new_password: str = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    """
    This is changing the password when lost
    """
    await commands.update_password(user["id"], new_password)


@router.post("/confirm-password")
async def confirm_password(
    password: str = Body(..., embed=True),
    user: Dict = Depends(user_commands.get_current_active_user_with_password),
):
    commands.confirm_password(password, user["password"])


def add_router(app):
    app.include_router(router)
