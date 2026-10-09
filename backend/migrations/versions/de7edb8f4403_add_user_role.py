"""add user role

Revision ID: de7edb8f4403
Revises: 1e77c883a69e
Create Date: 2026-07-20 18:39:34.832479
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "de7edb8f4403"
down_revision: Union[str, Sequence[str], None] = "1e77c883a69e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Create the PostgreSQL enum
user_role = sa.Enum(
    "CITIZEN",
    "MUNICIPALITY",
    "CONTRACTOR",
    "ADMIN",
    name="userrole",
)


def upgrade() -> None:
    """Upgrade schema."""

    # Create enum type first
    user_role.create(op.get_bind(), checkfirst=True)

    # Add column
    op.add_column(
        "users",
        sa.Column(
            "role",
            user_role,
            nullable=False,
            server_default="CITIZEN",
        ),
    )

    # Remove default for future inserts
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("users", "role")

    # Drop enum type
    user_role.drop(op.get_bind(), checkfirst=True)