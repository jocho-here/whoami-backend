from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from whoami_back.api.utils.loader import load_modules
from whoami_back.utils.config import FE_HOSTS


def get_app():
    app = FastAPI(title="whoami FastAPI API server")
    load_modules(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=FE_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )

    return app
