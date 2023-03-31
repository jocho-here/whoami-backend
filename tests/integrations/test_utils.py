import pytest

from whoami_back.api.v1.users import base_url as users_base_url
from whoami_back.api.v1.utils import base_url


@pytest.mark.asyncio
async def test_email_validation(add_user, api_client, event_loop):
    # Our current user, email is jocho@gmail.com
    await add_user()

    # An additional user to test email validation endpoint
    await add_user(email="test@gmail.com", username="hello")

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    email_with_expected_result = [
        {
            "email": "jocho@gmail.com",
            "status_code": 400,
            "reason": "The given email is the target user's email",
        },
        {
            "email": "test@gmail.com",
            "status_code": 400,
            "reason": "The given email is already taken",
        },
    ]

    for test_entry in email_with_expected_result:
        email = test_entry["email"]
        status_code = test_entry["status_code"]
        reason = test_entry["reason"]

        body = {"email": email}
        result = await api_client.post(
            f"{base_url}/validate/email", headers=headers, json=body
        )
        assert result.status_code == status_code

        if status_code == 400:
            assert result.json()["detail"] == reason


@pytest.mark.asyncio
async def test_username_validation(db_conn, add_user, api_client, event_loop):
    # Our current user, username is jocho
    await add_user()

    # An additional user to test username validation endpoint
    await add_user(email="test@gmail.com", username="hello")

    body = {"email": "jocho@gmail.com", "password": "hi"}
    result = await api_client.post(f"{users_base_url}/login", json=body)
    access_token = result.json()["access_token"]
    headers = {"authorization": f"Bearer {access_token}"}

    username_with_expected_result = [
        {
            "username": "jocho",
            "status_code": 400,
            "reason": "The given username is the target user's username",
        },
        {"username": "", "status_code": 400, "reason": "No username provided"},
        {
            "username": "Hello",
            "status_code": 400,
            "reason": "username format is invalid",
        },
        {
            "username": "hello",
            "status_code": 400,
            "reason": "The given username is already taken",
        },
        {"username": "b_y.e_3", "status_code": 200, "reason": ""},
    ]

    for test_entry in username_with_expected_result:
        username = test_entry["username"]
        status_code = test_entry["status_code"]
        reason = test_entry["reason"]

        body = {"username": username}
        result = await api_client.post(
            f"{base_url}/validate/username", headers=headers, json=body
        )
        assert result.status_code == status_code

        if status_code == 400:
            assert result.json()["detail"] == reason
