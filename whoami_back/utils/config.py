from sqlalchemy.engine.url import URL, make_url
from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")


# Database
DB_DRIVER = config("DB_DRIVER", default="postgresql")
DB_HOST = config("DB_HOST", default="0.0.0.0")
DB_PORT = config("DB_PORT", cast=int, default=5432)
DB_USER = config("DB_USER", default="postgres")
DB_PASSWORD = config("DB_PASSWORD", cast=Secret, default=None)
DB_DATABASE = config("DB_DATABASE", default="whoami")
DB_DSN = config(
    "DB_DSN",
    cast=make_url,
    default=URL.create(
        drivername=DB_DRIVER,
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE,
    ),
)
DB_ECHO = config("DB_ECHO", cast=bool, default=True)

# JWT
JWT_SIGNATURE = config("JWT_SIGNATURE", default="mylittlesecret")
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
LOGIN_JWT_EXPIRES_IN_HOURS = config(
    "LOGIN_JWT_EXPIRES_IN_HOURS", cast=int, default=168
)
CONFIRMATION_JWT_EXPIRES_IN_HOURS = config(
    "CONFIRMATION_JWT_EXPIRES_IN_HOURS", cast=int, default=3
)
PASSWORD_RESET_JWT_EXPIRES_IN_HOURS = config(
    "PASSWORD_RESET_JWT_EXPIRES_IN_HOURS", cast=int, default=24
)

# Google
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")

# Sendgrid
SENDGRID_API_KEY = config("SENDGRID_API_KEY")
ADMIN_EMAIL = config("ADMIN_EMAIL")

# Frontend
FE_HOSTS = config("FE_HOSTS").split(",")

# AWS
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
PROFILE_IMAGES_S3_BUCKET = config(
    "PROFILE_IMAGES_S3_BUCKET", default="whoami-profile-images"
)
POST_THUMBNAIL_IMAGES_S3_BUCKET = config(
    "POST_THUMBNAIL_IMAGES_S3_BUCKET", default="whoami-post-thumbnail-images"
)
POST_IMAGES_S3_BUCKET = config("POST_IMAGES_S3_BUCKET", default="whoami-post-images")
BOARD_IMAGES_S3_BUCKET = config(
    "BOARD_IMAGES_S3_BUCKET", default="whoami-board-images"
)

# Task queue
TASK_QUEUE_HOST = config("TASK_QUEUE_HOST", default="http://localhost:8001")
