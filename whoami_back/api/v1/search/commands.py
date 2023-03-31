from fastapi.encoders import jsonable_encoder

from whoami_back.utils.db import database


async def get_users_closest_to_keyword(keyword: str, *, limit: int = 20):
    values = {"keyword": keyword, "limit": limit}

    username_query = _get_search_query()
    users_with_closest_username = await database.fetch_all(
        query=username_query, values=values
    )

    full_name_query = _get_search_query(target_column="full_name")
    users_with_closest_full_name = await database.fetch_all(
        query=full_name_query, values=values
    )

    closest_users = []
    user_ids = set([])
    username_index = 0
    full_name_index = 0

    while len(user_ids) < limit and (
        username_index < len(users_with_closest_username)
        or full_name_index < len(users_with_closest_full_name)
    ):
        # 1. Determine which user to add
        if username_index == len(users_with_closest_username):
            # we've hit the end of username. Take the full_name user
            user_to_add = users_with_closest_full_name[full_name_index]
            full_name_index += 1
        elif full_name_index == len(users_with_closest_full_name):
            user_to_add = users_with_closest_username[username_index]
            username_index += 1
        else:
            username_user = users_with_closest_username[username_index]
            full_name_user = users_with_closest_full_name[full_name_index]

            if username_user["distance"] < full_name_user["distance"]:
                user_to_add = username_user
                username_index += 1
            elif username_user["distance"] > full_name_user["distance"]:
                user_to_add = full_name_user
                full_name_index += 1
            elif username_index < full_name_index:
                # Distances are same; pick the one with lower index
                user_to_add = username_user
                username_index += 1
            else:
                user_to_add = full_name_user
                full_name_index += 1

        # We can safely assume that if we've seen the user_to_add already,
        #  it must have closer distance to the keyword.
        if str(user_to_add["id"]) not in user_ids:
            closest_users.append(user_to_add)
            user_ids.add(str(user_to_add["id"]))

    return jsonable_encoder(closest_users)


async def get_users_with_closest_username(keyword: str, limit: int):
    values = {"keyword": keyword, "limit": limit}
    query = _get_search_query()
    closest_users = await database.fetch_all(query=query, values=values)

    return jsonable_encoder(closest_users)


async def get_users_with_closest_full_name(keyword: str, limit: int):
    values = {"keyword": keyword, "limit": limit}
    query = _get_search_query(target_colum="full_name")
    closest_users = await database.fetch_all(query=query, values=values)

    return jsonable_encoder(closest_users)


def _get_search_query(target_column: str = "username"):
    target_column_statement = ""

    if target_column == "full_name":
        target_column_statement = "first_name || ' ' || last_name"
    else:
        # For now, we are defaulting to username
        target_column_statement = '"user".username'

    query = f"""
SELECT
    "user".id,
    "user".username,
    "user".profile_image_s3_uri,
    "user".first_name,
    "user".last_name,
    LOWER({target_column_statement}) <-> LOWER(:keyword) AS distance
FROM
    "user"
WHERE
    "user".active IS TRUE
    AND "user".confirmed IS TRUE
ORDER BY distance
LIMIT :limit;
    """

    return query
