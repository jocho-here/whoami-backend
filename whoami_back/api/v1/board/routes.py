from typing import Dict, Optional

from asyncpg.exceptions import CheckViolationError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic.color import Color

from whoami_back.api.v1.board import base_url, commands
from whoami_back.api.v1.board.models import (
    BoardBackgroundImageFittingMode,
    BoardBackgroundModel,
    BoardViewType,
)
from whoami_back.api.v1.follow.commands import check_approved_following
from whoami_back.api.v1.posts import commands as post_commands
from whoami_back.api.v1.users import commands as user_commands
from whoami_back.utils.db import database

router = APIRouter(prefix=base_url, tags=["board_v1"])


@router.delete("/background/image")
async def delete_board_background_image(
    user: Dict = Depends(user_commands.get_current_active_user),
):
    await commands.delete_board_background_image(user["id"])


@router.patch("/background", response_model=BoardBackgroundModel)
async def update_board_background(
    background_image: Optional[UploadFile] = File(None),
    background_image_fitting_mode: Optional[BoardBackgroundImageFittingMode] = Form(
        None
    ),
    background_hex_color: Optional[Color] = Form(None),
    user: Dict = Depends(user_commands.get_current_active_user),
):
    try:
        updated_background = await commands.update_board_background(
            user["id"],
            background_image=background_image,
            background_image_fitting_mode=background_image_fitting_mode,
            background_hex_color=str(background_hex_color),
        )
    except CheckViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return updated_background


@router.get("/{username}")
async def get_board(
    username: str,
    *,
    board_view_type: Optional[BoardViewType] = None,
    current_user: Optional[Dict] = Depends(
        user_commands.get_current_active_user_auth_optional
    ),
):
    """
    Return the user board. If user is not found, we assume it's either unauthorized
    or inactive user OR no JWT token given (public access)
    """
    # Check if the username exists
    target_user = await user_commands.get_user(username=username)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with the given username ({username}) does not exist",
        )

    # Check if the target user is active
    if not target_user["active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with the given username ({username}) is not active",
        )

    # Check if the target user account is private
    if not target_user["public"]:
        if not current_user:
            # Non-user trying to look at a private account
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif current_user["id"] != target_user[
            "id"
        ] and not await check_approved_following(
            current_user["id"], target_user["id"]
        ):
            # Requires the current user to be an authorized follower
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not an approved follower of the target user",
            )

    if not board_view_type:
        if current_user:
            query = """
SELECT board_view_type
FROM board
WHERE user_id = :user_id
            """
            board_view_type = await database.execute(
                query=query, value={"user_id": current_user["id"]}
            )
        else:
            # Default
            board_view_type = BoardViewType.BOARD

    # Either public OR private but passed the tests above
    posts = await post_commands.get_posts(
        target_user["id"], board_view_type=board_view_type
    )

    return {"posts": posts}


def add_router(app):
    app.include_router(router)
