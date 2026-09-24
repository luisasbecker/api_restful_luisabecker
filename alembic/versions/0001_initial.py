"""Initial users, tasks, comments and persistent sessions.

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    uuid = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(5), nullable=False),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("updated_at", timestamp, nullable=False),
        sa.Column("deleted_at", timestamp),
        sa.CheckConstraint("role IN ('admin','user','guest')", name="ck_users_role"),
    )
    op.create_table(
        "tasks",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(5000)),
        sa.Column("status", sa.String(11), nullable=False),
        sa.Column("priority", sa.String(6), nullable=False),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", uuid, sa.ForeignKey("users.id")),
        sa.Column("due_at", timestamp),
        sa.Column("completed_at", timestamp),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("updated_at", timestamp, nullable=False),
        sa.Column("deleted_at", timestamp),
        sa.CheckConstraint("status IN ('pending','in_progress','done')", name="ck_tasks_status"),
        sa.CheckConstraint("priority IN ('low','medium','high')", name="ck_tasks_priority"),
        sa.CheckConstraint(
            "(status = 'done' AND completed_at IS NOT NULL) OR "
            "(status <> 'done' AND completed_at IS NULL)",
            name="ck_tasks_completion",
        ),
    )
    op.create_index(
        "ix_tasks_creator_live",
        "tasks",
        ["created_by", "created_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_tasks_assignee_live",
        "tasks",
        ["assigned_to", "created_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_tasks_filters_live",
        "tasks",
        ["status", "priority", "due_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "comments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("task_id", uuid, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("author_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.String(2000), nullable=False),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("deleted_at", timestamp),
    )
    op.create_index(
        "ix_comments_task_live",
        "comments",
        ["task_id", "created_at", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("jti", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", timestamp, nullable=False),
        sa.Column("expires_at", timestamp, nullable=False),
        sa.Column("revoked_at", timestamp),
    )
    op.create_index("ix_sessions_user_expiry", "auth_sessions", ["user_id", "expires_at"])


def downgrade():
    op.drop_index("ix_sessions_user_expiry", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_comments_task_live", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_tasks_filters_live", table_name="tasks")
    op.drop_index("ix_tasks_assignee_live", table_name="tasks")
    op.drop_index("ix_tasks_creator_live", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("users")
