from whoami_back.api.main import get_app
from whoami_back.utils.db import database

app = get_app()


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
