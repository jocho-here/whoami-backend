import time
from datetime import datetime, timezone

import arrow
import pytest
from sqlalchemy import text

from whoami_back.api.v1.board import base_url
from whoami_back.api.v1.users import base_url as users_base_url


@pytest.mark.asyncio
async def test_get_my_board(db_conn, add_post, add_user, api_client, event_loop):
    # Add a user and prepare the header to use
    username = "jocho"
    body = {"username": username, "email": f"{username}@gmail.com", "password": "hi"}
    user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Test API call not returning anything
    result = await api_client.get(
        f"{base_url}/{username}?board_view_type=board", headers=headers
    )
    assert result.status_code == 200
    assert len(result.json()["posts"]) == 0

    post_ids = []

    # time.sleep to make the posts updated_at time different. This is to check the
    # sorting functionality
    for _ in range(3):
        time.sleep(1)
        curr_time = datetime.now(timezone.utc)
        post_ids.append(
            await add_post(user_id, created_at=curr_time, updated_at=curr_time)
        )

    # Get board view type board
    result = await api_client.get(
        f"{base_url}/{username}?board_view_type=board", headers=headers
    )
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3

    # Check all the posts in board_json are expected ones
    for post in board_json:
        assert post["id"] in post_ids

        for key in (
            "content_uri",
            "updated_at",
            "created_at",
            "height",
            "source",
            "title",
            "user_id",
            "width",
            "x",
            "y",
        ):
            assert key in post

    # Check that we got the posts in chronological order of updated_at
    assert arrow.get(board_json[0]["updated_at"]) < arrow.get(
        board_json[1]["updated_at"]
    )
    assert arrow.get(board_json[1]["updated_at"]) < arrow.get(
        board_json[2]["updated_at"]
    )

    # Get stack view type board
    result = await api_client.get(
        f"{base_url}/{username}?board_view_type=stack", headers=headers
    )
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3

    # Check that we got the posts in reverse-chronological order of created_at
    assert arrow.get(board_json[0]["created_at"]) > arrow.get(
        board_json[1]["created_at"]
    )
    assert arrow.get(board_json[1]["created_at"]) > arrow.get(
        board_json[2]["created_at"]
    )

    # Add another user who's not following the user "jocho"
    jocho_username = username
    username = "choon.sik"
    body = {
        "username": username,
        "email": f"{username}@gmail.com",
        "password": "bye",
    }
    user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Confirm that "choon.sik", who's not following "jocho", can still get "jocho"
    # board since "jocho" is a public account
    result = await api_client.get(
        f"{base_url}/{jocho_username}?board_view_type=stack", headers=headers
    )
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3

    # Confirm that the board is reachable by non-logged in user, basically by public
    result = await api_client.get(
        f"{base_url}/{jocho_username}?board_view_type=stack"
    )
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3


@pytest.mark.asyncio
async def test_unable_get_inactive_user_board(
    db_conn, add_user, api_client, event_loop
):
    await add_user()
    target_user_id = await add_user(email="test@gmail.com", username="hello")

    await db_conn.execute(
        text('UPDATE "user" SET active = FALSE WHERE id = :id').bindparams(
            id=target_user_id
        )
    )

    target_user_username = "hello"
    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    result = await api_client.get(
        f"{base_url}/{target_user_username}", headers=headers
    )
    assert result.status_code == 400
    assert (
        result.json()["detail"]
        == "User with the given username (hello) is not active"
    )


@pytest.mark.asyncio
async def test_get_private_user_board(
    db_conn, add_following, add_post, add_user, api_client, event_loop
):
    # Add current user and prepare the header to use
    current_username = "jocho"
    body = {
        "username": current_username,
        "email": f"{current_username}@gmail.com",
        "password": "hi",
    }
    current_user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Add a private user
    target_username = "choon.sik"
    body = {
        "username": target_username,
        "email": f"{target_username}@gmail.com",
        "password": "bye",
        "public": False,
    }
    target_user_id = await add_user(**body)
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    target_user_headers = {"Authorization": f"Bearer {access_token}"}

    post_ids = []

    # time.sleep to make the posts updated_at time different. This is to check the
    # sorting functionality
    for _ in range(3):
        post_ids.append(await add_post(target_user_id))

    # Check if private user's board is not accessible by non-follower
    result = await api_client.get(f"{base_url}/{target_username}", headers=headers)
    assert result.status_code == 403

    # Check if private user's board is not accessible without logging as well
    result = await api_client.get(f"{base_url}/{target_username}")
    assert result.status_code == 401

    # Create a following from the following user to the followed user
    # First with unapproved following, and check if it's still unauthorized
    await add_following(current_user_id, target_user_id, approved=False)
    result = await api_client.get(f"{base_url}/{target_username}", headers=headers)
    assert result.status_code == 403

    await db_conn.execute(
        text(
            """
UPDATE following SET approved = :approved
            """
        ).bindparams(approved=True)
    )

    # Finally check that the target user's board is accessible
    result = await api_client.get(f"{base_url}/{target_username}", headers=headers)
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3

    # Check all the posts in board_json are expected ones
    for post in board_json:
        assert post["id"] in post_ids

    # Check that the target user can access his/ her own board
    result = await api_client.get(
        f"{base_url}/{target_username}", headers=target_user_headers
    )
    assert result.status_code == 200

    board_json = result.json()["posts"]
    assert len(board_json) == 3
