import base64
from typing import Dict
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from starlette.datastructures import UploadFile

from whoami_back.utils.config import POST_IMAGES_S3_BUCKET
from whoami_back.utils.db import database, to_csv, to_ref_csv, to_set_statement
from whoami_back.utils.s3 import s3_client


def _delete_post_image(thumbnail_image_uri: str) -> None:
    s3_object_key = thumbnail_image_uri.split("com/")[-1]
    s3_client.delete_object(Bucket=POST_IMAGES_S3_BUCKET, Key=s3_object_key)


def _is_saved_in_whoami_s3(thumbnail_image_uri: str) -> bool:
    host = f"https://{POST_IMAGES_S3_BUCKET}.s3.amazonaws.com"

    return thumbnail_image_uri.startswith(
        host
    ) and not thumbnail_image_uri.startswith(f"{host}/default-post-images")


async def delete_post(
    user_id: str,
    post_id: str,
) -> None:
    query = """
DELETE FROM post
WHERE user_id = :user_id AND id = :post_id
RETURNING thumbnail_image_uri
    """
    values = {"post_id": post_id, "user_id": user_id}
    thumbnail_image_uri = await database.execute(query=query, values=values)

    if thumbnail_image_uri and _is_saved_in_whoami_s3(thumbnail_image_uri):
        _delete_post_image(thumbnail_image_uri)


async def update_post(
    user_id: str,
    post_id: str,
    update_post_data: Dict,
) -> Dict:
    delete_post_image = False

    if "favicon_image" in update_post_data:
        favicon_image = update_post_data.pop("favicon_image")
        update_post_data["b64_favicon"] = await _favicon_to_b64(favicon_image)

    if "post_image" in update_post_data:
        delete_post_image = True
        post_image = update_post_data.pop("post_image")

        if _is_file_empty(post_image):
            # This should never be called LOGICALLY. Instead of this,
            # thumbnail_image_uri should set as " " and post_image should not be passed.
            update_post_data["thumbnail_image_uri"] = None
        else:
            # Create a new thumbnail image and save its S3 signature
            s3_object_key = f"{user_id}/{post_id}/{uuid4()}"
            thumbnail_image_uri = (
                f"https://{POST_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
            )
            s3_client.upload_fileobj(
                post_image.file,
                POST_IMAGES_S3_BUCKET,
                s3_object_key,
                ExtraArgs={"ACL": "public-read"},
            )
            update_post_data["thumbnail_image_uri"] = thumbnail_image_uri

    set_statement = to_set_statement(update_post_data.keys())

    query = f"""
UPDATE
    post p1
SET
    {set_statement}
FROM
    post p2
WHERE
    p1.id = p2.id
    AND p1.id = :post_id
    AND p1.user_id = :user_id
RETURNING
    p2.*
    """
    result = await database.fetch_one(
        query=query,
        values={
            **update_post_data,
            "user_id": user_id,
            "post_id": post_id,
        },
    )
    result = jsonable_encoder(result)

    if (
        delete_post_image
        and result["thumbnail_image_uri"]
        and _is_saved_in_whoami_s3(result["thumbnail_image_uri"])
    ):
        _delete_post_image(result["thumbnail_image_uri"])

    result.update(update_post_data)

    return result


async def create_post(
    user_id: str,
    create_post_data: Dict,
):
    create_post_data["user_id"] = user_id

    if "favicon_image" in create_post_data:
        favicon_image = create_post_data.pop("favicon_image")
        create_post_data["b64_favicon"] = await _favicon_to_b64(favicon_image)

    if "post_image" in create_post_data:
        post_image = create_post_data.pop("post_image")
        s3_object_key = f"{user_id}/{create_post_data['id']}/{uuid4()}"
        thumbnail_image_uri = (
            f"https://{POST_IMAGES_S3_BUCKET}.s3.amazonaws.com/{s3_object_key}"
        )

        s3_client.upload_fileobj(
            post_image.file,
            POST_IMAGES_S3_BUCKET,
            s3_object_key,
            ExtraArgs={"ACL": "public-read"},
        )

        create_post_data["thumbnail_image_uri"] = thumbnail_image_uri

    insert_statement = to_csv(create_post_data.keys())
    value_statement = to_ref_csv(create_post_data.keys())

    query = f"""
INSERT INTO post ({insert_statement})
VALUES ({value_statement})
RETURNING *
    """
    result = await database.fetch_one(query=query, values=create_post_data)

    return jsonable_encoder(result)


async def _favicon_to_b64(favicon_image: UploadFile) -> bytes:
    contents = await favicon_image.read()
    base64_favicon = base64.b64encode(contents) or None

    return base64_favicon


def _is_file_empty(tempfile: UploadFile) -> bool:
    if not isinstance(tempfile, UploadFile):
        raise ValueError("tempfile is not in a file type")

    if tempfile.file.seek(0, 2) == 0:
        return True

    tempfile.file.seek(0)

    return False


async def delete_post_image(
    user_id: str,
    post_id: str,
) -> None:
    """
    ### Deprecated
    """

    query = """
UPDATE
    post p1
SET
    post_image_s3_uri = NULL
FROM
    post p2
WHERE
    p1.user_id = p2.user_id AND
    p1.user_id = :user_id AND
    p1.id = :post_id
RETURNING
    p2.post_image_s3_uri
    """
    update_post_data = {"user_id": user_id, "post_id": post_id}
    result = await database.fetch_one(query=query, values=update_post_data)

    if getattr(result, "post_image_s3_uri"):
        _delete_post_image(result.post_image_s3_uri)
