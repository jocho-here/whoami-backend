import base64
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4

from asyncpg.exceptions import UniqueViolationError
from fastapi import Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_auth_service
from jose import JWTError, jwt
from passlib.context import CryptContext
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from whoami_back.api.v1.users import base_url
from whoami_back.api.v1.users.models import UserModel
from whoami_back.utils.config import (  # noqa: F401
    ADMIN_EMAIL,
    CONFIRMATION_JWT_EXPIRES_IN_HOURS,
    FE_HOSTS,
    GOOGLE_CLIENT_ID,
    JWT_ALGORITHM,
    JWT_SIGNATURE,
    PASSWORD_RESET_JWT_EXPIRES_IN_HOURS,
    SENDGRID_API_KEY,
)
from whoami_back.utils.db import database, to_csv, to_ref_csv
from whoami_back.utils.models import remove_keys

# Initialize shared objects
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{base_url}/login", auto_error=False)
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
FE_HOST = FE_HOSTS[0]


class EMAIL_TEMPLATE_IDS:
    CONFIRMATION = "d-554310a144774131bb53ddf318dc932e"
    PASSWORD_RESET = "d-d230239e5b7e47af8636c8de3a45856c"
    NEW_EMAIL_CONFIRMATION = "d-e6e6979caef1409eaa04b44b7ff88672"


class CredentialsException(HTTPException):
    def __init__(self, message):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials. {message}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme), get_password: bool = False
) -> Dict:
    """
    Given the JWT token, return a user found.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, JWT_SIGNATURE, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise CredentialsException(message="user_id is not given in the JWT.")
    except JWTError as e:
        raise CredentialsException(message=e)

    user = await get_user(user_id=user_id, get_password=get_password)

    if not user:
        raise CredentialsException(message="The given user_id in JWT is not valid.")

    return user


async def get_current_active_user_with_password(
    token: str = Depends(oauth2_scheme),
) -> Dict:
    """
    Given the JWT token, return a user found with its password.
    """
    user = await get_current_user(token=token, get_password=True)

    return user


async def get_current_active_user(
    user: Dict = Depends(get_current_user),
) -> Dict:
    if not user["active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    return user


async def get_current_active_user_auth_optional(
    token: str = Depends(oauth2_scheme),
) -> Optional[Dict]:
    if not token:
        user = None
    else:
        try:
            current_user = await get_current_user(token=token)
            user = await get_current_active_user(user=current_user)
        except Exception:
            user = None

    return user


async def get_current_unconfirmed_active_user(
    user: Dict = Depends(get_current_active_user),
) -> Dict:
    if user["confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The target user ({user['email']}) is already confirmed",
        )

    return user


# Password related
def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


async def create_access_token(user_id: str, jwt_expires_in_hours: int) -> str:
    data_to_encode = {
        "sub": user_id,
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=jwt_expires_in_hours),
    }

    encoded_jwt = jwt.encode(data_to_encode, JWT_SIGNATURE, algorithm=JWT_ALGORITHM)

    return encoded_jwt


def _prepare_get_user_param(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
):
    _filter = None
    param = {}

    if user_id:
        _filter = "id = :user_id"
        param["user_id"] = user_id
    if email:
        _filter = "email = :email"
        param["email"] = email
    if username:
        _filter = "LOWER(username) = LOWER(:username)"
        param["username"] = username

    return _filter, param


async def is_user_active(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
) -> bool:
    _filter, params = _prepare_get_user_param(user_id, email, username)

    is_user_active = await database.execute(
        query=f'SELECT EXISTS (SELECT TRUE FROM "user" WHERE {_filter})',
        values=params,
    )

    return is_user_active


async def get_user(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    get_password: Optional[bool] = False,
) -> Dict:
    """
    Get a user using either user_id, email, or username. If get_password is set
    to True, it returns password.
    """
    if not (user_id or email or username):
        return None

    _filter, params = _prepare_get_user_param(user_id, email, username)

    if not get_password:
        select_statement = to_csv(UserModel.schema()["properties"].keys())
    else:
        select_statement = "*"

    user = await database.fetch_one(
        query=f'SELECT {select_statement} FROM "user" WHERE {_filter}', values=params
    )

    if user:
        user = jsonable_encoder(user)

        if user.get("auth_attributes") and isinstance(user["auth_attributes"], str):
            user["auth_attributes"] = json.loads(user["auth_attributes"])

        return jsonable_encoder(user)
    else:
        return None


async def reset_failed_login_attempt(user_id: str) -> None:
    query = """
UPDATE \"user\"
SET
    failed_login_attempt_count = 0,
    updated_at = NOW()
WHERE id = :user_id
RETURNING failed_login_attempt_count
    """
    await database.execute(query=query, values={"user_id": user_id})


async def increment_failed_login_attempt(user_id: str) -> int:
    query = """
UPDATE \"user\"
SET
    failed_login_attempt_count = failed_login_attempt_count + 1,
    updated_at = NOW()
WHERE id = :user_id
RETURNING failed_login_attempt_count
    """
    result = await database.fetch_one(query=query, values={"user_id": user_id})

    return result[0]


async def authenticate_user(login_credential: Dict):
    """
    Try user login with the given email and either a plain password or an
    access_token and auth_service.
    Return False if not authenticated. Else, return a user Row.
    """
    user = await get_user(email=login_credential["email"], get_password=True)

    # Could not find a user with the given email
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user found with the email",
        )

    # Login using password
    if login_credential["password"]:
        # Check if the user exists with 3rd party authentication
        if not user["password"]:
            auth_service = user["auth_attributes"]["auth_service"].capitalize()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User signed up with {auth_service} OAuth",
            )

        # If failed 5 times already, let FE know that the account has been locked
        if user["failed_login_attempt_count"] >= 5:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed login attempts",
            )

        if not verify_password(login_credential["password"], user["password"]):
            new_failed_attempt_count = await increment_failed_login_attempt(
                user["id"]
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"failed_login_attempt_count": new_failed_attempt_count},
            )

        await reset_failed_login_attempt(user["id"])

    # Login using the access_token and auth_service
    if login_credential["access_token"] and login_credential["auth_service"]:
        new_auth_attributes = validate_access_token(
            login_credential["service_user_id"],
            login_credential["email"],
            login_credential["access_token"],
            login_credential["auth_service"],
            target_auth_attributes=user["auth_attributes"],
        )

        # update the user.auth_attributes
        query = """
UPDATE
    \"user\"
SET
    auth_attributes = :new_auth_attributes,
    updated_at = NOW()
WHERE
    id = :user_id
        """
        values = {
            "new_auth_attributes": new_auth_attributes,
            "user_id": user["id"],
        }
        await database.execute(query=query, values=values)

    return user


def validate_password(password: str) -> bool:
    """
    Check the password is valid
    - 1 or more letters (a-z, A-Z), 1 or more numbers
    - 0 or more special characters
    - 8 or more characters
    """
    if not password:
        return False, "No password provided"

    pattern = re.compile("(?=.*[A-Za-z])(?=.*[\d]).{8,}$")  # noqa: W605

    if not pattern.match(password):
        return False, "password format is invalid"

    return True, ""


async def create_user(signup_data: Dict) -> str:
    """
    Complete a user signup.
    Allow signup using email & password or email & access_token
    & auth_service. If successful, return the newly created
    user's ID.
    """
    signup_data["auth_attributes"] = None
    signup_data["confirmed"] = False

    if signup_data["access_token"]:
        signup_data["auth_attributes"] = validate_access_token(
            signup_data["service_user_id"],
            signup_data["email"],
            signup_data["access_token"],
            signup_data["auth_service"],
        )
        signup_data["confirmed"] = True
    elif signup_data["password"]:
        valid, error_message = validate_password(signup_data["password"])

        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message,
            )

        signup_data["password"] = hash_password(signup_data["password"])

    new_user_data = remove_keys(
        signup_data, ["access_token", "auth_service", "service_user_id"]
    )
    new_user_data["id"] = str(uuid4())

    # Add the default username. Take the username part of email address
    username = signup_data["email"].split("@")[0].casefold()
    possible_username = username
    username_counter = 0

    # If the username is taken, try adding number incrementally until it works
    username_already_exists = await username_exists(possible_username)
    while username_already_exists:
        possible_username = f"{username}_{username_counter}"
        username_already_exists = await username_exists(possible_username)
        username_counter += 1

    new_user_data["username"] = possible_username

    try:
        insert_statement = to_csv(new_user_data.keys())
        value_statement = to_ref_csv(new_user_data.keys())
        query = f"""
WITH new_user AS (
    INSERT INTO "user" ({insert_statement})
    VALUES ({value_statement})
    RETURNING id
)
INSERT INTO board (user_id)
SELECT id FROM new_user
        """
        await database.execute(query=query, values=new_user_data)
    except UniqueViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail),
        )

    return new_user_data["id"]


async def username_exists(username: str):
    query = """
SELECT COUNT(*)
FROM \"user\"
WHERE LOWER(username) = LOWER(:username)
    """
    username_count = await database.execute(
        query=query, values={"username": username}
    )

    if username_count > 0:
        return True

    return False


async def confirm_user(user: Dict) -> str:
    query = """
UPDATE \"user\"
SET
    confirmed = TRUE,
    updated_at = NOW()
WHERE id = :user_id
    """
    await database.execute(query=query, values={"user_id": user["id"]})

    return user["email"]


def send_email(email: str, template_id: str, content_url: Optional[str]):
    message = Mail(
        from_email=ADMIN_EMAIL,
        to_emails=email,
    )
    message.template_id = template_id

    if content_url:
        message.dynamic_template_data = {"link": content_url}

    sendgrid_client.send(message)


async def send_password_reset_email(
    email: str, user_id: str, background_tasks
) -> None:
    user_token = await create_access_token(
        user_id, PASSWORD_RESET_JWT_EXPIRES_IN_HOURS
    )
    password_reset_url = f"{FE_HOST}/users/reset-password?token={user_token}"
    background_tasks.add_task(
        send_email, email, EMAIL_TEMPLATE_IDS.PASSWORD_RESET, password_reset_url
    )


async def send_confirmation_email(
    email: str, user_id: str, background_tasks
) -> None:
    user_token = await create_access_token(
        user_id, CONFIRMATION_JWT_EXPIRES_IN_HOURS
    )
    confirmation_url = f"{FE_HOST}/users/confirm?token={user_token}"
    background_tasks.add_task(
        send_email, email, EMAIL_TEMPLATE_IDS.CONFIRMATION, confirmation_url
    )


async def send_new_email_confirmation_email(
    email: str, user_id: str, background_tasks
) -> None:
    user_token = await create_access_token(
        user_id, CONFIRMATION_JWT_EXPIRES_IN_HOURS
    )
    confirmation_url = (
        f"{FE_HOST}/users/confirm-new-email?token={user_token}&new_email={email}"
    )
    background_tasks.add_task(
        send_email,
        email,
        EMAIL_TEMPLATE_IDS.NEW_EMAIL_CONFIRMATION,
        confirmation_url,
    )


def validate_google_access_token(
    google_user_id: str,
    email: str,
    access_token: str,
    *,
    target_auth_attributes: Optional[Dict] = None,
) -> Dict:
    try:
        google_user_info = google_auth_service.verify_oauth2_token(
            access_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot verify the given access_token: {str(e)}",
        )

    verified_email = google_user_info.get("email")
    found_user_id = google_user_info.get("sub")

    # Verify the given email and user_id with the ones found in the access_token
    if verified_email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The email found in the access_token ({verified_email}) "
            f"does not match the given email ({email})",
        )
    elif google_user_id != found_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user_id found in the access_token ({found_user_id}) "
            f"does not match the given user_id ({google_user_id})",
        )

    # Check the Google user_id found in the access_token against the one already
    # exists in the user.auth_attributes
    if target_auth_attributes and found_user_id != target_auth_attributes["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The google_user_id found in the access_token "
            f"({found_user_id}) does not match the user's "
            f"({target_auth_attributes['user_id']})",
        )

    new_auth_attributes = {
        "user_id": found_user_id,
        "access_token": access_token,
        "auth_service": "google",
    }

    return new_auth_attributes


def validate_facebook_signed_request(
    facebook_user_id: str,
    signed_request: str,
    *,
    target_auth_attributes: Optional[Dict] = None,
):
    token_separated = signed_request.split(".")

    if len(token_separated) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The signed_request ({signed_request}) sent is not in the expected format.",
        )

    _, b64_encoded_token = token_separated

    try:
        decoded_token = base64.b64decode(b64_encoded_token)
    except Exception:
        try:
            # Try adding a padding character.
            b64_encoded_token += "=" * (4 - (len(b64_encoded_token) % 4))
            decoded_token = base64.b64decode(b64_encoded_token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not decode the given token: {b64_encoded_token}. Message: {e.orig}",
            )

    decoded_token_dict = json.loads(decoded_token)
    found_user_id = decoded_token_dict.get("user_id")

    # Check the user_id found in the token against the one given
    if found_user_id != facebook_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user_id ({found_user_id}) found in the signed_request does not match the given user_id ({facebook_user_id})",
        )

    # Check the Facebook user_id found in the token against the one already
    # exists in the user.auth_attributes
    if target_auth_attributes and (
        target_auth_attributes.get("user_id") != found_user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user_id ({found_user_id}) found in the signed_request does not match the user's ({target_auth_attributes['user_id']})",
        )

    new_auth_attributes = {
        "user_id": facebook_user_id,
        "signed_request": signed_request,
        "auth_service": "facebook",
    }

    return new_auth_attributes


def validate_access_token(
    service_user_id: str,
    email: str,
    access_token: str,
    auth_service: str,
    *,
    target_auth_attributes: Optional[Dict] = None,
) -> str:
    """
    Validate access_token based on the given auth_service.
    If target_auth_attributes is given, perform necessary confirmation with it.
    If successful, return an auth_attributes.
    """
    new_auth_attributes = {}

    if auth_service == "google":
        new_auth_attributes = validate_google_access_token(
            service_user_id,
            email,
            access_token,
            target_auth_attributes=target_auth_attributes,
        )
    elif auth_service == "facebook":
        new_auth_attributes = validate_facebook_signed_request(
            service_user_id,
            access_token,
            target_auth_attributes=target_auth_attributes,
        )
    else:
        # This should never be called as we already have auth_service Enum
        # validation in place in the model
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The given auth_service({auth_service}) is not supported",
        )

    return json.dumps(new_auth_attributes)
