from typing import Dict, Optional
from uuid import uuid4

import httpx
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder

from whoami_back.api.v1.board.models import BoardViewType
from whoami_back.api.v1.posts.models import CreatePostModel, UpdatePostModel
from whoami_back.utils.config import (
    POST_IMAGES_S3_BUCKET,
    POST_THUMBNAIL_IMAGES_S3_BUCKET,
)
from whoami_back.utils.db import database, to_csv, to_ref_csv, to_set_statement
from whoami_back.utils.s3 import s3_client


async def delete_whoami_post_image(
    post_id: str,
    user_id: str,
):
    query = """
SELECT content_uri
FROM post
WHERE user_id = :user_id AND id = :post_id
    """
    values = {"post_id": post_id, "user_id": user_id}
    content_uri = await database.execute(query=query, values=values)

    if content_uri:
        s3_object_key = content_uri.split("com/")[-1]
        s3_client.delete_object(Bucket=POST_IMAGES_S3_BUCKET, Key=s3_object_key)

    returning_statement = to_csv(CreatePostModel.__fields__.keys())
    query = f"""
UPDATE post
SET
    content_uri = NULL,
    thumbnail_image_uri = NULL,
    updated_at = NOW()
WHERE user_id = :user_id AND id = :post_id
RETURNING id, {returning_statement}
    """
    result = await database.fetch_one(query=query, values=values)

    return jsonable_encoder(result)


async def update_whoami_image_post(
    post_id: str,
    user_id: str,
    *,
    title: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    height: Optional[int] = None,
    width: Optional[int] = None,
    scale: Optional[float] = None,
    description: Optional[str] = None,
    content_image: Optional[UploadFile] = None,
):
    update_data = {
        "title": title,
        "x": x,
        "y": y,
        "height": height,
        "width": width,
        "scale": scale,
        "description": description,
    }

    update_post_data = {
        k: update_data[k] for k in update_data if update_data[k] is not None
    }

    if content_image:
        # This content_uri setting mechanism is to trigger React
        query = """
SELECT content_uri
FROM post
WHERE user_id = :user_id AND id = :post_id
        """
        values = {
            "user_id": user_id,
            "post_id": post_id,
        }
        content_uri = await database.execute(query=query, values=values)

        if content_uri:
            s3_object_key = content_uri.split("com/")[-1]
            s3_client.delete_object(Bucket=POST_IMAGES_S3_BUCKET, Key=s3_object_key)

        s3_object_key = f"{user_id}/{post_id}/{uuid4()}"

        content_image_s3_uri = (
            f"https://{POST_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
        )
        s3_client.upload_fileobj(
            content_image.file,
            POST_IMAGES_S3_BUCKET,
            s3_object_key,
            ExtraArgs={"ACL": "public-read"},
        )
        update_post_data["content_uri"] = content_image_s3_uri
        update_post_data["thumbnail_image_uri"] = content_image_s3_uri

    set_statement = to_set_statement(update_post_data.keys())
    returning_statement = to_csv(UpdatePostModel.__fields__.keys())

    query = f"""
UPDATE post
SET {set_statement}
WHERE user_id = :user_id AND id = :post_id
RETURNING id, {returning_statement}
    """
    update_post_data["user_id"] = user_id
    update_post_data["post_id"] = post_id
    result = await database.fetch_one(query=query, values=update_post_data)

    return jsonable_encoder(result)


async def create_whoami_image_post(
    user_id: str,
    title: str,
    x: int,
    y: int,
    height: int,
    width: int,
    scale: float,
    *,
    description: Optional[str] = None,
    content_image: Optional[UploadFile] = None,
):
    create_post_data = {
        "id": str(uuid4()),
        "user_id": user_id,
        "source": "whoami",
        "title": title,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "scale": scale,
    }

    if description:
        create_post_data["description"] = description

    if content_image:
        s3_object_key = f"{user_id}/{create_post_data['id']}/{uuid4()}"
        content_image_s3_uri = (
            f"https://{POST_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
        )
        s3_client.upload_fileobj(
            content_image.file,
            POST_IMAGES_S3_BUCKET,
            s3_object_key,
            ExtraArgs={"ACL": "public-read"},
        )
        create_post_data["content_uri"] = content_image_s3_uri
        create_post_data["thumbnail_image_uri"] = content_image_s3_uri

    insert_statement = to_csv(create_post_data.keys())
    value_statement = to_ref_csv(create_post_data.keys())
    returning_statement = to_csv(CreatePostModel.__fields__.keys())

    query = f"""
INSERT INTO post ({insert_statement})
VALUES ({value_statement})
RETURNING id, {returning_statement}
    """
    result = await database.fetch_one(query=query, values=create_post_data)

    return jsonable_encoder(result)


async def get_posts(user_id: str, *, board_view_type: BoardViewType = None):
    order_by_statement = ""

    if board_view_type == BoardViewType.BOARD:
        order_by_statement = "ORDER BY updated_at ASC"
    elif board_view_type == BoardViewType.STACK:
        order_by_statement = "ORDER BY created_at DESC"

    query = f"""
SELECT * FROM post
WHERE user_id = :user_id
{order_by_statement}
    """
    posts = await database.fetch_all(query=query, values={"user_id": user_id})

    return jsonable_encoder(posts)


async def create_post(user_id: str, create_post_data: Dict):
    create_post_data["id"] = str(uuid4())
    create_post_data["user_id"] = user_id
    thumbnail_image_uri = None

    if "thumbnail_image_uri" in create_post_data:
        async with httpx.AsyncClient() as client:
            result = await client.get(create_post_data.pop("thumbnail_image_uri"))
            thumbnail_image_in_bytes = result.content
            s3_object_key = f'{user_id}/{create_post_data["id"]}'
            thumbnail_image_uri = f"https://{POST_THUMBNAIL_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
            s3_client.put_object(
                Bucket=POST_THUMBNAIL_IMAGES_S3_BUCKET,
                Key=s3_object_key,
                Body=thumbnail_image_in_bytes,
                ACL="public-read",
            )

    create_post_data["thumbnail_image_uri"] = thumbnail_image_uri
    insert_statement = to_csv(create_post_data.keys())
    value_statement = to_ref_csv(create_post_data.keys())
    query = f"""
INSERT INTO post ({insert_statement})
VALUES ({value_statement})
    """
    await database.execute(query=query, values=create_post_data)

    create_post_data["source"] = create_post_data["source"].value
    create_post_data.pop("user_id", None)

    return create_post_data


async def update_post(user_id: str, post_id: str, update_post_data: Dict):
    set_statement = to_set_statement(update_post_data.keys())
    returning_statement = to_csv(UpdatePostModel.__fields__.keys())
    query = f"""
UPDATE post
SET {set_statement}
WHERE user_id = :user_id AND id = :post_id
RETURNING id, {returning_statement}
    """
    update_post_data["user_id"] = user_id
    update_post_data["post_id"] = post_id
    result = await database.fetch_one(query=query, values=update_post_data)

    return jsonable_encoder(result)


async def delete_post(user_id: str, post_id: str):
    query = """
DELETE FROM post
WHERE user_id = :user_id AND id = :post_id
    """
    values = {"user_id": user_id, "post_id": post_id}
    await database.execute(query=query, values=values)
