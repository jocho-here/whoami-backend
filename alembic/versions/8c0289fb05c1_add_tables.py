"""add tables

Revision ID: 8c0289fb05c1
Revises:
Create Date: 2021-03-21 17:20:05.762655

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from whoami_back.api.v1.notifications.resources import actions

# revision identifiers, used by Alembic.
revision = "8c0289fb05c1"
down_revision = None
branch_labels = None
depends_on = None

# Enums
board_view_type_enum = postgresql.ENUM("board", "stack", name="board_view_type_enum")
background_image_fitting_mode_enum = postgresql.ENUM(
    "fill", "fit", "center", name="background_image_fitting_mode_enum"
)


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.create_table(
        "user",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "board_view_type",
            board_view_type_enum,
            server_default="board",
            nullable=False,
        ),
        sa.Column("email", sa.Text(), unique=True, index=True, nullable=False),
        sa.Column("unconfirmed_new_email", sa.Text()),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("password", sa.Text()),
        sa.Column("auth_attributes", sa.JSON()),
        sa.Column("confirmed", sa.Boolean(), server_default="f", nullable=False),
        sa.Column("public", sa.Boolean(), server_default="t", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="t", nullable=False),
        sa.Column("username", sa.Text(), unique=True, index=True, nullable=False),
        sa.Column("bio", sa.Text()),
        sa.Column("profile_image_s3_uri", sa.Text()),
        sa.Column("profile_background_s3_uri", sa.Text()),
        sa.Column(
            "failed_login_attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "check_user_one_authentication_method",
        "user",
        "((password IS NOT NULL)::INT + (auth_attributes IS NOT NULL)::INT) <= 1",
    )
    op.execute(
        """
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE INDEX username_search_idx ON "user" USING GIN (username gin_trgm_ops);
CREATE INDEX full_name_search_idx ON "user" USING GIN (LOWER(first_name || ' ' || last_name) gin_trgm_ops);
    """
    )

    op.create_table(
        "follow",
        sa.Column(
            "following_user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "followed_user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("approved", sa.Boolean(), server_default="f", nullable=False),
        sa.UniqueConstraint("following_user_id", "followed_user_id"),
        sa.CheckConstraint("following_user_id != followed_user_id"),
    )

    op.create_table(
        "post",
        # General post data
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        # Made content_uri nullable so we could use this table for whoami posts too
        sa.Column("content_uri", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("thumbnail_image_uri", sa.Text()),
        sa.Column("title", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("post_image_s3_uri", sa.Text()),
        sa.Column("b64_favicon", postgresql.BYTEA()),
        # Geometric data
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("scale", sa.Float(), nullable=False),
    )
    op.create_table(
        "linked_profile",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("profile_link", sa.Text(), nullable=False),
        sa.Column("link_label", sa.Text()),
    )

    op.create_table(
        "notification_action",
        sa.Column(
            "id",
            postgresql.UUID(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
    )

    op.execute(actions.get_insert_actions_query_text())

    op.create_table(
        "notification",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "triggering_user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "action_id",
            postgresql.UUID(),
            sa.ForeignKey("notification_action.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("uri_destination", sa.Text()),
        sa.Column(
            "read", sa.Boolean(), server_default="f", index=True, nullable=False
        ),
        sa.CheckConstraint("triggering_user_id != target_user_id"),
    )

    op.create_table(
        "board",
        sa.Column(
            "user_id",
            postgresql.UUID(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("background_image_s3_uri", sa.Text()),
        sa.Column(
            "background_image_fitting_mode", background_image_fitting_mode_enum
        ),
        sa.Column("background_hex_color", sa.Text()),
    )
    op.create_check_constraint(
        "check_image_fitting_mode_present_when_image_present",
        "board",
        "((background_image_s3_uri IS NOT NULL)::INT = (background_image_fitting_mode IS NOT NULL)::INT)",
    )


def downgrade():
    op.drop_table("board")
    op.drop_table("notification")
    op.drop_table("notification_action")
    op.drop_table("follow")
    op.drop_table("linked_profile")
    op.drop_table("post")

    op.drop_index("username_search_idx")
    op.drop_index("full_name_search_idx")
    op.execute(
        """
DROP EXTENSION IF EXISTS pg_trgm;
DROP EXTENSION IF EXISTS btree_gin;
    """
    )
    op.drop_table("user")

    board_view_type_enum.drop(op.get_bind())
    background_image_fitting_mode_enum.drop(op.get_bind())
