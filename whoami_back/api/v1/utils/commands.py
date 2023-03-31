import re
from typing import Optional, Tuple

from whoami_back.api.v1.users import commands as user_commands


async def validate_email(
    email: str, *, current_user_email: Optional[str] = None
) -> Tuple[bool, str]:
    if not email:
        return False, "No email provided"

    # Check if the given email matches to the target user's email
    if current_user_email and current_user_email == email:
        return False, "The given email is the target user's email"

    email_already_exists = await user_commands.get_user(email=email)

    if email_already_exists:
        return False, "The given email is already taken"

    return True, ""


async def validate_username(
    username: str, *, current_user_username: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if the username is valid
    - Letters should be all lowercased
    - Numbers allowed
    - `-` or `.` special characters are ONLY allowed
    - 1 <= len(x) <= 20
    """
    if not username:
        return False, "No username provided"

    # Check if the given username matches to the target user's username
    if current_user_username and current_user_username == username:
        return False, "The given username is the target user's username"

    pattern = re.compile("^[a-z\d_.]{1,20}$")  # noqa: W605

    if not pattern.match(username):
        return False, "username format is invalid"

    username_already_exists = await user_commands.username_exists(username)

    if username_already_exists:
        return False, "The given username is already taken"

    return True, ""
