from enum import StrEnum


class ImportState(StrEnum):
    STUB = "stub"
    FULL = "full"


class ArtistType(StrEnum):
    PERSON = "person"
    GROUP = "group"
    LABEL = "label"
    OTHER = "other"


class AlbumType(StrEnum):
    ALBUM = "album"
    EP = "ep"
    SINGLE = "single"
    COMPILATION = "compilation"
    LIVE = "live"
    MIXTAPE = "mixtape"
    SOUNDTRACK = "soundtrack"
    DJ_MIX = "dj_mix"  # an album of Genius that a real import met (1664955); a text column, so no migration
    OTHER = "other"


class DatePrecision(StrEnum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


class SongArtistRole(StrEnum):
    PRIMARY = "primary"
    FEATURED = "featured"


class SongRelationType(StrEnum):
    """One stored direction only; the inverse (sampled_in, remixed_by, ...) is derived."""

    SAMPLES = "samples"
    INTERPOLATES = "interpolates"
    COVER_OF = "cover_of"
    REMIX_OF = "remix_of"
    LIVE_VERSION_OF = "live_version_of"
    TRANSLATION_OF = "translation_of"


class AlbumRelationType(StrEnum):
    DELUXE_EDITION_OF = "deluxe_edition_of"
    ALTERNATE_VERSION_OF = "alternate_version_of"
    REISSUE_OF = "reissue_of"
    REMIX_VERSION_OF = "remix_version_of"


class NicknameKind(StrEnum):
    """`main`: the names of an artist that follow each other in time. `alter_ego`: a name tied to releases."""

    MAIN = "main"
    ALTER_EGO = "alter_ego"


class NicknameScope(StrEnum):
    """Where a name tied to a release is the name: `artist` in the lines of artists (the artists of an album or a song),
    `credit` in the credits (producers and the other roles), `any` in both. So one person can stand on a release under
    the main name as its artist and under an alter ego as its producer."""

    ARTIST = "artist"
    CREDIT = "credit"
    ANY = "any"


class UserRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class RevisionAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    IMPORT = "import"


class ImportKind(StrEnum):
    """What to import; each value is also the kind of work item the importer processes."""

    DISCOGRAPHY = "discography"  # an artist with every album, song and artist found on the way
    ARTIST = "artist"
    ALBUM = "album"
    SONG = "song"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
