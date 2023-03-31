from unittest.mock import patch

import pytest
from sendgrid.sendgrid import SendGridAPIClient
from sqlalchemy import text

from whoami_back.api.v1.account import base_url
from whoami_back.api.v1.board import base_url as board_base_url
from whoami_back.api.v1.posts import base_url as posts_base_url
from whoami_back.api.v1.users import base_url as users_base_url


@pytest.mark.asyncio
async def test_update_password(add_user, api_client, event_loop):
    # Our current user, email is jocho@gmail.com and password is hi
    await add_user()

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Check if it errors out on a wrong old_password
    body = {"old_password": "hii", "new_password": "bye"}
    result = await api_client.patch(
        f"{base_url}/update-password", headers=headers, json=body
    )
    assert result.status_code == 400
    assert result.json()["detail"] == "Wrong password"

    # Check the update password endpoint with the correct password
    body["old_password"] = "hi"
    result = await api_client.patch(
        f"{base_url}/update-password", headers=headers, json=body
    )
    assert result.status_code == 200

    # Confirm we cannot login using the old password
    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    assert result.status_code == 401
    assert "failed_login_attempt_count" in result.json()["detail"]

    # Confirm we can login using the new password
    body = {"email": "jocho@gmail.com", "password": "bye"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_update_account_privacy(db_conn, add_user, api_client, event_loop):
    # A user with email = jocho@gmail.com
    await add_user()

    # Another user with email = test@gmail.com
    await add_user(email="test@gmail.com", username="hello")

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Make the current user private
    body = {"public": False}
    result = await api_client.patch(
        f"{base_url}/privacy", headers=headers, json=body
    )
    assert result.status_code == 200

    body = {"email": "test@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Try to see the user A's board
    result = await api_client.get(f"{board_base_url}/jocho", headers=headers)
    assert result.status_code == 403
    assert (
        result.json()["detail"]
        == "Current user is not an approved follower of the target user"
    )


@pytest.mark.asyncio
async def test_delete_account(db_conn, add_user, api_client, event_loop):
    # A user with email jocho@gmail.com
    user_id = await add_user()

    # An additional user to test interactions
    await add_user(email="test@gmail.com", username="test")

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Check if it checks the password correctly
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        body["password"] = "bye"
        result = await api_client.request(
            "DELETE",
            base_url,
            headers=headers,
            json=body,
        )
        mock_method.assert_not_called()
        assert result.status_code == 400
        assert result.json()["detail"] == "Wrong password"

    # Actually delete the account
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        body["password"] = "hi"
        result = await api_client.request(
            "DELETE", base_url, headers=headers, json=body
        )
        mock_method.assert_called_once()
        assert result.status_code == 200

    # Actually check the user has been deleted
    query = await db_conn.execute(
        text('SELECT * FROM "user" WHERE id = :user_id').bindparams(user_id=user_id)
    )
    query_result = query.fetchone()
    assert query_result is None


@pytest.mark.asyncio
async def test_deactivate_account(db_conn, add_user, api_client, event_loop):
    # Our current user, email is jocho@gmail.com
    await add_user()

    # An additional user to test interactions
    await add_user(email="test@gmail.com", username="hello")

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Check if it checks the password correctly
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        body["password"] = "bye"
        result = await api_client.patch(
            f"{base_url}/deactivate", headers=headers, json=body
        )
        mock_method.assert_not_called()
        assert result.status_code == 400
        assert result.json()["detail"] == "Wrong password"

    # Actually deactivate the account
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        body["password"] = "hi"
        result = await api_client.patch(
            f"{base_url}/deactivate", headers=headers, json=body
        )
        mock_method.assert_called_once()
        assert result.status_code == 200

    # Check resources are blocked for the inactive user
    result = await api_client.get(posts_base_url, headers=headers)
    assert result.status_code == 401
    assert result.json()["detail"] == "Inactive user"

    # TODO: Add some other resource calls


@pytest.mark.asyncio
async def test_update_linked_profiles(add_user, db_conn, api_client, event_loop):
    user_id = await add_user()

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Check if it works with an empty linked_profiles
    body = {"linked_profiles": []}
    result = await api_client.post(
        f"{base_url}/linked-profiles", headers=headers, json=body
    )
    assert result.status_code == 200

    # Check the basic functionality
    body = {
        "linked_profiles": [
            {
                "social_media_platform": "facebook",
                "profile_link": "https://whoami.com/jocho",
                "link_label": "My unique whoami board",
            },
            {
                "social_media_platform": "instagram",
                "profile_link": "https://instagram.com/jocho",
                "link_label": "My unique instagram board",
            },
        ]
    }
    result = await api_client.post(
        f"{base_url}/linked-profiles", headers=headers, json=body
    )
    assert result.status_code == 200
    query = await db_conn.execute(
        text("SELECT * FROM linked_profile WHERE user_id = :user_id").bindparams(
            user_id=user_id
        )
    )
    query_result = query.fetchall()
    assert len(query_result) == 2
    original_profile_ids = {str(q.id) for q in query_result}

    # Check if the profile is marked with unknown
    body["linked_profiles"][0]["social_media_platform"] = "unknown"
    result = await api_client.post(
        f"{base_url}/linked-profiles", headers=headers, json=body
    )
    assert result.status_code == 200
    query = await db_conn.execute(
        text("SELECT * FROM linked_profile WHERE user_id = :user_id").bindparams(
            user_id=user_id
        )
    )
    query_result = query.fetchall()
    assert len(query_result) == 2
    new_profile_ids = {str(q.id) for q in query_result}

    assert len(original_profile_ids & new_profile_ids) == 0
    assert len(original_profile_ids | new_profile_ids) == 4


@pytest.mark.asyncio
async def test_confirm_password(add_user, api_client, event_loop):
    # Our current user, email is jocho@gmail.com and password is hi
    await add_user()

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Check if it errors out on a wrong password
    body = {"password": "bye"}
    result = await api_client.post(
        f"{base_url}/confirm-password", headers=headers, json=body
    )
    assert result.status_code == 400
    assert result.json()["detail"] == "Wrong password"

    # Check the confirm password endpoint with the correct password
    body["password"] = "hi"
    result = await api_client.post(
        f"{base_url}/confirm-password", headers=headers, json=body
    )
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_change_email(db_conn, add_user, api_client, event_loop):
    # Our current user, email is jocho@gmail.com
    await add_user()

    # An additional user to test email validation endpoint
    await add_user(email="test@gmail.com", username="hello")

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    # Check if it doesn't let you change to an existing email address
    body = {"new_email": "test@gmail.com"}
    result = await api_client.patch(f"{base_url}/email", headers=headers, json=body)
    assert result.status_code == 400
    assert result.json()["detail"] == "The given email is already taken"

    body["new_email"] = "done@gmail.com"
    result = await api_client.patch(f"{base_url}/email", headers=headers, json=body)
    assert result.status_code == 200

    query = await db_conn.execute(
        text('SELECT * FROM "user" WHERE email = :email').bindparams(
            email=body["new_email"]
        )
    )
    query_result = query.fetchone()
    assert query_result
