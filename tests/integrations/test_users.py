import base64
import json
from unittest.mock import patch

import pytest
from google.oauth2 import id_token
from sendgrid.sendgrid import SendGridAPIClient
from sqlalchemy import text

from whoami_back.api.v1.account import base_url as account_base_url
from whoami_back.api.v1.users import base_url


@pytest.mark.asyncio
async def test_password_signup_confirm_and_login_flow(
    db_conn, api_client, event_loop
):
    # Test signup
    body = {
        "email": "test@gmail.com",
        "password": "test",
        "first_name": "test_first_name",
        "last_name": "test_last_name",
    }
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(f"{base_url}/signup", json=body)
        mock_method.assert_called_once()
        assert result.status_code == 200

    query = await db_conn.execute(
        text('select * from "user" where email = :email').bindparams(
            email=body["email"]
        )
    )
    query_result = query.fetchone()
    user = dict(query_result)
    assert user["first_name"] == body["first_name"]
    assert user["last_name"] == body["last_name"]
    assert user["username"] == body["email"].split("@")[0]

    # Test unconfirmed user login
    body = {"email": body["email"], "password": body["password"]}
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 403
    assert result.json().get("detail").get("access_token")
    assert result.json().get("detail").get("message")

    # Resend the confirmation email
    access_token = result.json()["detail"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.get(
            f"{base_url}/resend-confirmation", headers=headers
        )
        mock_method.assert_called_once()
        assert result.status_code == 200

    query = await db_conn.execute(
        text('select * from "user" where email = :email').bindparams(
            email=body["email"]
        )
    )
    query_result = query.fetchone()
    user = dict(query_result)
    assert not user["confirmed"]

    # Confirm the user
    confirmation_url = (
        mock_method.call_args[0][0].personalizations[0].dynamic_template_data["link"]
    )
    access_token = confirmation_url.split("token=")[1]
    headers = {"Authorization": f"Bearer {access_token}"}

    result = await api_client.get(f"{base_url}/confirm", headers=headers)
    assert result.status_code == 200
    assert result.json()["confirmed_user_email"] == body["email"]

    # Try login
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200
    assert result.json()["access_token"]

    # Check user_profile entry has been created
    query = await db_conn.execute(
        text("SELECT * FROM user_profile WHERE user_id = :user_id").bindparams(
            user_id=user["id"]
        )
    )
    query_result = query.fetchone()
    user_profile = dict(query_result)
    assert user_profile is not None
    assert user_profile["user_id"] is not None
    assert user["id"] == user_profile["user_id"]


@pytest.mark.asyncio
async def test_account_lockout(api_client, add_user, event_loop):
    # Create a test user
    body = {"username": "jocho", "email": "jocho@gmail.com", "password": "hi"}
    await add_user(**body)
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200

    # Attempt failed logins
    for i in range(5):
        body["password"] = "something_else"
        result = await api_client.post(f"{base_url}/login", json=body)
        assert result.status_code == 401

        result = result.json()
        assert "failed_login_attempt_count" in result["detail"]
        assert result["detail"]["failed_login_attempt_count"] == i + 1

    # Check if the account has been locked. Try that the correct credential still
    # doesn't work.
    body["password"] = "hi"
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 423


@pytest.mark.asyncio
async def test_password_reset_resetting_failed_login_attempt_count(
    api_client, add_user, db_conn, event_loop
):
    # Create a test user
    body = {"username": "jocho", "email": "jocho@gmail.com", "password": "hi"}
    await add_user(**body)
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200
    access_token = result.json()["access_token"]

    # Attempt failed logins
    for i in range(5):
        body["password"] = "something_else"
        result = await api_client.post(f"{base_url}/login", json=body)
        assert result.status_code == 401

    # Check if the account has been locked
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 423

    # Reset password
    headers = {"Authorization": f"Bearer {access_token}"}
    update_password_body = {"new_password": "new_hi"}
    result = await api_client.patch(
        f"{account_base_url}/password",
        headers=headers,
        json=update_password_body,
    )
    assert result.status_code == 200

    # Confirm that login works again
    body["password"] = update_password_body["new_password"]
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200

    # Get the user's id
    result = await api_client.get(f"{base_url}", headers=headers)
    user_id = result.json()["id"]

    # Confirm that the user's login attempt count has been reset
    query = await db_conn.execute(
        text('SELECT * FROM "user" WHERE id = :id').bindparams(id=user_id)
    )
    user_data = query.fetchone()

    assert user_data["failed_login_attempt_count"] == 0


@pytest.mark.asyncio
async def test_me_endpoint(api_client, add_user, event_loop):
    # Create a test user
    body = {"username": "jocho", "email": "jocho@gmail.com", "password": "hi"}
    await add_user(**body)
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200

    # Hit the ME endpoint
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    result = await api_client.get(base_url, headers=headers)
    assert result.status_code == 200

    # Check the response
    user_data = result.json()
    user_keys = [
        "id",
        "created_at",
        "updated_at",
        "board_view_type",
        "email",
        "username",
        "first_name",
        "last_name",
        "confirmed",
        "public",
        "active",
    ]

    for key in user_keys:
        assert key in user_data

        if key in body:
            assert body[key] == user_data[key]


@pytest.mark.asyncio
async def test_password_reset_flow(api_client, event_loop):
    body = {
        "email": "test@gmail.com",
        "password": "beforechange",
        "first_name": "test_first_name",
        "last_name": "test_last_name",
    }
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(f"{base_url}/signup", json=body)

    body = {"email": body["email"], "password": body["password"]}
    result = await api_client.post(f"{base_url}/login", json=body)
    access_token = result.json()["detail"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    result = await api_client.get(f"{base_url}/confirm", headers=headers)

    # Confirm login works
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200
    assert result.json()["access_token"]
    access_token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Test not sending an email for an unknown user
    bad_body = {"email": "random@gmail.com"}
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(
            f"{base_url}/send-password-reset", json=bad_body
        )
        mock_method.assert_not_called()

    # Test sending an email for an known user
    good_body = {"email": "test@gmail.com"}
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(
            f"{base_url}/send-password-reset", json=good_body
        )
        mock_method.assert_called_once()

    body = {"new_password": "afterchange"}
    result = await api_client.patch(
        f"{account_base_url}/password", headers=headers, json=body
    )
    assert result.status_code == 200

    # Try login with the new credential
    body = {"email": "test@gmail.com", "password": "afterchange"}
    result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200
    assert result.json()["access_token"]


@pytest.mark.asyncio
async def test_google_signup_and_login_flow(db_conn, api_client, event_loop):
    mock_google_user_info = {"email": "test@gmail.com", "sub": "fake_google_id"}
    body = {
        "email": "test@gmail.com",
        "first_name": "test_first_name",
        "last_name": "test_last_name",
        "access_token": "fake_access_token",
        "service_user_id": "fake_google_id",
        "auth_service": "google",
    }
    with patch.object(
        id_token, "verify_oauth2_token", return_value=mock_google_user_info
    ):
        result = await api_client.post(f"{base_url}/signup", json=body)
        assert result.status_code == 200

    query = await db_conn.execute(
        text('select * from "user" where email = :email').bindparams(
            email=body["email"]
        )
    )
    query_result = query.fetchone()
    user = dict(query_result)
    assert user["first_name"] == body["first_name"]
    assert user["last_name"] == body["last_name"]
    assert user["confirmed"]
    assert user["username"] == body["email"].split("@")[0]

    body = {
        "email": body["email"],
        "access_token": body["access_token"],
        "auth_service": body["auth_service"],
        "service_user_id": body["service_user_id"],
    }
    with patch.object(
        id_token, "verify_oauth2_token", return_value=mock_google_user_info
    ):
        result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200
    assert result.json()["access_token"]


@pytest.mark.asyncio
async def test_facebook_signup_and_login_flow(db_conn, api_client, event_loop):
    mock_facebook_user_info = {
        "email": "test@gmail.com",
        "sub": "fake_facebook_id",
    }
    fake_token_dict = {
        "user_id": "facebook_user_id",
        "code": "fake_code",
        "algorithm": "fake-algorithm",
        "issued_at": 111111111,
    }
    dict_in_str = json.dumps(fake_token_dict)
    fake_access_token_byte = base64.b64encode(dict_in_str.encode("utf-8"))
    fake_access_token = f"something.{fake_access_token_byte.decode('utf-8')}"

    if fake_access_token[-1] == "=":
        fake_access_token = fake_access_token[:-1]

    body = {
        "email": "test@gmail.com",
        "first_name": "test_first_name",
        "last_name": "test_last_name",
        "access_token": fake_access_token,
        "auth_service": "facebook",
        "service_user_id": "facebook_user_id",
    }
    with patch.object(
        id_token, "verify_oauth2_token", return_value=mock_facebook_user_info
    ):
        result = await api_client.post(f"{base_url}/signup", json=body)
        assert result.status_code == 200

    query = await db_conn.execute(
        text('select * from "user" where email = :email').bindparams(
            email=body["email"]
        )
    )
    query_result = query.fetchone()
    user = dict(query_result)
    assert user["first_name"] == body["first_name"]
    assert user["last_name"] == body["last_name"]
    assert user["username"] == body["email"].split("@")[0]
    assert user["confirmed"]

    body = {
        "email": body["email"],
        "access_token": body["access_token"],
        "auth_service": body["auth_service"],
        "service_user_id": body["service_user_id"],
    }
    with patch.object(
        id_token, "verify_oauth2_token", return_value=mock_facebook_user_info
    ):
        result = await api_client.post(f"{base_url}/login", json=body)
    assert result.status_code == 200
    assert result.json()["access_token"]


@pytest.mark.asyncio
async def test_default_usernaming_logic(db_conn, api_client, event_loop):
    body = {
        "email": "test@gmail.com",
        "password": "test",
        "first_name": "test_first_name",
        "last_name": "test_last_name",
    }
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(f"{base_url}/signup", json=body)
        mock_method.assert_called_once()
        assert result.status_code == 200

    # Create 2 more users with the same username part in the email address
    body["email"] = "test@yahoo.com"
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(f"{base_url}/signup", json=body)
        mock_method.assert_called_once()
        assert result.status_code == 200

    body["email"] = "test@something.com"
    with patch.object(SendGridAPIClient, "send", return_value=None) as mock_method:
        result = await api_client.post(f"{base_url}/signup", json=body)
        mock_method.assert_called_once()
        assert result.status_code == 200

    # Check their usernames
    query = await db_conn.execute(
        text('select * from "user" where first_name = :first_name').bindparams(
            first_name=body["first_name"]
        )
    )
    query_result = query.fetchall()
    assert len(query_result) == 3
    usernames_dict = {user_row.email: user_row.username for user_row in query_result}
    assert usernames_dict["test@gmail.com"] == "test"
    assert usernames_dict["test@yahoo.com"] == "test_0"
    assert usernames_dict["test@something.com"] == "test_1"
