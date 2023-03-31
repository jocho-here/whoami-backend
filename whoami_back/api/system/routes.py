from fastapi import APIRouter, Response

from whoami_back.utils.db import database

router = APIRouter()


@router.get("/ping")
async def ping():
    """
    This endpoint is used to check if the API server is alive.
    """
    return Response("pong")


@router.get("/deep-ping")
async def deep_ping():
    """
    This endpoint is used to check if the API server is able to execute DB queries.
    """
    result = await database.execute(query="SELECT now()")
    print(f"Deep pinged at {result}")

    return Response(str(result))


def add_router(app):
    app.include_router(router)
