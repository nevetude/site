"""nicknames, edits and views

Revision ID: ef742d728482
Revises: 6a4e568ecef9
Create Date: 2026-10-23 05:38:09.998790

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef742d728482"
down_revision: str | Sequence[str] | None = "6a4e568ecef9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The views the site reads: the tables of the catalog with the edits (`models/edits.py`) laid over them. Written out
# here and not made from the models, so that this migration stays what it was whatever the models become.
ALBUM_COLUMNS = [
    "id",
    "genius_id",
    "name",
    "variant",
    "base_name",
    "disambiguator",
    "album_type",
    "import_state",
    "language",
    "release_date",
    "release_date_precision",
    "is_released",
    "description",
    "genius_url",
    "cover_url",
    "cover_thumbnail_url",
    "cover_primary_color",
    "cover_secondary_color",
    "view_count",
    "genius_updated_at",
    "created_at",
    "updated_at",
]
ALBUM_EDITED = [
    "base_name",
    "variant",
    "album_type",
    "is_released",
    "release_date",
    "release_date_precision",
    "cover_url",
    "cover_thumbnail_url",
    "cover_primary_color",
    "cover_secondary_color",
    "description",
]
ARTIST_COLUMNS = [
    "id",
    "genius_id",
    "name",
    "base_name",
    "disambiguator",
    "artist_type",
    "import_state",
    "description",
    "real_name",
    "genius_url",
    "cover_url",
    "is_verified",
    "is_meme_verified",
    "followers_count",
    "created_at",
    "updated_at",
]
ARTIST_EDITED = ["disambiguator", "artist_type", "description", "real_name", "cover_url"]
SONG_COLUMNS = [
    "id",
    "genius_id",
    "name",
    "variant",
    "base_name",
    "disambiguator",
    "import_state",
    "language",
    "release_date",
    "release_date_precision",
    "description",
    "recording_location",
    "explicit",
    "instrumental",
    "is_music",
    "hidden",
    "published",
    "lyrics_state",
    "genre_id",
    "genius_url",
    "cover_url",
    "cover_thumbnail_url",
    "cover_primary_color",
    "cover_secondary_color",
    "view_count",
    "genius_updated_at",
    "created_at",
    "updated_at",
]
SONG_EDITED = [
    "base_name",
    "variant",
    "release_date",
    "release_date_precision",
    "cover_url",
    "cover_thumbnail_url",
    "cover_primary_color",
    "cover_secondary_color",
    "description",
    "genre_id",
]


def overlaid(
    view: str, table: str, edit: str, key: str, columns: list[str], edited: list[str]
) -> str:
    """A column that was set by hand is named in `overridden` of the edit row: its value (maybe NULL) wins."""
    selected = ",\n    ".join(
        f"CASE WHEN e.overridden @> ARRAY['{c}'] THEN e.{c} ELSE t.{c} END AS {c}"
        if c in edited
        else f"t.{c}"
        for c in columns
    )
    return (
        f"CREATE VIEW {view} AS SELECT\n    {selected}\n"
        f"FROM {table} t LEFT JOIN {edit} e ON e.{key} = t.id"
    )


ARTIST_MEMBER_VIEW = """
CREATE VIEW artist_member_view AS SELECT
    m.group_id,
    m.member_id,
    coalesce(e.position, m.position) AS position,
    e.start_album_id,
    e.start_song_id,
    e.end_album_id,
    e.end_song_id,
    coalesce(sa.release_date, ss.release_date, e.start_date) AS starts_on,
    CASE WHEN sa.release_date IS NOT NULL THEN sa.release_date_precision
         WHEN ss.release_date IS NOT NULL THEN ss.release_date_precision
         ELSE e.start_precision END AS starts_precision,
    coalesce(ea.release_date, es.release_date, e.end_date) AS ends_on,
    CASE WHEN ea.release_date IS NOT NULL THEN ea.release_date_precision
         WHEN es.release_date IS NOT NULL THEN es.release_date_precision
         ELSE e.end_precision END AS ends_precision,
    coalesce(e.has_left, false) AS has_left
FROM artist_member m
LEFT JOIN artist_member_edit e ON e.group_id = m.group_id AND e.member_id = m.member_id
LEFT JOIN album_view sa ON sa.id = e.start_album_id
LEFT JOIN song_view ss ON ss.id = e.start_song_id
LEFT JOIN album_view ea ON ea.id = e.end_album_id
LEFT JOIN song_view es ON es.id = e.end_song_id
WHERE NOT coalesce(e.removed, false)
"""

ALBUM_TRACK_VIEW = """
CREATE VIEW album_track_view AS SELECT
    t.id,
    t.album_id,
    t.song_id,
    coalesce(e.disc_number, t.disc_number) AS disc_number,
    coalesce(e.position, t.position) AS position,
    t.sort_order,
    t.is_primary
FROM album_track t LEFT JOIN album_track_edit e ON e.album_track_id = t.id
WHERE NOT coalesce(e.removed, false)
"""


ALBUM_ARTIST_VIEW = """
CREATE VIEW album_artist_view AS SELECT
    a.album_id,
    a.artist_id,
    coalesce(e.position, a.position) AS position
FROM album_artist a
LEFT JOIN album_artist_edit e ON e.album_id = a.album_id AND e.artist_id = a.artist_id
WHERE NOT coalesce(e.removed, false)
"""

SONG_ARTIST_VIEW = """
CREATE VIEW song_artist_view AS SELECT
    a.song_id,
    a.artist_id,
    a.role,
    coalesce(e.position, a.position) AS position
FROM song_artist a
LEFT JOIN song_artist_edit e ON e.song_id = a.song_id AND e.artist_id = a.artist_id AND e.role = a.role
WHERE NOT coalesce(e.removed, false)
"""

SONG_CREDIT_VIEW = """
CREATE VIEW song_credit_view AS SELECT c.id, c.song_id, c.artist_id, c.role_id, c.label_text
FROM song_credit c LEFT JOIN song_credit_edit e ON e.song_credit_id = c.id
WHERE NOT coalesce(e.removed, false)
"""

ALBUM_CREDIT_VIEW = """
CREATE VIEW album_credit_view AS SELECT c.id, c.album_id, c.artist_id, c.role_id, c.label_text
FROM album_credit c LEFT JOIN album_credit_edit e ON e.album_credit_id = c.id
WHERE NOT coalesce(e.removed, false)
"""

SONG_TAG_VIEW = """
CREATE VIEW song_tag_view AS SELECT t.song_id, t.tag_id
FROM song_tag t LEFT JOIN song_tag_edit e ON e.song_id = t.song_id AND e.tag_id = t.tag_id
WHERE NOT coalesce(e.removed, false)
"""


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "album_edit",
        sa.Column("album_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "overridden", sa.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("base_name", sa.String(), nullable=True),
        sa.Column("variant", sa.String(), nullable=True),
        sa.Column(
            "album_type",
            sa.Enum(
                "album",
                "ep",
                "single",
                "compilation",
                "live",
                "mixtape",
                "soundtrack",
                "other",
                name="album_type",
                native_enum=False,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("is_released", sa.Boolean(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column(
            "release_date_precision",
            sa.Enum("year", "month", "day", name="date_precision", native_enum=False, length=40),
            nullable=True,
        ),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("cover_thumbnail_url", sa.String(), nullable=True),
        sa.Column("cover_primary_color", sa.String(), nullable=True),
        sa.Column("cover_secondary_color", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["album_id"], ["album.id"], name=op.f("fk_album_edit_album_id_album")
        ),
        sa.PrimaryKeyConstraint("album_id", name=op.f("pk_album_edit")),
    )
    op.create_table(
        "artist_edit",
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "overridden", sa.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("disambiguator", sa.String(), nullable=True),
        sa.Column(
            "artist_type",
            sa.Enum(
                "person",
                "group",
                "label",
                "other",
                name="artist_type",
                native_enum=False,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("real_name", sa.String(), nullable=True),
        sa.Column("cover_url", sa.String(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["artist_id"], ["artist.id"], name=op.f("fk_artist_edit_artist_id_artist")
        ),
        sa.PrimaryKeyConstraint("artist_id", name=op.f("pk_artist_edit")),
    )
    op.create_table(
        "nickname",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("main", "alter_ego", name="nickname_kind", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artist_id"], ["artist.id"], name=op.f("fk_nickname_artist_id_artist")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nickname")),
    )
    op.create_index(op.f("ix_nickname_artist_id"), "nickname", ["artist_id"], unique=False)
    op.create_table(
        "album_credit_edit",
        sa.Column("album_credit_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["album_credit_id"],
            ["album_credit.id"],
            name=op.f("fk_album_credit_edit_album_credit_id_album_credit"),
        ),
        sa.PrimaryKeyConstraint("album_credit_id", name=op.f("pk_album_credit_edit")),
    )
    op.create_table(
        "artist_member_edit",
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column("member_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("start_album_id", sa.BigInteger(), nullable=True),
        sa.Column("start_song_id", sa.BigInteger(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column(
            "start_precision",
            sa.Enum("year", "month", "day", name="date_precision", native_enum=False, length=40),
            nullable=True,
        ),
        sa.Column("end_album_id", sa.BigInteger(), nullable=True),
        sa.Column("end_song_id", sa.BigInteger(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "end_precision",
            sa.Enum("year", "month", "day", name="date_precision", native_enum=False, length=40),
            nullable=True,
        ),
        sa.Column("has_left", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["end_album_id"], ["album.id"], name=op.f("fk_artist_member_edit_end_album_id_album")
        ),
        sa.ForeignKeyConstraint(
            ["end_song_id"], ["song.id"], name=op.f("fk_artist_member_edit_end_song_id_song")
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["artist.id"], name=op.f("fk_artist_member_edit_group_id_artist")
        ),
        sa.ForeignKeyConstraint(
            ["member_id"], ["artist.id"], name=op.f("fk_artist_member_edit_member_id_artist")
        ),
        sa.ForeignKeyConstraint(
            ["start_album_id"],
            ["album.id"],
            name=op.f("fk_artist_member_edit_start_album_id_album"),
        ),
        sa.ForeignKeyConstraint(
            ["start_song_id"], ["song.id"], name=op.f("fk_artist_member_edit_start_song_id_song")
        ),
        sa.PrimaryKeyConstraint("group_id", "member_id", name=op.f("pk_artist_member_edit")),
    )
    op.create_table(
        "nickname_period",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("nickname_id", sa.BigInteger(), nullable=False),
        sa.Column("start_album_id", sa.BigInteger(), nullable=True),
        sa.Column("start_song_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["nickname_id"], ["nickname.id"], name=op.f("fk_nickname_period_nickname_id_nickname")
        ),
        sa.ForeignKeyConstraint(
            ["start_album_id"], ["album.id"], name=op.f("fk_nickname_period_start_album_id_album")
        ),
        sa.ForeignKeyConstraint(
            ["start_song_id"], ["song.id"], name=op.f("fk_nickname_period_start_song_id_song")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nickname_period")),
    )
    op.create_index(
        op.f("ix_nickname_period_nickname_id"), "nickname_period", ["nickname_id"], unique=False
    )
    op.create_table(
        "nickname_spelling",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("nickname_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["nickname_id"], ["nickname.id"], name=op.f("fk_nickname_spelling_nickname_id_nickname")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nickname_spelling")),
    )
    op.create_index(
        op.f("ix_nickname_spelling_nickname_id"), "nickname_spelling", ["nickname_id"], unique=False
    )
    op.create_table(
        "song_artist_edit",
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("primary", "featured", name="song_artist_role", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["artist_id"], ["artist.id"], name=op.f("fk_song_artist_edit_artist_id_artist")
        ),
        sa.ForeignKeyConstraint(
            ["song_id"], ["song.id"], name=op.f("fk_song_artist_edit_song_id_song")
        ),
        sa.PrimaryKeyConstraint("song_id", "artist_id", "role", name=op.f("pk_song_artist_edit")),
    )
    op.create_table(
        "song_edit",
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "overridden", sa.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("base_name", sa.String(), nullable=True),
        sa.Column("variant", sa.String(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column(
            "release_date_precision",
            sa.Enum("year", "month", "day", name="date_precision", native_enum=False, length=40),
            nullable=True,
        ),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("cover_thumbnail_url", sa.String(), nullable=True),
        sa.Column("cover_primary_color", sa.String(), nullable=True),
        sa.Column("cover_secondary_color", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("genre_id", sa.BigInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["genre_id"], ["genre.id"], name=op.f("fk_song_edit_genre_id_genre")
        ),
        sa.ForeignKeyConstraint(["song_id"], ["song.id"], name=op.f("fk_song_edit_song_id_song")),
        sa.PrimaryKeyConstraint("song_id", name=op.f("pk_song_edit")),
    )
    op.create_table(
        "song_tag_edit",
        sa.Column("song_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["song_id"], ["song.id"], name=op.f("fk_song_tag_edit_song_id_song")
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], name=op.f("fk_song_tag_edit_tag_id_tag")),
        sa.PrimaryKeyConstraint("song_id", "tag_id", name=op.f("pk_song_tag_edit")),
    )
    op.create_table(
        "artist_alias_edit",
        sa.Column("alias_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["alias_id"],
            ["artist_alias.id"],
            name=op.f("fk_artist_alias_edit_alias_id_artist_alias"),
        ),
        sa.PrimaryKeyConstraint("alias_id", name=op.f("pk_artist_alias_edit")),
    )
    op.create_table(
        "album_artist_edit",
        sa.Column("album_id", sa.BigInteger(), nullable=False),
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["album_id"], ["album.id"], name=op.f("fk_album_artist_edit_album_id_album")
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"], ["artist.id"], name=op.f("fk_album_artist_edit_artist_id_artist")
        ),
        sa.PrimaryKeyConstraint("album_id", "artist_id", name=op.f("pk_album_artist_edit")),
    )
    op.create_table(
        "album_track_edit",
        sa.Column("album_track_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("disc_number", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["album_track_id"],
            ["album_track.id"],
            name=op.f("fk_album_track_edit_album_track_id_album_track"),
        ),
        sa.PrimaryKeyConstraint("album_track_id", name=op.f("pk_album_track_edit")),
    )
    op.create_table(
        "nickname_use",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("nickname_id", sa.BigInteger(), nullable=False),
        sa.Column("album_id", sa.BigInteger(), nullable=True),
        sa.Column("song_id", sa.BigInteger(), nullable=True),
        sa.Column("spelling_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["album_id"], ["album.id"], name=op.f("fk_nickname_use_album_id_album")
        ),
        sa.ForeignKeyConstraint(
            ["nickname_id"], ["nickname.id"], name=op.f("fk_nickname_use_nickname_id_nickname")
        ),
        sa.ForeignKeyConstraint(
            ["song_id"], ["song.id"], name=op.f("fk_nickname_use_song_id_song")
        ),
        sa.ForeignKeyConstraint(
            ["spelling_id"],
            ["nickname_spelling.id"],
            name=op.f("fk_nickname_use_spelling_id_nickname_spelling"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nickname_use")),
    )
    op.create_index(op.f("ix_nickname_use_album_id"), "nickname_use", ["album_id"], unique=False)
    op.create_index(
        op.f("ix_nickname_use_nickname_id"), "nickname_use", ["nickname_id"], unique=False
    )
    op.create_index(op.f("ix_nickname_use_song_id"), "nickname_use", ["song_id"], unique=False)
    op.create_table(
        "song_credit_edit",
        sa.Column("song_credit_id", sa.BigInteger(), nullable=False),
        sa.Column("removed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["song_credit_id"],
            ["song_credit.id"],
            name=op.f("fk_song_credit_edit_song_credit_id_song_credit"),
        ),
        sa.PrimaryKeyConstraint("song_credit_id", name=op.f("pk_song_credit_edit")),
    )
    op.create_table(
        "release_series",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("artist_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artist_id"], ["artist.id"], name=op.f("fk_release_series_artist_id_artist")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_release_series")),
    )
    op.create_index(
        op.f("ix_release_series_artist_id"), "release_series", ["artist_id"], unique=False
    )
    op.create_table(
        "release_series_album",
        sa.Column("series_id", sa.BigInteger(), nullable=False),
        sa.Column("album_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["album_id"], ["album.id"], name=op.f("fk_release_series_album_album_id_album")
        ),
        sa.ForeignKeyConstraint(
            ["series_id"],
            ["release_series.id"],
            name=op.f("fk_release_series_album_series_id_release_series"),
        ),
        sa.PrimaryKeyConstraint("series_id", "album_id", name=op.f("pk_release_series_album")),
    )
    op.create_index(
        op.f("ix_release_series_album_album_id"), "release_series_album", ["album_id"], unique=False
    )
    # ### end Alembic commands ###
    op.execute(
        overlaid("album_view", "album", "album_edit", "album_id", ALBUM_COLUMNS, ALBUM_EDITED)
    )
    op.execute(
        overlaid("artist_view", "artist", "artist_edit", "artist_id", ARTIST_COLUMNS, ARTIST_EDITED)
    )
    op.execute(overlaid("song_view", "song", "song_edit", "song_id", SONG_COLUMNS, SONG_EDITED))
    for view in (
        ARTIST_MEMBER_VIEW,
        ALBUM_TRACK_VIEW,
        ALBUM_ARTIST_VIEW,
        SONG_ARTIST_VIEW,
        SONG_CREDIT_VIEW,
        ALBUM_CREDIT_VIEW,
        SONG_TAG_VIEW,
    ):
        op.execute(view)


def downgrade() -> None:
    """Downgrade schema."""
    for view in (
        "song_tag_view",
        "album_credit_view",
        "song_credit_view",
        "song_artist_view",
        "album_artist_view",
        "album_track_view",
        "artist_member_view",
        "song_view",
        "artist_view",
        "album_view",
    ):
        op.execute(f"DROP VIEW {view}")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_release_series_album_album_id"), table_name="release_series_album")
    op.drop_table("release_series_album")
    op.drop_index(op.f("ix_release_series_artist_id"), table_name="release_series")
    op.drop_table("release_series")
    op.drop_table("album_artist_edit")
    op.drop_table("artist_alias_edit")
    op.drop_table("song_credit_edit")
    op.drop_index(op.f("ix_nickname_use_song_id"), table_name="nickname_use")
    op.drop_index(op.f("ix_nickname_use_nickname_id"), table_name="nickname_use")
    op.drop_index(op.f("ix_nickname_use_album_id"), table_name="nickname_use")
    op.drop_table("nickname_use")
    op.drop_table("album_track_edit")
    op.drop_table("song_tag_edit")
    op.drop_table("song_edit")
    op.drop_table("song_artist_edit")
    op.drop_index(op.f("ix_nickname_spelling_nickname_id"), table_name="nickname_spelling")
    op.drop_table("nickname_spelling")
    op.drop_index(op.f("ix_nickname_period_nickname_id"), table_name="nickname_period")
    op.drop_table("nickname_period")
    op.drop_table("artist_member_edit")
    op.drop_table("album_credit_edit")
    op.drop_index(op.f("ix_nickname_artist_id"), table_name="nickname")
    op.drop_table("nickname")
    op.drop_table("artist_edit")
    op.drop_table("album_edit")
    # ### end Alembic commands ###
