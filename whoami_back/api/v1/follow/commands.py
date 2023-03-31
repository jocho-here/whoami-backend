from typing import Optional

from fastapi.encoders import jsonable_encoder

from whoami_back.api.v1.follow.models import FollowingStatus
from whoami_back.api.v1.notifications.resources.actions import actions_data
from whoami_back.utils.db import database, to_csv, to_ref_csv, to_where_clause

PUBLIC_ACCOUNT_ACTION_ID = actions_data[0]["id_0"]
PRIVATE_ACCOUNT_ACTION_ID = actions_data[1]["id_1"]
ACCEPTED_FOLLOW_ACTION_ID = actions_data[2]["id_2"]


async def get_follower_following_nums(user_id: str):
    values = {"user_id": user_id}
    follower_num_query = """
SELECT
    COUNT(*)
FROM
    follow
WHERE
    followed_user_id = :user_id
    AND approved IS TRUE
    """
    number_of_followers = await database.execute(follower_num_query, values=values)
    following_num_query = """
SELECT
    COUNT(*)
FROM
    follow
WHERE
    following_user_id = :user_id
    AND approved IS TRUE
    """
    number_of_followings = await database.execute(following_num_query, values=values)

    return {
        "number_of_followings": number_of_followings,
        "number_of_followers": number_of_followers,
    }


async def get_follow_requests(followed_user_id: str):
    columns = [
        '"user".id AS user_id',
        '"user".profile_image_s3_uri',
        '"user".username',
    ]
    filters = [
        "follow.followed_user_id = :followed_user_id",
        "follow.approved IS FALSE",
    ]
    select_clause = to_csv(columns)
    where_clause = to_where_clause(filters)
    values = {"followed_user_id": followed_user_id}
    query = f"""
SELECT {select_clause}
FROM follow JOIN "user" ON "user".id = follow.following_user_id
WHERE {where_clause}
    """
    result = await database.fetch_all(query=query, values=values)

    return jsonable_encoder(result)


async def get_followers(followed_user_id: str, current_user_id: str):
    columns = [
        "f_1.following_user_id",
        '"user".profile_image_s3_uri',
        '"user".username',
        """
        (
            SELECT
                f_2.approved
            FROM
                follow f_2
            WHERE
                f_2.following_user_id = :current_user_id
                AND f_2.followed_user_id = f_1.following_user_id
        ) AS follow_status
        """,
    ]

    conditions = ["f_1.followed_user_id = :followed_user_id"]

    # If current user is looking at someone else's followers list,
    #  ONLY show approved followers, not the requested ones.
    # If current user is looking at the user's followers list,
    #  show follow requests AS WELL
    if followed_user_id != current_user_id:
        conditions.append("f_1.approved IS TRUE")
    else:
        columns.append("f_1.approved")

    select_clause = to_csv(columns)
    where_clause = to_where_clause(conditions)

    query = f"""
SELECT {select_clause}
FROM follow f_1
JOIN "user" ON "user".id = f_1.following_user_id
WHERE {where_clause}
    """

    result = await database.fetch_all(
        query=query,
        values={
            "followed_user_id": followed_user_id,
            "current_user_id": current_user_id,
        },
    )

    followers = jsonable_encoder(result)

    for row in followers:
        row["user"] = {
            "id": row.pop("following_user_id"),
            "profile_image_s3_uri": row.pop("profile_image_s3_uri"),
            "username": row.pop("username"),
        }
        row["current_user_following_status"] = determine_following_status(
            row.pop("follow_status")
        )

    return followers


async def get_followed_users(following_user_id: str, current_user_id: str):
    where_clause = """
WHERE
    f_1.following_user_id = :following_user_id
    """

    # If current user is looking at someone else's following list,
    #  ONLY show approved ones, not the requested ones.
    if following_user_id != current_user_id:
        where_clause += """
AND
    f_1.approved IS TRUE
        """

    query = """
SELECT
    f_1.followed_user_id,
    "user".profile_image_s3_uri,
    "user".username,
    (
        SELECT
            f_2.approved
        FROM
            follow f_2
        WHERE
            f_2.following_user_id = :current_user_id
            AND f_2.followed_user_id = f_1.followed_user_id
    ) AS follow_status
FROM
    follow f_1
JOIN
    "user" ON "user".id = f_1.followed_user_id
WHERE
    f_1.following_user_id = :following_user_id
    """

    result = await database.fetch_all(
        query=query,
        values={
            "following_user_id": following_user_id,
            "current_user_id": current_user_id,
        },
    )

    followed_users = jsonable_encoder(result)

    for row in followed_users:
        row["user"] = {
            "id": row.pop("followed_user_id"),
            "profile_image_s3_uri": row.pop("profile_image_s3_uri"),
            "username": row.pop("username"),
        }
        row["current_user_following_status"] = determine_following_status(
            row["follow_status"]
        )

    return followed_users


async def follow_user(
    following_user_id: str, followed_user_id: str, is_followed_user_public: bool
):
    """
    Create a row in the follow table using the given users.
    If the followed user is a private account, create a "requested
    to follow" notification on the followed_user_id.
    If the followed user is a public account, create a "started following"
    notification on the followed_user_id.
    """
    # Create a row in the follow
    query = """
INSERT INTO follow (
    following_user_id,
    followed_user_id,
    approved
)
SELECT
    :following_user_id,
    :followed_user_id,
    "user".public
FROM
    "user"
WHERE
    id = :followed_user_id
    """
    values = {
        "following_user_id": following_user_id,
        "followed_user_id": followed_user_id,
    }
    await database.execute(query=query, values=values)

    # Populate notification table
    values = {
        "triggering_user_id": following_user_id,
        "target_user_id": followed_user_id,
    }

    if is_followed_user_public:
        values["action_id"] = PUBLIC_ACCOUNT_ACTION_ID
    else:
        values["action_id"] = PRIVATE_ACCOUNT_ACTION_ID

    value_statement = to_ref_csv(values.keys())

    query = f"""
INSERT INTO notification (
    triggering_user_id,
    target_user_id,
    action_id
)
VALUES ({value_statement})
    """

    await database.execute(query=query, values=values)


async def delete_follow(unfollowing_user_id: str, unfollowed_user_id: str):
    query = """
DELETE FROM
    follow
WHERE
    following_user_id = :unfollowing_user_id
    AND followed_user_id = :unfollowed_user_id
    """
    values = {
        "unfollowing_user_id": unfollowing_user_id,
        "unfollowed_user_id": unfollowed_user_id,
    }
    await database.execute(query=query, values=values)


async def approve_following(following_user_id: str, followed_user_id: str):
    """
    Approve following of a private account (followed_user_id).
    Populate a notification on the user with following_user_id saying
    "accepted your follow request"
    """
    query = """
UPDATE
    follow
SET
    approved = TRUE
WHERE
    following_user_id = :following_user_id
    AND followed_user_id = :followed_user_id
    """
    values = {
        "following_user_id": following_user_id,
        "followed_user_id": followed_user_id,
    }
    await database.execute(query=query, values=values)

    # Populate notification table
    values = {
        "triggering_user_id": followed_user_id,
        "target_user_id": following_user_id,
        "action_id": ACCEPTED_FOLLOW_ACTION_ID,
    }

    value_statement = to_ref_csv(values.keys())

    query = f"""
INSERT INTO notification (
    triggering_user_id,
    target_user_id,
    action_id
)
VALUES ({value_statement})
    """
    await database.execute(query=query, values=values)


async def check_approved_following(
    following_user_id: str, followed_user_id: str
) -> bool:
    query = """
SELECT EXISTS(
    SELECT TRUE
    FROM follow
    WHERE following_user_id = :following_user_id
        AND followed_user_id = :followed_user_id
        AND approved IS TRUE
)
    """
    values = {
        "following_user_id": following_user_id,
        "followed_user_id": followed_user_id,
    }
    result = await database.execute(query=query, values=values)

    return result


def determine_following_status(following_approval_status: Optional[bool]):
    if following_approval_status is None:
        return FollowingStatus.NOT_FOLLOWING
    elif following_approval_status is False:
        return FollowingStatus.REQUESTED
    else:
        return FollowingStatus.FOLLOWING
