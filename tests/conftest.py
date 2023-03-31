import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from whoami_back.api.asgi import app
from whoami_back.api.v1.users import commands as user_commands
from whoami_back.utils.db import get_async_engine


@pytest.fixture(autouse=True)
async def db_conn():
    mock_engine = get_async_engine()

    async with mock_engine.begin() as mock_conn:
        # Always get the mock_engine
        async_context_manager = MagicMock(name="async_context_manager")
        async_context_manager.__aenter__.return_value = mock_conn
        mock_engine._begin = mock_engine.begin
        mock_engine.begin = MagicMock(return_value=async_context_manager)

        with patch(
            "sqlalchemy.ext.asyncio.create_async_engine",
            AsyncMock(return_value=mock_engine),
        ):
            yield mock_conn
            await mock_conn.close()

        mock_engine.begin = mock_engine._begin


@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for each test case"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def api_client():
    """Create an async API client"""
    async_api_client = AsyncClient(app=app, base_url="http://testserver")
    yield async_api_client
    await async_api_client.aclose()


@pytest.fixture
async def add_user_profile(db_conn):
    async def _add_user_profile(
        user_id: UUID,
        *,
        bio: str = None,
        profile_image_s3_key: str = None,
        profile_background_s3_key: str = None,
    ) -> None:
        # Don't need to assign default values to bio and S3 keys. In this way, we
        # can mimic an empty user_profile creation when we create a new user.
        await db_conn.execute(
            text(
                """
INSERT INTO user_profile (user_id, bio, profile_image_s3_key, profile_background_s3_key)
VALUES (:user_id, :bio, :profile_image_s3_key, :profile_background_s3_key)
                """
            ).bindparams(
                user_id=user_id,
                bio=bio,
                profile_image_s3_key=profile_image_s3_key,
                profile_background_s3_key=profile_background_s3_key,
            )
        )

    return _add_user_profile


@pytest.fixture
async def add_user(db_conn, add_user_profile):
    async def _add_user(
        email: str = "jocho@gmail.com",
        username: str = "jocho",
        first_name: str = "Jo",
        last_name: str = "Cho",
        password: str = "hi",
        confirmed: bool = True,
        public: bool = True,
        active: bool = True,
        _add_user_profile: bool = True,
    ) -> str:
        id_ = uuid4()
        hashed_password = user_commands.hash_password(password)
        await db_conn.execute(
            text(
                """
INSERT INTO \"user\" (id, username, email, first_name, last_name, password, confirmed, public, active)
VALUES (:id, :username, :email, :first_name, :last_name, :password, :confirmed, :public, :active)
                """
            ).bindparams(
                id=id_,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=hashed_password,
                confirmed=confirmed,
                public=public,
                active=active,
            )
        )

        if _add_user_profile:
            await add_user_profile(id_)

        return str(id_)

    return _add_user


@pytest.fixture
async def add_post(db_conn):
    async def _add_post(
        user_id: UUID,
        *,
        created_at: datetime = datetime.now(timezone.utc),
        updated_at: datetime = datetime.now(timezone.utc),
        source: str = "instagram",
        content_uri: str = "https://some_platform.com/some_content",
        title: str = "content_title",
        meta_title: str = "original_title",
        meta_description: str = "original_description",
        width: int = 1,
        height: int = 1,
        scale: float = 1.0,
        x: int = 1,
        y: int = 1,
    ):
        id_ = uuid4()

        await db_conn.execute(
            text(
                """
INSERT INTO post (id, created_at, updated_at, user_id, source, content_uri, title, meta_title, meta_description, width, height, x, y, scale)
VALUES (:id, :created_at, :updated_at, :user_id, :source, :content_uri, :title, :meta_title, :meta_description, :width, :height, :x, :y, :scale)
                """
            ).bindparams(
                id=id_,
                created_at=created_at,
                updated_at=updated_at,
                user_id=user_id,
                source=source,
                content_uri=content_uri,
                title=title,
                meta_title=meta_title,
                meta_description=meta_description,
                width=width,
                height=height,
                scale=scale,
                x=x,
                y=y,
            )
        )

        return str(id_)

    return _add_post


@pytest.fixture
async def add_following(db_conn):
    async def _add_following(
        following_user_id: UUID, followed_user_id: UUID, *, approved: bool = True
    ):
        await db_conn.execute(
            text(
                """
INSERT INTO following (following_user_id, followed_user_id, approved)
VALUES (:following_user_id, :followed_user_id, :approved)
                """
            ).bindparams(
                following_user_id=following_user_id,
                followed_user_id=followed_user_id,
                approved=approved,
            )
        )

    return _add_following
