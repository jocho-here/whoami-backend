from fastapi import APIRouter

from whoami_back.api.v1.search import base_url, commands

router = APIRouter(prefix=f"{base_url}", tags=["search"])


@router.get("")
async def get_twenty_users_closest_to_keyword(keyword: str):
    """
    Return the 20 users that have closest username or full name to the keyword
    provided
    """

    closest_users = await commands.get_users_closest_to_keyword(keyword)

    return closest_users


def add_router(app):
    app.include_router(router)
