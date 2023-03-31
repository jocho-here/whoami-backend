from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from whoami_back.api.utils.endpoint_helpers import deprecated_endpoint
from whoami_back.api.v1.posts import base_url, commands
from whoami_back.api.v1.posts.models import CreatePostModel, UpdatePostModel
from whoami_back.api.v1.users.commands import get_current_active_user

router = APIRouter(prefix=f"{base_url}", tags=["posts_v1"])


@router.delete("/whoami/image/{post_id}")
async def delete_whoami_post_image(
    post_id: str,
    *,
    user: Dict = Depends(get_current_active_user),
):
    """
    Delete the whoami post's image. Deleting the post is done through the generic
    delete_post() function, just like other posts.
    """
    image_deleted_post = await commands.delete_whoami_post_image(post_id, user["id"])

    return {"post": image_deleted_post}


@router.post("/whoami/image")
async def create_whoami_image_post(
    title: str = Form(...),
    x: int = Form(...),
    y: int = Form(...),
    height: int = Form(...),
    width: int = Form(...),
    scale: float = Form(...),
    description: Optional[str] = Form(None),
    content_image: Optional[UploadFile] = File(None),
    user: Dict = Depends(get_current_active_user),
):
    """
    Create a whoami post - image
    """
    created_post = await commands.create_whoami_image_post(
        user["id"],
        title,
        x,
        y,
        height,
        width,
        scale,
        description=description,
        content_image=content_image,
    )

    return {"post": created_post}


@router.patch("/whoami/image/{post_id}")
async def update_whoami_image_post(
    post_id: str,
    *,
    title: Optional[str] = Form(None),
    x: Optional[int] = Form(None),
    y: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    width: Optional[int] = Form(None),
    scale: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    content_image: Optional[UploadFile] = File(None),
    user: Dict = Depends(get_current_active_user),
):
    """
    Update a whoami post - image
    """
    updated_post = await commands.update_whoami_image_post(
        post_id,
        user["id"],
        title=title,
        x=x,
        y=y,
        height=height,
        width=width,
        scale=scale,
        description=description,
        content_image=content_image,
    )

    return {"post": updated_post}


@router.get("")
async def get_posts(user: Dict = Depends(get_current_active_user)):
    """
    Return the user posts
    """
    posts = await commands.get_posts(user["id"])

    return {"posts": posts}


@router.post("")
async def create_post(
    create_post_data: CreatePostModel,
    *,
    user: Dict = Depends(get_current_active_user),
):
    """
    ### Deprecated ###
    """
    deprecated_endpoint()

    new_post = await commands.create_post(
        user["id"], create_post_data.dict(exclude_unset=True)
    )

    return {"post": new_post}


@router.patch("/{post_id}")
async def update_post(
    update_post_data: UpdatePostModel,
    post_id: str,
    *,
    user: Dict = Depends(get_current_active_user),
):
    updated_post = await commands.update_post(
        user["id"], post_id, update_post_data.dict(exclude_unset=True)
    )

    return {"post": updated_post}


@router.delete("/{post_id}")
async def delete_post(post_id, *, user: Dict = Depends(get_current_active_user)):
    await commands.delete_post(user["id"], post_id)


def add_router(app):
    app.include_router(router)
