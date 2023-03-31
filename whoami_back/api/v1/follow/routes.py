from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from whoami_back.api.v1.follow import base_url, commands
from whoami_back.api.v1.users import commands as user_commands

router = APIRouter(prefix=base_url, tags=["follow"])


async def _get_confirmed_active_user(user_id: str, id_name: str) -> Dict:
    user = await user_commands.get_user(user_id=user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user with {id_name} not found",
        )

    if not user["confirmed"] or not user["active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user with {id_name} is inactive or not confirmed",
        )

    return user


@router.get("/{followed_user_id}/followers")
async def get_followers(
    followed_user_id: str,
    *,
    current_user: Dict = Depends(user_commands.get_current_active_user),
):
    # Check if the user with the followed_user_id is confirmed and active
    _ = await _get_confirmed_active_user(followed_user_id, "followed_user_id")
    followers = await commands.get_followers(followed_user_id, current_user["id"])

    return {"followers": followers}


@router.get("/{following_user_id}/following")
async def get_followed_users(
    following_user_id: str,
    *,
    current_user: Dict = Depends(user_commands.get_current_active_user),
):
    # Check if the user with the following_user_id is confirmed and active
    _ = await _get_confirmed_active_user(following_user_id, "following_user_id")
    followed_users = await commands.get_followed_users(
        following_user_id, current_user["id"]
    )

    return {"following": followed_users}


@router.post("/{followed_user_id}/follow")
async def follow_user(
    followed_user_id: str,
    *,
    current_user: Dict = Depends(user_commands.get_current_active_user),
):
    """
    Current user wants to follow the user with followed_user_id.
    """
    # Check if the user with the followed_user_id is confirmed and active
    followed_user = await _get_confirmed_active_user(
        followed_user_id, "followed_user_id"
    )

    await commands.follow_user(
        current_user["id"], followed_user_id, followed_user["public"]
    )


@router.delete("/{unfollowed_user_id}/unfollow")
async def unfollow_user(
    unfollowed_user_id: str,
    *,
    current_user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.delete_follow(current_user["id"], unfollowed_user_id)


@router.delete("/remove-follower/{removed_follower_user_id}")
async def remove_follower(
    removed_follower_user_id: str,
    *,
    current_user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.delete_follow(removed_follower_user_id, current_user["id"])


@router.patch("/approve/{following_user_id}")
async def approve_following(
    following_user_id: str,
    *,
    current_user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.approve_following(following_user_id, current_user["id"])


@router.get("/follow-requests")
async def get_follow_requests(
    user: Dict = Depends(user_commands.get_current_active_user),
):
    follow_requests = await commands.get_follow_requests(user["id"])

    return {"follow_requests": follow_requests}


def add_router(app):
    app.include_router(router)
