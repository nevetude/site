# ADR 0006: Names over time, edits over Genius, membership with time

Status: accepted (decisions of the user, 2026-10-23). It is the design of what `docs/domain-model.md` called "editing and
deleting are not modelled yet".

## What the user wanted
1. An artist has **main names** that follow each other in time (Snoop Doggy Dogg, Snoop Dogg, Snoop Lion, Snoop Dogg
   again) and **alter egos** that belong to some releases. Every name has **spellings** (Bladee, BLADEE, bladee).
2. Everywhere a date stands beside an artist's name (an album, a song, a clip, a credit), the name is the one the artist
   had on that date, also on somebody else's release.
3. A **pencil** on the page of an artist, an album and a song opens an edit mode on the page itself.
4. What was changed by hand must **survive a new import**, and what Genius says must stay untouched.
5. A group has a composition with the **time of each member**, and the groups live in files, not in the database.

## Names (`models/edits.py`, `api/names.py`, `api/nicknames.py`)
- `nickname(artist_id, kind main|alter_ego, name)`, `nickname_spelling`, `nickname_period` (a main name is in force from
  the release `start_album_id` / `start_song_id` on, the first period has no start; a name that came back has two
  periods), `nickname_use` (a name on a release: an alter ego is the name there, in the places its `scope` says; for a main
  name only `spelling_id` counts, the spelling that release writes). `scope` is `artist` (the lines of artists of the
  album or the song), `credit` (the credits: producers and the other roles) or `any` (both, the default). So one release
  can show the main name as its artist and an alter ego as its producer (2026-10-31).
- `artist_name(artist, on=, album_id=, song_id=)` is one SQL expression that stands where `Artist.base_name` stood in
  every query of the API (the place says if it is a line of artists or a credit with `scope=`): 1. an alter ego tied to the
  album or the song whose scope fits the place; 2. else the main name whose period started last
  not after the date (a period with no start is in force from the beginning; with no date the latest period); 3. the
  spelling chosen for the release; 4. else the name Genius gave. The dates are the effective ones, so a period follows
  the date of the release it starts with.
- Which date: an album's artists and credits, the album's date; a track, the date of the song, else of the album; a song
  page, the date of the song; a clip, the date of its song; the artist's own page, the lists of artists and the members
  of a group, the latest name (no date). An alter ego tied to an album is the name on all of its songs.
- The aliases of Genius (`artist_alias`) stay as they are: the editor shows them "not sorted" and turns one into a name.
- `PUT /artists/{id}/nicknames` replaces all the names of the artist (the editor holds the list and saves it once);
  `GET /artists/{id}/releases?q=` finds the albums and songs of the artist for the pickers; `GET /artists/search?q=`
  finds an artist of the library by any name or spelling.

## Edits over Genius: a layer, read through views (`models/views.py`, the migration)
- The import writes only the tables of `catalog.py`. A field set by hand goes to `album_edit`, `artist_edit` or
  `song_edit`: typed nullable columns and `overridden text[]`, the names of the fields that were set (a NULL value is a
  value: a date taken away). Resetting a field to Genius is taking its name out of the list.
- The lists have a row of edits per row of Genius: `artist_member_edit`, `album_track_edit`, `song_artist_edit`,
  `song_credit_edit`, `album_credit_edit`, `song_tag_edit` (`removed`, and for some the order of the user and, for members,
  the time). What is taken out is hidden, never deleted, so the import cannot bring it back. What is added is a normal
  row of the table of Genius (nothing of Genius is overwritten by it).
- **Reads go through views** (`album_view`, `artist_view`, `song_view`, `artist_member_view`, `album_track_view`,
  `song_artist_view`, `song_credit_view`, `album_credit_view`, `song_tag_view`) mapped by classes of `ViewBase` (not on
  `Base.metadata`: Alembic must not make tables of them). The classes share the columns of the tables by mixins
  (`ArtistColumns`, ...); `tests/test_views.py` checks that every column of a table is in its view.
- Postgres cannot know the primary key of a view: a query that groups by `id` and selects other columns groups by all
  the columns (`group_by(*ArtistView.__table__.c)`).
- Why a layer and not "the import skips what was edited" (the user's choice): Genius's data stays complete, a field goes
  back to it with no new import, and an import has no rule to know about edits.

## Group membership with time (`ArtistMemberEdit`, `api/members.py`, `groups.py`, `imports/group_file.py`)
- Each end of the time is a release (the date follows it) or a date (a year is enough: `2012`, `2012-05`, `2012-05-03`);
  no start is unknown, no end is "now", and `has_left` with no end is "left, nobody knows when".
- `PUT /artists/{id}/members` makes the group what the list says: the order, the time, and who is in it.
- The file `groups/<genius id>.json` keeps the list and the time of each member (`start`, `end`, `has_left` as years),
  and `discographies`. Importing a group applies the file to the database when the job ends (`apply_group`), and editing
  the members on the page writes the file back, so a clean database gets the group again.

## The edit mode (API and site)
- `GET /me` says whether to show the pencil; every write needs `require_editor` anyway.
- Fields: `PATCH /albums|artists|songs/{id}` (only what is in the body; `reset: [...]` puts fields back to Genius; the
  cover is four fields). Lists: `PUT /albums/{id}/tracks`, `/albums|songs/{id}/credits`, `/songs/{id}/artists`,
  `/songs/{id}/tags`. Dictionaries: `GET/POST /genres`, `GET /tags`, `GET /credit-roles` (roles and tags are made by the call
  that uses them; a genre by `POST /genres`). `GET /songs/search?q=` finds a song for a tracklist.
- Every change is one transaction with one `Revision` (`{what: [before, after]}`, the author).
- A description written by hand has no Genius `dom`: the page shows the text with its paragraphs.
- On the site (`frontend-next`) the pencil (`features/edit/edit-bar.svelte`) makes a draft of the page (`AlbumDraft`,
  `ArtistDraft`, `SongDraft`: the fields and lists, and what to send), the components of the page show fields in place of
  values while a draft is there, Save sends what differs from the page and reads it again. A field that was edited has a
  button that puts it back to Genius when saved.

## Not done, on purpose
- The main artists of an album, the relations between albums or songs, the gallery and the other fields that have no
  data are not edited. Deleting a whole entity is not there.
- An alter ego that Genius has as a separate artist is imported as one; merging it into the main artist is a later task.
- Only the main name is shown in lists and the headers: the places that show a spelling choice are the ones with a
  release (see the rules above).
