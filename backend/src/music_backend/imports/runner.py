import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import select

from music_backend.enums import ImportKind, ImportState
from music_backend.imports.album import handle_album
from music_backend.imports.artist import handle_artist, handle_discography
from music_backend.imports.client import RateLimitedError
from music_backend.imports.common import Follow, Task
from music_backend.imports.song import handle_song
from music_backend.models import (
    Album,
    AlbumArtist,
    AlbumCredit,
    AlbumRelationship,
    AlbumTrack,
    Artist,
    Song,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from music_backend.imports.common import Context, Handler


log = logging.getLogger(__name__)

# Entities handled at the same time. A request waits ~0.8 s for its answer, so this many keep the
# client's request interval (`genius_min_interval_s`) full; more would only queue behind it.
WORKERS = 4

HANDLERS: dict[ImportKind, Handler] = {
    ImportKind.DISCOGRAPHY: handle_discography,
    ImportKind.ARTIST: handle_artist,
    ImportKind.ALBUM: handle_album,
    ImportKind.SONG: handle_song,
}
# The entity a task is "about": the name in the progress, `result_id` of a job, the page of a request.
ENTITY_MODEL: dict[ImportKind, type[Artist] | type[Album] | type[Song]] = {
    ImportKind.DISCOGRAPHY: Artist,
    ImportKind.ARTIST: Artist,
    ImportKind.ALBUM: Album,
    ImportKind.SONG: Song,
}


@dataclass(slots=True)
class Count:
    kind: ImportKind
    done: int = 0
    total: int = 0


class NodeState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class Node:
    """An artist of the walk over groups and members, for the tracker of the nesting. `parent` is the artist that found
    it first (none: the artist of the job, or one found in an album or a song, then `via` says which). `also_in` are
    the artists that found it again afterwards: a person in two groups, or a loop back to where the walk came from."""

    genius_id: int
    name: str | None
    parent: int | None
    via: ImportKind | None
    state: NodeState = NodeState.QUEUED
    also_in: list[int] = field(default_factory=list)


@dataclass(slots=True)
class Progress:
    """What a client sees while a job runs. Only two levels are counted, because only those totals
    are known in advance and never grow:

    - `units`: the things the first task found (a discography: the artist and every album);
    - `items`: what the current unit found when it was read (an album: its songs, artists, ...).

    Everything deeper (the artists of a song, ...) is imported as part of its item and only shows as
    `active`.
    """

    root: Task | None = None
    units: list[Count] = field(default_factory=list)
    unit: Task | None = None
    items: list[Count] = field(default_factory=list)
    active: Task | None = None
    # Every artist the job has met, in the order it met them (a dict keeps it): the nesting of the walk.
    tree: dict[int, Node] = field(default_factory=dict)

    @property
    def done(self) -> int:
        return sum(c.done for c in self.units)

    @property
    def total(self) -> int | None:
        return sum(c.total for c in self.units) if self.units else None


type OnProgress = Callable[[Progress], Awaitable[None]]


def _counts(tasks: list[Task], done: int = 0) -> list[Count]:
    counts: dict[ImportKind, Count] = {}
    for task in tasks:
        counts.setdefault(task.kind, Count(task.kind)).total += 1
    if done and tasks:
        counts[tasks[0].kind].done = done
    return list(counts.values())


def _grow(counts: list[Count], kind: ImportKind) -> None:
    """One more unit of this kind, put on the job while it runs."""
    found = next((c for c in counts if c.kind is kind), None)
    if found is None:
        counts.append(found := Count(kind))
    found.total += 1


def _bump(counts: list[Count], kind: ImportKind) -> None:
    next(c for c in counts if c.kind is kind).done += 1


async def _name_of(sessionmaker: async_sessionmaker[AsyncSession], task: Task) -> str | None:
    model = ENTITY_MODEL[task.kind]
    async with sessionmaker() as session:
        name: str | None = await session.scalar(
            select(model.name).where(model.genius_id == task.genius_id)
        )
    return name


async def _stored_children(session: AsyncSession, task: Task) -> list[Task] | None:
    """What an entity that was already read in full leaves to do, so that it is not asked of Genius again; None for one that
    must be read (it is not in full, or it is a list of albums, which can have new ones).

    A song or an artist in full has nothing left. An album in full gives its songs and artists from the database: the
    ones that are still stubs (an import that was cut short) are read now, the others pass by in the same way."""
    if task.kind not in (ImportKind.ARTIST, ImportKind.ALBUM, ImportKind.SONG):
        return None
    model = ENTITY_MODEL[task.kind]
    row: Artist | Album | Song | None = await session.scalar(
        select(model).where(model.genius_id == task.genius_id)
    )
    if row is None or row.import_state is not ImportState.FULL:
        return None
    if task.kind is not ImportKind.ALBUM:
        return []
    songs = await session.execute(
        select(Song.genius_id, Song.name)
        .join(AlbumTrack, AlbumTrack.song_id == Song.id)
        .where(AlbumTrack.album_id == row.id)
        .order_by(AlbumTrack.sort_order)
    )
    artists = await session.execute(
        select(Artist.genius_id, Artist.name)
        .where(
            Artist.id.in_(select(AlbumArtist.artist_id).where(AlbumArtist.album_id == row.id))
            | Artist.id.in_(select(AlbumCredit.artist_id).where(AlbumCredit.album_id == row.id))
        )
        .order_by(Artist.id)
    )
    found = [Task(ImportKind.SONG, gid, task.follow, name=name) for gid, name in songs if gid]
    found += [Task(ImportKind.ARTIST, gid, Follow.ALL, name=name) for gid, name in artists if gid]
    if Follow.RELATED in task.follow:
        others = await session.execute(
            select(Album.genius_id, Album.name).where(
                Album.id.in_(
                    select(AlbumRelationship.related_album_id).where(
                        AlbumRelationship.album_id == row.id
                    )
                )
                | Album.id.in_(
                    select(AlbumRelationship.album_id).where(
                        AlbumRelationship.related_album_id == row.id
                    )
                )
            )
        )
        found += [
            Task(ImportKind.ALBUM, gid, Follow.NONE, name=name) for gid, name in others if gid
        ]
    return found


async def run_tasks(
    sessionmaker: async_sessionmaker[AsyncSession],
    ctx: Context,
    root: Task,
    on_progress: OnProgress,
    workers: int = WORKERS,
    extra: Sequence[Task] = (),
) -> list[str]:
    """Process `root` and everything the handlers queue, each entity once.

    One entity is one transaction: stopping (cancel, crash, restart) keeps everything already
    finished and loses only the entity being written. A failure of the root task raises; a failure
    of any other task is logged and returned, and the run goes on.

    The root's children are the job's units and are done one after another, each with its whole
    surroundings, so a stop leaves complete albums and not half of every album. The items of one unit
    (the songs of an album, ...) run in parallel, `workers` entities at a time, each item with its own
    surroundings depth first. `extra` are more units of the root, put there by hand (the members of a saved group).
    """
    state = Progress(root=root)
    seen = {root.key}
    if root.kind is ImportKind.DISCOGRAPHY:
        seen.add((ImportKind.ARTIST, root.genius_id))  # imported by the root itself
    tree = state.tree
    if root.kind in (ImportKind.DISCOGRAPHY, ImportKind.ARTIST):
        tree[root.genius_id] = Node(root.genius_id, root.name, None, None, NodeState.RUNNING)

    def met(parent: Task, found: list[Task]) -> None:
        """Writes the artists among `found` into the tree; one that is already there was found again."""
        for child in found:
            if child.kind not in (ImportKind.ARTIST, ImportKind.DISCOGRAPHY):
                continue
            at_parent = (
                parent.genius_id
                if parent.kind in (ImportKind.ARTIST, ImportKind.DISCOGRAPHY)
                else None
            )
            if child.genius_id not in tree:
                via = None if at_parent else parent.kind
                tree[child.genius_id] = Node(child.genius_id, child.name, at_parent, via)
            elif at_parent and at_parent != tree[child.genius_id].parent:
                if at_parent not in tree[child.genius_id].also_in:
                    tree[child.genius_id].also_in.append(at_parent)

    failures: list[str] = []
    later: list[
        Task
    ] = []  # the other albums of the songs, imported as units after the units of the job
    slots = asyncio.Semaphore(workers)

    async def handle(task: Task) -> list[Task]:
        """Save one entity; the tasks it found, minus the ones already known."""
        state.active = task
        node = (
            tree.get(task.genius_id)
            if task.kind in (ImportKind.ARTIST, ImportKind.DISCOGRAPHY)
            else None
        )
        if node:
            node.state = NodeState.RUNNING
        await on_progress(state)
        try:
            async with slots, sessionmaker() as session, session.begin():
                # The root is always read (it is what the user asked to refresh); what it found is not read again when
                # it is in full already.
                children = None if task is root else await _stored_children(session, task)
                if children is None:
                    children = await HANDLERS[task.kind](ctx.for_task(task), session, task)
        except RateLimitedError:
            raise  # not a failure of this entity: the whole import stops here
        except Exception as error:
            if node:
                node.state = NodeState.FAILED
            if task is root:
                raise
            log.warning("import of %s %s failed: %r", task.kind.value, task.genius_id, error)
            failures.append(f"{task.kind.value} {task.genius_id}: {error}")
            return []
        if node:
            node.state = NodeState.DONE
        children = list(dict.fromkeys(children))
        met(task, children)
        new = [child for child in children if child.key not in seen]
        seen.update(child.key for child in new)
        if task.kind is ImportKind.SONG:
            # The other albums of a song wait for the end of the job: the album being imported is finished first.
            later.extend(child for child in new if child.kind is ImportKind.ALBUM)
            new = [child for child in new if child.kind is not ImportKind.ALBUM]
        return new

    async def walk(start: Task) -> None:
        queue = deque([start])
        while queue:
            queue.extendleft(reversed(await handle(queue.popleft())))  # depth first

    async def finish(item: Task) -> None:
        await walk(item)
        _bump(state.items, item.kind)
        await on_progress(state)

    units = await handle(root)
    fresh = [task for task in extra if task.key not in seen]
    seen.update(task.key for task in fresh)
    # A discography reads its artist itself: the same artist is not also a unit of its own, nor read again later.
    whole = {task.genius_id for task in fresh if task.kind is ImportKind.DISCOGRAPHY}
    seen.update((ImportKind.ARTIST, genius_id) for genius_id in whole)
    units = [u for u in units if not (u.kind is ImportKind.ARTIST and u.genius_id in whole)]
    met(root, fresh)
    units += fresh
    state.root = replace(root, name=await _name_of(sessionmaker, root))
    if root.genius_id in tree:
        tree[root.genius_id].name = state.root.name
    # A discography is the artist plus a list: its units are what they found. Any other root is itself the first unit.
    counted = units if root.kind is ImportKind.DISCOGRAPHY else [root, *units]
    state.units = _counts(counted, done=0 if root.kind is ImportKind.DISCOGRAPHY else 1)

    position = 0
    while position < len(units) or later:
        if position == len(units):
            units.append(later.pop(0))
            _grow(state.units, units[-1].kind)
        unit = units[position]
        position += 1
        state.unit = unit
        state.items = []
        items = await handle(unit)
        state.unit = replace(unit, name=unit.name or await _name_of(sessionmaker, unit))
        state.items = _counts(items)
        running = [asyncio.create_task(finish(item)) for item in items]
        try:
            await asyncio.gather(*running)
        except BaseException:
            # A 429, a crash or a cancel: stop the siblings too, and raise the first error as it is
            # (a TaskGroup would wrap it in an ExceptionGroup).
            for task in running:
                task.cancel()
            await asyncio.gather(*running, return_exceptions=True)
            raise
        _bump(state.units, unit.kind)
        await on_progress(state)

    state.unit = state.active = None
    state.items = []
    await on_progress(state)
    return failures
