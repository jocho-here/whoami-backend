from typing import List

from fastapi.encoders import jsonable_encoder

from whoami_back.api.v1.follow.commands import determine_following_status
from whoami_back.utils.db import database, to_ref_csv


async def get_latest_notifications(user_id: str):
    # Decide if we need to return all unreads or the latest 10 notifications
    values = {"user_id": user_id}
    query = """
SELECT COUNT(*)
FROM notification
WHERE target_user_id = :user_id
    AND read IS FALSE
    """
    number_of_unreads = await database.execute(query, values=values)

    if number_of_unreads > 10:
        where_clause_supplement = "AND notification.read IS FALSE"
        limit_clause = ""
    else:
        where_clause_supplement = ""
        limit_clause = "LIMIT 10"

    query = f"""
SELECT
    notification.id,
    notification.updated_at,
    notification.read,
    notification.action_id,
    notification.triggering_user_id,
    notification_action.message,
    "user".username,
    "user".profile_image_s3_uri,
    (
        SELECT
            approved
        FROM
            follow
        WHERE
            follow.following_user_id = :user_id
            AND follow.followed_user_id = notification.triggering_user_id
    ) AS current_user_following_status
FROM notification
JOIN notification_action ON notification_action.id = notification.action_id
JOIN "user" ON "user".id = notification.triggering_user_id
WHERE notification.target_user_id = :user_id
    {where_clause_supplement}
ORDER BY notification.updated_at desc
{limit_clause}
    """

    result = await database.fetch_all(
        query=query,
        values={"user_id": user_id},
    )

    result = jsonable_encoder(result)

    for row in result:
        row["triggering_user"] = {
            "id": row.pop("triggering_user_id"),
            "profile_image_s3_uri": row.pop("profile_image_s3_uri"),
            "username": row.pop("username"),
            "current_user_following_status": determine_following_status(
                row.pop("current_user_following_status")
            ),
        }
        row["action"] = {
            "id": row.pop("action_id"),
            "message": row.pop("message"),
        }

    return result


async def mark_notifications_read(user_id: str, notification_ids: List):
    values = {f"notification_id_{i}": _id for i, _id in enumerate(notification_ids)}
    id_refs = to_ref_csv(values.keys())
    values["user_id"] = user_id
    query = f"""
UPDATE notification
SET
    read = TRUE,
    updated_at = NOW()
WHERE target_user_id = :user_id AND id in ({id_refs})
    """

    await database.execute(query, values=values)


async def update_notification_action(
    user_id: str, notification_id: str, new_action_id: str
):
    # First update the given notification
    values = {
        "user_id": user_id,
        "notification_id": notification_id,
        "new_action_id": new_action_id,
    }

    query = """
UPDATE notification
SET
    action_id = :new_action_id,
    updated_at = NOW()
WHERE target_user_id = :user_id AND id = :notification_id
    """

    await database.execute(query, values=values)

    # Then get the updated notification
    values.pop("new_action_id")
    query = """
SELECT
    notification.id,
    notification.updated_at,
    notification.read,
    notification.action_id,
    notification.triggering_user_id,
    notification_action.message,
    "user".username,
    "user".profile_image_s3_uri,
    (
        SELECT
            approved
        FROM
            follow
        WHERE
            follow.following_user_id = :user_id
            AND follow.followed_user_id = notification.triggering_user_id
    ) AS current_user_following_status
FROM notification
JOIN notification_action ON notification_action.id = notification.action_id
JOIN "user" ON "user".id = notification.triggering_user_id
WHERE notification.target_user_id = :user_id
    AND notification.id = :notification_id
    """

    result = await database.fetch_one(query, values=values)
    result = jsonable_encoder(result)

    result["triggering_user"] = {
        "id": result.pop("triggering_user_id"),
        "profile_image_s3_uri": result.pop("profile_image_s3_uri"),
        "username": result.pop("username"),
        "current_user_following_status": determine_following_status(
            result.pop("current_user_following_status")
        ),
    }
    result["action"] = {
        "id": result.pop("action_id"),
        "message": result.pop("message"),
    }

    return result
