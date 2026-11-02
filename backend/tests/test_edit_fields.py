from music_backend.api.album_edit import AlbumPatch
from music_backend.api.artist_edit import ArtistPatch
from music_backend.api.song_edit import SongPatch
from music_backend.models import (
    ALBUM_FIELDS,
    ARTIST_FIELDS,
    SONG_FIELDS,
    AlbumEdit,
    ArtistEdit,
    SongEdit,
)


def test_a_patch_names_the_fields_that_can_be_overridden_and_no_other() -> None:
    """The fields exist in three places (the body of a patch, the edit table and the view): they must say the same."""
    for patch, edit, fields in (
        (AlbumPatch, AlbumEdit, ALBUM_FIELDS),
        (ArtistPatch, ArtistEdit, ARTIST_FIELDS),
        (SongPatch, SongEdit, SONG_FIELDS),
    ):
        assert set(patch.model_fields) - {"reset"} == set(fields), patch.__name__
        assert set(fields) <= set(edit.__table__.columns.keys()), edit.__name__
        # `reset` takes the same names
        reset = patch.model_fields["reset"].annotation
        assert set(reset.__args__[0].__value__.__args__) == set(fields), patch.__name__  # type: ignore[union-attr]
