from unittest.mock import MagicMock, Mock, patch

import pytest
from s3transfer.manager import TransferManager
from sqlalchemy import text

from tests.utils import create_temp_image_file
from whoami_back.api.v1.user_profile import base_url
from whoami_back.api.v1.users import base_url as users_base_url


@pytest.mark.asyncio
async def test_edit_user_profile_username_validation(
    db_conn, tmp_path, add_user, api_client, event_loop
):
    await add_user()
    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Assert uppercase username is invalid
    data = {
        "first_name": "java",
        "last_name": "chip",
        "username": "COOKIE",
        "bio": "random bio #here",
    }
    result = await api_client.patch(base_url, headers=headers, data=data)
    assert result.status_code == 400
    assert result.json()["detail"] == "username format is invalid"

    # Add another user to test edit profile invalidating the SAME username
    body = {"email": "shangchi@gmail.com", "username": "shangchi", "password": "hi"}
    await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Assert same username is invalid
    data["username"] = "jocho"
    result = await api_client.patch(base_url, headers=headers, data=data)
    assert result.status_code == 400
    assert result.json()["detail"] == "The given username is already taken"


@pytest.mark.asyncio
async def test_edit_user_profile(
    db_conn, tmp_path, add_user, api_client, event_loop
):
    user_id = await add_user()
    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Edit profile without new images
    data = {
        "first_name": "java",
        "last_name": "chip",
        "username": "cookie",
        "bio": "random bio #here",
    }
    result = await api_client.patch(base_url, headers=headers, data=data)
    assert result.status_code == 200

    # Check if it was changed correctly
    query = await db_conn.execute(
        text(
            """
SELECT id, bio, first_name, last_name, username FROM user_profile
JOIN \"user\" ON \"user\".id = user_profile.user_id
WHERE \"user\".id = :user_id
            """
        ).bindparams(user_id=user_id)
    )
    query_result = query.fetchone()
    user_profile = dict(query_result)
    assert str(user_profile["id"]) == user_id
    assert user_profile["bio"] == data["bio"]
    assert user_profile["username"] == data["username"]
    assert user_profile["first_name"] == data["first_name"]
    assert user_profile["last_name"] == data["last_name"]

    # Edit profile with new images
    profile_image_dir = create_temp_image_file(tmp_path, "profile_image.jpg")
    profile_background_dir = create_temp_image_file(
        tmp_path, "profile_background.jpg"
    )
    files = {
        "profile_image": open(profile_image_dir, "rb"),
        "profile_background": open(profile_background_dir, "rb"),
    }
    data = {
        "first_name": "JAVA",
        "last_name": "CHIP",
        "username": "cookies",
        "bio": "RANDOM BIO #HERE",
    }

    # Mock out the S3 transfer part
    upload_mock = Mock()
    upload_mock.result = MagicMock(return_value=None)
    with patch.object(
        TransferManager, "upload", return_value=upload_mock
    ) as mock_method:
        result = await api_client.patch(
            base_url, headers=headers, data=data, files=files
        )
        assert mock_method.asert_called()

    # Check if it was changed correctly
    query = await db_conn.execute(
        text(
            """
SELECT
    id,
    bio,
    first_name,
    last_name,
    username,
    profile_image_s3_key,
    profile_background_s3_key
FROM user_profile
JOIN \"user\" ON \"user\".id = user_profile.user_id
WHERE \"user\".id = :user_id
            """
        ).bindparams(user_id=user_id)
    )
    query_result = query.fetchone()
    user_profile = dict(query_result)
    assert str(user_profile["id"]) == user_id
    assert user_profile["bio"] == data["bio"]
    assert user_profile["username"] == data["username"]
    assert user_profile["first_name"] == data["first_name"]
    assert user_profile["last_name"] == data["last_name"]
    assert user_profile["profile_image_s3_key"] == f"profile_image/{user_id}"
    assert (
        user_profile["profile_background_s3_key"] == f"profile_background/{user_id}"
    )
