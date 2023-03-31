from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder

from whoami_back.api.v1.follow.commands import determine_following_status
from whoami_back.api.v1.utils.commands import validate_username
from whoami_back.utils.config import PROFILE_IMAGES_S3_BUCKET
from whoami_back.utils.db import database, to_csv, to_set_statement
from whoami_back.utils.s3 import s3_client


async def delete_user_profile_image(user_id: str) -> None:
    query = """
SELECT profile_image_s3_uri
FROM "user"
WHERE id = :user_id
    """
    profile_image_s3_uri = await database.execute(
        query=query, values={"user_id": user_id}
    )

    if profile_image_s3_uri:
        s3_object_key = profile_image_s3_uri.split(".com/")[-1]
        s3_client.delete_object(Bucket=PROFILE_IMAGES_S3_BUCKET, Key=s3_object_key)

    query = """
UPDATE "user"
SET
    profile_image_s3_uri = NULL,
    updated_at = NOW()
WHERE id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})


async def delete_user_profile_background(user_id: str) -> None:
    query = """
SELECT profile_background_s3_uri
FROM "user"
WHERE id = :user_id
    """
    profile_background_s3_uri = await database.execute(
        query=query, values={"user_id": user_id}
    )

    if profile_background_s3_uri:
        s3_object_key = profile_background_s3_uri.split(".com/")[-1]
        s3_client.delete_object(Bucket=PROFILE_IMAGES_S3_BUCKET, Key=s3_object_key)

    query = """
UPDATE "user"
SET
    profile_background_s3_uri = NULL,
    updated_at = NOW()
WHERE id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})


async def get_user_profile(
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    current_user_id: Optional[str] = None,
) -> None:
    params = {}
    select_keys = [
        '"user".id AS user_id',
        '"user".username',
        '"user".first_name',
        '"user".last_name',
        '"user".bio',
        '"user".profile_image_s3_uri',
        '"user".profile_background_s3_uri',
        '"user".unconfirmed_new_email',
    ]

    if user_id:
        where_clause = "id = :user_id"
        params["user_id"] = user_id
    elif username:
        where_clause = "username = :username"
        params["username"] = username

    # If we received current_user_id, we check if this user in the token is
    #  following the target user
    left_join_clause = ""
    if current_user_id:
        left_join_clause = """
LEFT JOIN follow
ON follow.followed_user_id = "user".id
AND follow.following_user_id = :current_user_id
        """
        params["current_user_id"] = current_user_id
        select_keys.append("follow.approved")

    select_statement = to_csv(select_keys)
    query = f"""
SELECT {select_statement}
FROM "user"
{left_join_clause}
WHERE {where_clause}
    """
    user_profile = await database.fetch_one(query=query, values=params)
    user_profile = jsonable_encoder(user_profile)

    if current_user_id and user_profile:
        user_profile["current_user_following_status"] = determine_following_status(
            user_profile.pop("approved", None)
        )

    return user_profile


async def edit_user_profile(
    user_id: str,
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    bio: Optional[str] = None,
    profile_image: Optional[UploadFile] = None,
    profile_background: [UploadFile] = None,
) -> None:
    user_object_updates = {}

    if username:
        valid, reason = await validate_username(username)

        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=reason
            )

        user_object_updates["username"] = username

    if first_name:
        user_object_updates["first_name"] = first_name

    if last_name:
        user_object_updates["last_name"] = last_name

    if len(user_object_updates):
        set_statement = to_set_statement(user_object_updates.keys())
        query = f"""
UPDATE \"user\"
SET {set_statement}
WHERE id = :user_id
        """
        user_object_updates["user_id"] = user_id
        await database.execute(query=query, values=user_object_updates)

    user_profile_object_updates = {}

    if profile_image:
        s3_object_key = f"profile_image/{user_id}/{uuid4()}"
        profile_image_s3_uri = (
            f"https://{PROFILE_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
        )
        s3_client.upload_fileobj(
            profile_image.file,
            PROFILE_IMAGES_S3_BUCKET,
            s3_object_key,
            ExtraArgs={"ACL": "public-read"},
        )
        user_profile_object_updates["profile_image_s3_uri"] = profile_image_s3_uri

    if profile_background:
        s3_object_key = f"profile_background/{user_id}/{uuid4()}"
        profile_background_s3_uri = (
            f"https://{PROFILE_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
        )
        s3_client.upload_fileobj(
            profile_background.file,
            PROFILE_IMAGES_S3_BUCKET,
            s3_object_key,
            ExtraArgs={"ACL": "public-read"},
        )
        user_profile_object_updates[
            "profile_background_s3_uri"
        ] = profile_background_s3_uri

    if isinstance(bio, str):
        if bio == " ":
            bio = ""

        user_profile_object_updates["bio"] = bio

    if len(user_profile_object_updates):
        set_statement = to_set_statement(user_profile_object_updates.keys())
        query = f"""
UPDATE "user"
SET {set_statement}
WHERE id = :user_id
        """
        user_profile_object_updates["user_id"] = user_id
        await database.execute(query=query, values=user_profile_object_updates)
