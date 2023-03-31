from typing import Dict, Optional
from uuid import uuid4

from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder

from whoami_back.api.v1.board.models import BoardBackgroundImageFittingMode
from whoami_back.utils.config import BOARD_IMAGES_S3_BUCKET
from whoami_back.utils.db import database, to_set_statement
from whoami_back.utils.models import exclude_unset, nullify_text_columns
from whoami_back.utils.s3 import get_s3_object_uri, s3_client


async def get_board_background(user_id: str) -> Dict:
    query = """
SELECT background_image_s3_uri, background_image_fitting_mode, background_hex_color
FROM board
WHERE user_id = :user_id
    """
    result = await database.fetch_one(query=query, values={"user_id": user_id})

    return jsonable_encoder(result)


async def delete_board_background_image(user_id: str) -> None:
    query = """
UPDATE
    board b1
SET
    background_image_s3_uri = NULL,
    background_image_fitting_mode = NULL,
    updated_at = NOW()
FROM
    board b2
WHERE
    b1.user_id = b2.user_id
    AND b1.user_id = :user_id
RETURNING
    b2.background_image_s3_uri,
    b2.background_image_fitting_mode
    """
    result = await database.fetch_one(query=query, values={"user_id": user_id})

    if result["background_image_s3_uri"]:
        s3_object_key = result["background_image_s3_uri"].split("com/")[-1]
        s3_client.delete_object(Bucket=BOARD_IMAGES_S3_BUCKET, Key=s3_object_key)


async def update_board_background(
    user_id: str,
    *,
    background_image: Optional[UploadFile] = None,
    background_image_fitting_mode: Optional[BoardBackgroundImageFittingMode] = None,
    background_hex_color: Optional[str] = None,
) -> Dict:
    background_image_s3_uri = None

    if background_image:
        s3_object_key = f"background_image/{user_id}/{uuid4()}"
        background_image_s3_uri = get_s3_object_uri(
            BOARD_IMAGES_S3_BUCKET, s3_object_key
        )
        s3_client.upload_fileobj(
            background_image.file,
            BOARD_IMAGES_S3_BUCKET,
            s3_object_key,
            ExtraArgs={"ACL": "public-read"},
        )

    update_background_data = nullify_text_columns(
        exclude_unset(
            {
                "background_hex_color": background_hex_color,
                "background_image_fitting_mode": background_image_fitting_mode,
                "background_image_s3_uri": background_image_s3_uri,
            }
        )
    )
    update_background_data["user_id"] = user_id

    set_statement = to_set_statement(update_background_data.keys())
    query = f"""
UPDATE
    board b1
SET
    {set_statement}
FROM
    board b2
WHERE
    b1.user_id = b2.user_id
    AND b1.user_id = :user_id
RETURNING
    b2.background_image_s3_uri as prev_bg_image_uri,
    b1.background_image_s3_uri,
    b1.background_hex_color,
    b1.background_image_fitting_mode
    """

    result = await database.fetch_one(query=query, values=update_background_data)

    if result["prev_bg_image_uri"]:
        prev_bg_image_uri = result["prev_bg_image_uri"]
        s3_object_key = prev_bg_image_uri.split("com/")[-1]
        s3_client.delete_object(Bucket=BOARD_IMAGES_S3_BUCKET, Key=s3_object_key)

    return jsonable_encoder(result)
