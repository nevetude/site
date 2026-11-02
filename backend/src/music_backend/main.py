from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from music_backend.api import (
    album_edit,
    album_page,
    artist_edit,
    artist_page,
    artists,
    credits_edit,
    dictionaries,
    genius,
    groups,
    imports,
    me,
    members,
    nicknames,
    series,
    song_edit,
    song_page,
)
from music_backend.api.deps import SessionDep
from music_backend.config import Settings, get_settings
from music_backend.imports.client import GeniusClient
from music_backend.imports.manager import ImportManager


def create_app(
    settings: Settings | None = None, genius_client: GeniusClient | None = None
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        client = genius_client or GeniusClient(
            settings.genius_base_url,
            settings.genius_min_interval_s,
            settings.genius_retry_backoff_s,
            official_url=settings.genius_official_url,
            user_token=settings.genius_user_token,
        )
        manager = ImportManager(sessionmaker, client, settings.groups_dir)
        await manager.recover()
        app.state.settings = settings
        app.state.sessionmaker = sessionmaker
        app.state.genius = client
        app.state.imports = manager
        yield
        await manager.shutdown()
        await client.aclose()
        await engine.dispose()

    app = FastAPI(
        title="Music",
        lifespan=lifespan,
        # operationId = function name, so generated clients (TypeScript, Kotlin) get stable method names.
        generate_unique_id_function=lambda route: route.name,
    )

    app.include_router(album_page.router)
    app.include_router(album_edit.router)
    app.include_router(artists.router)
    app.include_router(artist_page.router)  # after the list: `/roles` must not be read as an id
    app.include_router(artist_edit.router)
    app.include_router(nicknames.router)
    app.include_router(members.router)
    app.include_router(series.router)
    app.include_router(genius.router)
    app.include_router(groups.router)
    app.include_router(imports.router)
    app.include_router(song_page.router)
    app.include_router(song_edit.router)
    app.include_router(credits_edit.songs)
    app.include_router(credits_edit.albums)
    app.include_router(dictionaries.router)
    app.include_router(me.router)

    @app.get("/api/v1/health")
    async def health(session: SessionDep) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
