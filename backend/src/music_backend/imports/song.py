from datetime import date
from typing import TYPE_CHECKING, Any

from music_backend.enums import (
    DatePrecision,
    ImportKind,
    ImportState,
    SongArtistRole,
    SongRelationType,
)
from music_backend.imports.client import GeniusError
from music_backend.imports.common import (
    Context,
    Follow,
    Task,
    add_credits,
    add_if_missing,
    description_of,
    find_or_insert,
    find_placement,
    from_unix,
    get_or_create_album_stub,
    get_or_create_artist_stub,
    get_or_create_song_stub,
    is_released,
    log_changes,
    partial_date,
    upsert,
)
from music_backend.models import (
    AlbumArtist,
    AlbumTrack,
    Genre,
    Song,
    SongArtist,
    SongAudio,
    SongCredit,
    SongRelationship,
    SongTag,
    SongVideo,
    Tag,
)
from music_backend.names import split_name

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Same idea as for albums: Genius lists each relation from both sides, we store it once.
RELATIONS: dict[str, tuple[SongRelationType, bool]] = {
    "samples": (SongRelationType.SAMPLES, False),
    "sampled_in": (SongRelationType.SAMPLES, True),
    "interpolates": (SongRelationType.INTERPOLATES, False),
    "interpolated_by": (SongRelationType.INTERPOLATES, True),
    "cover_of": (SongRelationType.COVER_OF, False),
    "covered_by": (SongRelationType.COVER_OF, True),
    "remix_of": (SongRelationType.REMIX_OF, False),
    "remixed_by": (SongRelationType.REMIX_OF, True),
    "live_version_of": (SongRelationType.LIVE_VERSION_OF, False),
    "performed_live_as": (SongRelationType.LIVE_VERSION_OF, True),
    "translation_of": (SongRelationType.TRANSLATION_OF, False),
    "translations": (SongRelationType.TRANSLATION_OF, True),
}


async def handle_song(ctx: Context, session: AsyncSession, task: Task) -> list[Task]:
    """The song with its artists, credits, tags, links and relations. Queues every artist found
    (each walks to its groups); related songs and the song's albums are stubs."""
    path = f"/songs/{task.genius_id}"
    try:
        raw = (await ctx.get(path, hold_403=True))["song"]
        closed = False
    except GeniusError as error:
        # A closed song ("Missing Lyrics") is 403 to anonymous users. The owner of a user token reads it from the official
        # API, which gives fewer fields: see `_closed_facts`. The 403 is in the log only when that does not help.
        if error.status_code != 403 or not ctx.client.has_token:
            raise
        try:
            raw = (await ctx.get(path, official=True))["song"]
        except GeniusError:
            if error.held:
                await ctx.log(error.held)
            raise
        closed = True
    name = split_name(raw["title"])
    facts = _closed_facts(raw) if closed else await _full_facts(session, raw)
    stats = raw["stats"]

    song, changes = await upsert(
        session,
        Song,
        task.genius_id,
        {
            "name": raw["title"],
            "base_name": name.base_name,
            "disambiguator": name.disambiguator,
            "variant": name.variant,
            "language": raw["language"],
            "description": description_of(raw["description"]["dom"]),
            "recording_location": raw["recording_location"],
            "lyrics_state": raw["lyrics_state"],
            "genius_url": raw["url"],
            "cover_url": raw["song_art_image_url"],
            "cover_thumbnail_url": raw["song_art_image_thumbnail_url"],
            "cover_primary_color": raw["song_art_primary_color"],
            "cover_secondary_color": raw["song_art_secondary_color"],
            "view_count": stats.get("pageviews"),  # Genius leaves it out for most songs
            "import_state": ImportState.FULL,
            **facts,
        },
    )

    artists: list[dict[str, Any]] = []
    for role, key in (
        (SongArtistRole.PRIMARY, "primary_artists"),
        (SongArtistRole.FEATURED, "featured_artists"),
    ):
        for position, artist in enumerate(raw[key], start=1):
            stub = await get_or_create_artist_stub(session, artist)
            await add_if_missing(
                session,
                SongArtist,
                {"song_id": song.id, "artist_id": stub.id, "role": role},
                position=position,
            )
            artists.append(artist)

    credit_groups = [
        {"label": "Writer", "artists": raw["writer_artists"]},
        {"label": "Producer", "artists": raw["producer_artists"]},
        *raw["custom_performances"],
    ]
    artists += await add_credits(session, SongCredit, {"song_id": song.id}, credit_groups)

    for tag in [] if closed else raw["tags"]:
        row = await _dictionary_row(session, Tag, tag)
        await add_if_missing(session, SongTag, {"song_id": song.id, "tag_id": row.id})

    for relation in raw["song_relationships"]:
        relation_type, inverted = RELATIONS[relation["relationship_type"]]
        for other in relation["songs"]:
            other_song = await get_or_create_song_stub(session, other)
            source, target = (other_song, song) if inverted else (song, other_song)
            await add_if_missing(
                session,
                SongRelationship,
                {"song_id": source.id, "related_song_id": target.id, "type": relation_type},
            )

    for media in raw["media"]:
        if media["type"] == "video":
            await add_if_missing(
                session,
                SongVideo,
                {"song_id": song.id, "url": media["url"]},
                start_seconds=media.get("start"),
            )
        else:
            await add_if_missing(
                session,
                SongAudio,
                {"song_id": song.id, "provider": media["provider"], "url": media["url"]},
                native_uri=media.get("native_uri"),  # not every provider has these two
                attribution=media.get("attribution"),
            )

    if not closed:  # the albums of a closed song place it themselves: their tracklists name it
        await _save_placements(session, song, raw)

    await log_changes(session, "song", song, raw, changes)
    # Any artist found, credits included, walks both ways: a person to its groups, a group to its members (a group that
    # only walked to its groups would keep its own members as stubs). With `RELATED` every other album the song is on
    # is imported in full too, with its tracks, one level: those tracks do not bring their albums (`Follow.NONE`), or
    # the walk would go through compilations to the whole of Genius. The runner keeps these albums for the end of the job.
    queued = [Task(ImportKind.ARTIST, a["id"], Follow.ALL, name=a["name"]) for a in artists]
    if Follow.RELATED in task.follow and not closed:
        queued += [
            Task(ImportKind.ALBUM, a["id"], Follow.NONE, name=a["name"]) for a in raw["albums"]
        ]
    return queued


async def _full_facts(session: AsyncSession, raw: dict[str, Any]) -> dict[str, Any]:
    release_date, precision = partial_date(raw["release_date_components"])
    genre = await _dictionary_row(session, Genre, raw["primary_tag"])
    return {
        "release_date": release_date,
        "release_date_precision": precision,
        "explicit": raw["explicit"],
        "instrumental": raw["instrumental"],
        "is_music": raw["is_music"],
        "hidden": raw["hidden"],
        "published": raw["published"],
        "genre_id": genre.id,
        "genius_updated_at": from_unix(raw["updated_at"]),
    }


def _closed_facts(raw: dict[str, Any]) -> dict[str, Any]:
    """What the official API gives for a closed song: the date as a text (how much of it is known is in the text it is
    shown as) and none of the flags, the genre and the time of the last change; they stay empty."""
    text, shown = raw["release_date"], raw["release_date_for_display"]
    precision = (
        None
        if text is None
        else DatePrecision.YEAR
        if shown.isdigit()
        else DatePrecision.DAY
        if "," in shown
        else DatePrecision.MONTH
    )
    return {
        "release_date": date.fromisoformat(text) if text else None,
        "release_date_precision": precision,
    }


async def _dictionary_row(
    session: AsyncSession, model: type[Genre] | type[Tag], raw: dict[str, Any]
) -> Any:
    """The genre or tag with this Genius id; created the first time it is seen."""
    name = split_name(raw["name"])
    return await find_or_insert(
        session,
        model,
        {"genius_id": raw["id"]},
        name=raw["name"],
        base_name=name.base_name,
        disambiguator=name.disambiguator,
    )


async def _save_placements(session: AsyncSession, song: Song, raw: dict[str, Any]) -> None:
    """The albums the song is on. Genius gives no track numbers here, so a placement is created
    without a position; the album's own import fills it in."""
    primary_id = raw["album"]["id"] if raw["album"] else None  # singles have no album
    for raw_album in raw["albums"]:
        release_date, precision = partial_date(raw_album["release_date_components"])
        album = await get_or_create_album_stub(
            session,
            raw_album,
            release_date=release_date,
            release_date_precision=precision,
            is_released=is_released(raw_album["name"], release_date),
            cover_thumbnail_url=raw_album["cover_art_thumbnail_url"],
            genius_url=raw_album["url"],
        )
        # The artists of an album that is only a stub come from the list too; a full album has its own.
        if album.import_state is ImportState.STUB:
            for position, artist in enumerate(raw_album["primary_artists"], start=1):
                stub = await get_or_create_artist_stub(session, artist)
                await add_if_missing(
                    session,
                    AlbumArtist,
                    {"album_id": album.id, "artist_id": stub.id},
                    position=position,
                )
        track = await find_placement(session, album.id, song.id)
        if track is None:
            track = AlbumTrack(album_id=album.id, song_id=song.id)
            session.add(track)
        is_primary = raw_album["id"] == primary_id
        if track.is_primary != is_primary:
            track.is_primary = is_primary
