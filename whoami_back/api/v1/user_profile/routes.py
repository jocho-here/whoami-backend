from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from whoami_back.api.v1.account import commands as account_commands
from whoami_back.api.v1.follow import commands as follow_commands
from whoami_back.api.v1.user_profile import base_url, commands
from whoami_back.api.v1.users import commands as user_commands

router = APIRouter(prefix=f"{base_url}", tags=["user_profile"])


@router.patch("")
async def edit_user_profile(
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
    profile_background: Optional[UploadFile] = File(None),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.edit_user_profile(
        user["id"],
        first_name=first_name,
        last_name=last_name,
        username=username,
        bio=bio,
        profile_image=profile_image,
        profile_background=profile_background,
    )


@router.delete("/profile-image")
async def delete_user_profile_image(
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.delete_user_profile_image(user["id"])


@router.delete("/profile-background")
async def delete_user_profile_background(
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.delete_user_profile_background(user["id"])


@router.get("/{username}")
async def get_user_profile(
    username: str,
    *,
    current_user: Optional[Dict] = Depends(
        user_commands.get_current_active_user_auth_optional
    ),
):
    current_user = current_user or {}
    user_profile = await commands.get_user_profile(
        username=username, current_user_id=current_user.get("id")
    )

    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    linked_profiles = await account_commands.get_linked_profiles(
        user_profile["user_id"]
    )
    follow_following_nums = await follow_commands.get_follower_following_nums(
        user_profile["user_id"]
    )

    user_profile["linked_profiles"] = linked_profiles
    user_profile.update(follow_following_nums)

    return user_profile


def add_router(app):
    app.include_router(router)
