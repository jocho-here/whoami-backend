from typing import Dict, Optional
from uuid import uuid4

# import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status

from whoami_back.api.utils.endpoint_helpers import deprecated_endpoint
from whoami_back.api.v1.notifications.resources.actions import actions_data
from whoami_back.api.v1.users.commands import get_current_active_user
from whoami_back.api.v2.posts import base_url, commands
from whoami_back.api.v2.posts.models import PostResponse

# from whoami_back.utils.config import TASK_QUEUE_HOST
from whoami_back.utils.models import exclude_unset, nullify_text_columns

router = APIRouter(prefix=f"{base_url}", tags=["posts_v2"])
POPULATE_NOTIFICATION_ENDPOINT = "/api/tasks/populate-notifications"
SHARED_A_NEW_POST_ACTION_ID = actions_data[3]["id_3"]


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    *,
    user: Dict = Depends(get_current_active_user),
):
    await commands.delete_post(user["id"], post_id)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    *,
    x: Optional[int] = Form(None),
    y: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    width: Optional[int] = Form(None),
    scale: Optional[float] = Form(None),
    favicon_image: Optional[UploadFile] = Form(None),
    content_uri: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    post_image: Optional[UploadFile] = Form(None),
    thumbnail_image_uri: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user: Dict = Depends(get_current_active_user),
):
    """
    ONLY accept either thumbnail_image_uri OR post_image.
    """
    update_post_data = exclude_unset(
        {
            "x": x,
            "y": y,
            "height": height,
            "width": width,
            "scale": scale,
            "post_image": post_image,
            "favicon_image": favicon_image,
            "content_uri": content_uri,
            "source": source,
            "thumbnail_image_uri": thumbnail_image_uri,
            "title": title,
            "description": description,
        }
    )
    update_post_data = nullify_text_columns(update_post_data)

    if (
        "thumbnail_image_uri" in update_post_data
        and "post_image" in update_post_data
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update request contains both post_image and thumbnail_image_uri",
        )

    updated_post = await commands.update_post(user["id"], post_id, update_post_data)

    return {"post": updated_post}


@router.post("", response_model=PostResponse)
async def create_post(
    x: int = Form(...),
    y: int = Form(...),
    height: int = Form(...),
    width: int = Form(...),
    scale: float = Form(...),
    *,
    post_image: Optional[UploadFile] = Form(None),
    favicon_image: Optional[UploadFile] = Form(None),
    content_uri: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    thumbnail_image_uri: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user: Dict = Depends(get_current_active_user),
):
    if not (
        post_image
        or favicon_image
        or content_uri
        or thumbnail_image_uri
        or title
        or description
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creating a post requires one or more items",
        )
    elif (content_uri is None) != (source is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content_uri and source should either be both present or both absent",
        )

    create_post_data = exclude_unset(
        {
            "id": str(uuid4()),
            "x": x,
            "y": y,
            "height": height,
            "width": width,
            "scale": scale,
            "post_image": post_image,
            "favicon_image": favicon_image,
            "content_uri": content_uri,
            "source": source,
            "thumbnail_image_uri": thumbnail_image_uri,
            "title": title,
            "description": description,
        }
    )

    created_post = await commands.create_post(user["id"], create_post_data)

    # Populate followers notification
    """
    try:
        populate_uri = TASK_QUEUE_HOST + POPULATE_NOTIFICATION_ENDPOINT
        async with httpx.AsyncClient() as client:
            data = {
                "triggering_user_id": user["id"],
                "action_id": SHARED_A_NEW_POST_ACTION_ID,
            }
            await client.post(populate_uri, json=data, timeout=None)
    except Exception as e:
        print(f"Could not find the Task Queue probably! Error: {str(e)}")
    """

    return {"post": created_post}


@router.delete("/image/{post_id}")
async def delete_post_image(
    post_id: str,
    *,
    user: Dict = Depends(get_current_active_user),
):
    """
    ### Deprecated
    """
    deprecated_endpoint()

    await commands.delete_post_image(user["id"], post_id)


def add_router(app):
    app.include_router(router)
