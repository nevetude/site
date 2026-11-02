"""where a name tied to a release is the name

Revision ID: b7c1d93a4e52
Revises: ef742d728482
Create Date: 2026-10-31 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1d93a4e52"
down_revision: str | Sequence[str] | None = "ef742d728482"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The names tied to releases before this were the name everywhere on the release: `any`.
    op.add_column(
        "nickname_use",
        sa.Column(
            "scope",
            sa.Enum("artist", "credit", "any", name="nickname_scope", native_enum=False, length=40),
            server_default="any",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("nickname_use", "scope")
