from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder

from whoami_back.api.v1.users import commands as user_commands
from whoami_back.api.v1.utils.commands import validate_email
from whoami_back.utils.config import CONFIRMATION_JWT_EXPIRES_IN_HOURS, FE_HOSTS
from whoami_back.utils.db import database, to_csv, to_ref_csv

# Initialize shared objects
FE_HOST = FE_HOSTS[0]


class EMAIL_TEMPLATE_IDS:
    CONFIRM_DEACTIVATE_ACCOUNT = "d-5a2d7e82d53e4781972a916aead481d4"
    CONFIRM_DELETE_ACCOUNT = "d-a6481a6b8f7a496d921ffbf2badead3a"
    ACCOUNT_DEACTIVATED = "d-f411e7162d8a47f68d96b0f1b1599f7c"
    ACCOUNT_DELETED = "d-8ace21756e5d4d1fad53282d7d9405d5"


async def send_deactivate_account_confirmation_email(
    user_id: str, email: str, background_tasks
) -> None:
    user_token = await user_commands.create_access_token(
        user_id, CONFIRMATION_JWT_EXPIRES_IN_HOURS
    )
    deactivate_account_link = (
        f"{FE_HOST}/users/deactivate/confirm?token={user_token}"
    )
    background_tasks.add_task(
        user_commands.send_email,
        email,
        EMAIL_TEMPLATE_IDS.CONFIRM_DEACTIVATE_ACCOUNT,
        deactivate_account_link,
    )


async def send_delete_account_confirmation_email(
    user_id: str, email: str, background_tasks
) -> None:
    user_token = await user_commands.create_access_token(
        user_id, CONFIRMATION_JWT_EXPIRES_IN_HOURS
    )
    delete_account_link = f"{FE_HOST}/users/delete/confirm?token={user_token}"
    background_tasks.add_task(
        user_commands.send_email,
        email,
        EMAIL_TEMPLATE_IDS.CONFIRM_DELETE_ACCOUNT,
        delete_account_link,
    )


def send_account_deleted_email(email: str, background_tasks) -> None:
    background_tasks.add_task(
        user_commands.send_email,
        email,
        EMAIL_TEMPLATE_IDS.ACCOUNT_DELETED,
        FE_HOST,
    )


def send_account_deactivated_email(email: str, background_tasks) -> None:
    background_tasks.add_task(
        user_commands.send_email,
        email,
        EMAIL_TEMPLATE_IDS.ACCOUNT_DEACTIVATED,
        FE_HOST,
    )


async def update_account_privacy(user_id: str, public: bool):
    query = """
UPDATE \"user\"
SET
    public = :public,
    updated_at = NOW()
WHERE id = :user_id
    """
    values = {"user_id": user_id, "public": public}
    await database.execute(query=query, values=values)


async def get_linked_profiles(user_id: str):
    """
    Return social media profiles of the given user
    """
    keys = ["source", "profile_link", "link_label"]
    select_statement = to_csv(keys)
    query = f"""
SELECT {select_statement}
FROM
    linked_profile
WHERE
    user_id = :user_id
ORDER BY
    created_at ASC
    """
    result = await database.fetch_all(query=query, values={"user_id": user_id})

    return jsonable_encoder(result)


async def update_linked_profiles(user_id: str, linked_profiles: List[Dict]):
    """
    Replace present social media profiles of the user with what's given
    """
    query = """
DELETE FROM linked_profile
WHERE user_id = :user_id
    """
    values = {"user_id": user_id}

    # First, remove all
    await database.execute(query=query, values=values)

    # Then add the given profiles if any
    if linked_profiles:
        columns = [
            "user_id",
            "source",
            "profile_link",
            "link_label",
            "created_at",
            "updated_at",
        ]
        values = []
        values_references = {}

        # Set created_at and updated_at times differently so we could be consistent
        #  with their orders
        current_time = datetime.now(timezone.utc)
        for i, linked_profile in enumerate(linked_profiles):
            profile_time = current_time + timedelta(seconds=i)
            linked_profile["created_at"] = profile_time
            linked_profile["updated_at"] = profile_time
            linked_profile["user_id"] = user_id
            ith_refs = []

            for c in columns:
                reference_key = f"{c}_{i}"
                values_references[reference_key] = linked_profile[c]
                ith_refs.append(reference_key)

            current_value_statement = f"({to_ref_csv(ith_refs)})"
            values.append(current_value_statement)

        insert_statement = to_csv(columns)
        value_statement = to_csv(values)

        query = f"""
INSERT INTO linked_profile ({insert_statement})
VALUES {value_statement}
        """
        await database.execute(query=query, values=values_references)


async def delete_user(user_id: str) -> None:
    query = """
DELETE FROM \"user\"
WHERE id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})


async def deactivate_user(user_id: str) -> None:
    query = """
UPDATE \"user\"
SET
    active = FALSE,
    updated_at = NOW()
WHERE id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})


async def initiate_email_update(
    user_id: str, current_email: str, new_email: str
) -> None:
    valid, reason = await validate_email(new_email, current_user_email=current_email)

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    query = """
UPDATE
    \"user\"
SET
    unconfirmed_new_email = :new_email,
    updated_at = NOW()
WHERE
    id = :user_id
    """
    values = {"user_id": user_id, "new_email": new_email}
    await database.execute(query=query, values=values)


async def confirm_new_email(user_id: str) -> None:
    query = """
UPDATE
    \"user\"
SET
    email = unconfirmed_new_email,
    unconfirmed_new_email = null,
    updated_at = NOW()
WHERE
    id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})


async def cancel_email_update(user_id: str) -> None:
    query = """
UPDATE
    \"user\"
SET
    unconfirmed_new_email = null,
    updated_at = NOW()
WHERE
    id = :user_id
    """
    await database.execute(query=query, values={"user_id": user_id})


async def update_password(user_id: str, new_password: str) -> None:
    valid, message = user_commands.validate_password(new_password)

    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    query = """
UPDATE \"user\"
SET
    password = :new_hashed_password,
    updated_at = NOW(),
    failed_login_attempt_count = 0
WHERE id = :user_id
    """
    values = {
        "user_id": user_id,
        "new_hashed_password": user_commands.hash_password(new_password),
    }
    await database.execute(query=query, values=values)


def confirm_password(given_password: str, correct_hashed_password: str):
    """
    Raise an exception if not matching
    """
    if not user_commands.verify_password(given_password, correct_hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password"
        )
