from unittest.mock import MagicMock, Mock, patch

import pytest
from s3transfer.manager import TransferManager
from sqlalchemy import text

from tests.utils import create_temp_image_file
from whoami_back.api.v1.board import base_url as board_base_url
from whoami_back.api.v1.posts import base_url
from whoami_back.api.v1.users import base_url as users_base_url


@pytest.mark.asyncio
async def test_update_whoami_image_post(
    db_conn, tmp_path, add_post, add_user, api_client, event_loop
):
    # Add a user and prepare the header to use
    username = "jocho"
    body = {"username": username, "email": f"{username}@gmail.com", "password": "hi"}
    user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Make sure there's no post
    result = await api_client.get(f"{board_base_url}/{username}", headers=headers)
    assert result.status_code == 200
    assert len(result.json()["posts"]) == 0

    content_image_dir = create_temp_image_file(tmp_path, "content_image.jpg")
    files = {"content_image": open(content_image_dir, "rb")}
    data = {
        "title": "a",
        "description": "a",
        "x": 1,
        "y": 1,
        "height": 1,
        "width": 1,
        "scale": 1.0,
    }

    # Create a post
    upload_mock = Mock()
    upload_mock.result = MagicMock(return_value=None)
    with patch.object(
        TransferManager, "upload", return_value=upload_mock
    ) as mock_method:
        result = await api_client.post(
            f"{base_url}/whoami-image", headers=headers, data=data, files=files
        )
        assert mock_method.asert_called()

    post_id = result.json()["post"]["id"]

    new_data = {
        "title": "b",
        "description": "b",
        "x": 2,
        "y": 2,
        "height": 2,
        "width": 2,
        "scale": 2.0,
    }

    # Update the post
    with patch.object(
        TransferManager, "upload", return_value=upload_mock
    ) as mock_method:
        result = await api_client.patch(
            f"{base_url}/whoami-image/{post_id}", headers=headers, data=new_data
        )
        assert mock_method.asert_called()

    # Check if it was set correctly
    query = await db_conn.execute(
        text(
            """
SELECT
    id,
    source,
    content_uri,
    thumbnail_image_uri,
    description,
    title,
    x,
    y,
    height,
    width,
    scale
FROM post
WHERE user_id = :user_id
            """
        ).bindparams(user_id=user_id)
    )
    query_result = query.fetchone()
    post = dict(query_result)

    assert post["content_uri"] == post["thumbnail_image_uri"]
    assert (
        f"https://whoami-post-images.s3.amazonaws.com/{user_id}/{post['id']}"
        == post["content_uri"]
    )

    for key in data:
        assert post[key] == new_data[key]


@pytest.mark.asyncio
async def test_create_whoami_image_post(
    db_conn, tmp_path, add_post, add_user, api_client, event_loop
):
    # Add a user and prepare the header to use
    username = "jocho"
    body = {"username": username, "email": f"{username}@gmail.com", "password": "hi"}
    user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Make sure there's no post
    result = await api_client.get(f"{board_base_url}/{username}", headers=headers)
    assert result.status_code == 200
    assert len(result.json()["posts"]) == 0

    content_image_dir = create_temp_image_file(tmp_path, "content_image.jpg")
    files = {"content_image": open(content_image_dir, "rb")}
    data = {
        "title": "some title",
        "description": "some description",
        "x": 1,
        "y": 1,
        "height": 1,
        "width": 1,
        "scale": 1.0,
    }

    # Mock out the S3 transfer part
    upload_mock = Mock()
    upload_mock.result = MagicMock(return_value=None)
    with patch.object(
        TransferManager, "upload", return_value=upload_mock
    ) as mock_method:
        result = await api_client.post(
            f"{base_url}/whoami-image", headers=headers, data=data, files=files
        )
        assert mock_method.asert_called()

    # Check if it was set correctly
    query = await db_conn.execute(
        text(
            """
SELECT
    id,
    source,
    content_uri,
    thumbnail_image_uri,
    description,
    title,
    x,
    y,
    height,
    width,
    scale
FROM post
WHERE user_id = :user_id
            """
        ).bindparams(user_id=user_id)
    )
    query_result = query.fetchone()
    post = dict(query_result)

    assert post["content_uri"] == post["thumbnail_image_uri"]
    assert (
        f"https://whoami-post-images.s3.amazonaws.com/{user_id}/{post['id']}"
        == post["content_uri"]
    )

    for key in data:
        assert post[key] == data[key]


@pytest.mark.asyncio
async def test_create_post(db_conn, add_post, add_user, api_client, event_loop):
    # Add a user and prepare the header to use
    username = "jocho"
    body = {"username": username, "email": f"{username}@gmail.com", "password": "hi"}
    await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Make sure there's no post
    result = await api_client.get(f"{board_base_url}/{username}", headers=headers)
    assert result.status_code == 200
    assert len(result.json()["posts"]) == 0

    # Create three posts
    bodies = {}
    for i in range(3):
        body = {
            "source": "instagram",
            "content_uri": f"https://instagram.com/some_content_{i}",
            "title": f"content_{i}",
            "meta_title": f"meta_title_{i}",
            "meta_description": f"meta_description_{i}",
            "x": i,
            "y": i,
            "width": i,
            "height": i,
            "scale": float(i * 2),
        }
        bodies[i] = body

        result = await api_client.post(f"{base_url}", json=body, headers=headers)
        assert result.status_code == 200

        new_post_data = result.json()
        assert "post" in new_post_data
        assert "id" in new_post_data["post"]

        for key in body:
            assert new_post_data["post"][key] == body[key]

    # Get the board
    result = await api_client.get(f"{board_base_url}/{username}", headers=headers)
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3

    for post in board_json:
        target_post_data = bodies[post["x"]]

        for key in target_post_data.keys():
            assert target_post_data[key] == post[key]


@pytest.mark.asyncio
async def test_update_post(db_conn, add_post, add_user, api_client, event_loop):
    # Add a user and prepare the header to use
    username = "jocho"
    body = {"username": username, "email": f"{username}@gmail.com", "password": "hi"}
    user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create three posts
    create_post_bodies = {}
    for i in range(3):
        body = {
            "source": "instagram",
            "content_uri": f"https://instagram.com/some_content_{i}",
            "title": f"content_{i}",
            "meta_title": f"meta_title_{i}",
            "meta_description": f"meta_description_{i}",
            "x": i,
            "y": i,
            "width": i,
            "height": i,
            "scale": float(i * 2),
        }
        post_id = await add_post(user_id, **body)
        body["id"] = post_id
        create_post_bodies[i] = body

    # Get the board
    result = await api_client.get(f"{board_base_url}/{username}", headers=headers)
    assert result.status_code == 200
    assert len(result.json()["posts"]) == 3

    # Update the first post. post.title & post.x stay the same
    post_id = create_post_bodies[0]["id"]
    update_post_body = {
        "source": "facebook",
        "content_uri": "testing url",
        "meta_title": "testing_meta_title",
        "meta_description": "testing_meta_description",
        "y": 100,
        "width": 100,
        "height": 100,
        "scale": 100.0,
    }
    result = await api_client.patch(
        f"{base_url}/{post_id}", headers=headers, json=update_post_body
    )
    assert result.status_code == 200
    updated_post = result.json()
    assert "post" in updated_post

    assert updated_post["post"]["title"] == "content_0"
    assert updated_post["post"]["x"] == 0
    for key in update_post_body:
        assert updated_post["post"][key] == update_post_body[key]

    # Check if the post data has been REALLY updated correctly in DB
    query = await db_conn.execute(
        text("SELECT * FROM post WHERE id = :post_id").bindparams(post_id=post_id)
    )
    target_post = query.fetchone()
    for key in update_post_body:
        assert str(getattr(target_post, key)) == str(update_post_body[key])
    assert target_post.title == "content_0"
    assert target_post.x == 0

    # Check if the other post have stayed the SAME
    query = await db_conn.execute(
        text("SELECT * FROM post WHERE id = :post_id").bindparams(
            post_id=create_post_bodies[1]["id"]
        )
    )
    target_post = query.fetchone()
    for key in create_post_bodies[1]:
        assert str(getattr(target_post, key)) == str(create_post_bodies[1][key])


@pytest.mark.asyncio
async def test_delete_post(db_conn, add_post, add_user, api_client, event_loop):
    # Add a user and prepare the header to use
    username = "jocho"
    body = {"username": username, "email": f"{username}@gmail.com", "password": "hi"}
    user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create three posts
    create_post_bodies = {}
    for i in range(3):
        body = {
            "source": "instagram",
            "content_uri": f"https://instagram.com/some_content_{i}",
            "title": f"content_{i}",
            "meta_title": f"meta_title_{i}",
            "meta_description": f"meta_description_{i}",
            "x": i,
            "y": i,
            "width": i,
            "height": i,
            "scale": float(i * 2),
        }
        post_id = await add_post(user_id, **body)
        body["id"] = post_id
        create_post_bodies[i] = body

    # Delete the first post
    post_id = create_post_bodies[0]["id"]
    result = await api_client.delete(f"{base_url}/{post_id}", headers=headers)
    assert result.status_code == 200

    # Check that the post has been ACTUALLY removed
    query = await db_conn.execute(
        text("SELECT * FROM post WHERE user_id = :user_id").bindparams(
            user_id=user_id
        )
    )
    result = query.fetchall()
    assert len(result) == 2

    # Check that the other two are STILL there
    create_post_bodies.pop(0)
    left_over_post_ids = list(
        map(lambda i: create_post_bodies[i]["id"], create_post_bodies)
    )
    for post in result:
        assert str(post.id) in left_over_post_ids
