"""Create the initial Memoria AI relational schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_person_id", "messages", ["person_id"])
    op.create_index("ix_messages_timestamp", "messages", ["timestamp"])

    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("importance", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_memories_person_id", "memories", ["person_id"])
    op.create_index("ix_memories_timestamp", "memories", ["timestamp"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversations_person_id", "conversations", ["person_id"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"])

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_photos_person_id", "photos", ["person_id"])
    op.create_index("ix_photos_timestamp", "photos", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_photos_timestamp", table_name="photos")
    op.drop_index("ix_photos_person_id", table_name="photos")
    op.drop_table("photos")
    op.drop_index("ix_conversation_messages_conversation_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_person_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_memories_timestamp", table_name="memories")
    op.drop_index("ix_memories_person_id", table_name="memories")
    op.drop_table("memories")
    op.drop_index("ix_messages_timestamp", table_name="messages")
    op.drop_index("ix_messages_person_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("people")

