# Music

Production web app that combines two things:
- **Streaming** (Spotify / Yandex Music style): playback, library, playlists, queue.
- **Encyclopedic catalog** (Genius / AlbumOfTheYear / RateYourMusic style): detailed artist/release/track pages, credits, genres, ratings, reviews, lyrics annotations.

Reply to the user in Russian. Code, UI, commit messages and docs are in English; comments and logs may be in Russian where the logic is hard (the user reads English at B1). Agreed domain and import decisions live in `docs/decisions/0002-domain-and-import-decisions.md`. Use Genius terms (`album`, not `release`).

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic v2, async everywhere |
| Frontend | TypeScript (strict), SvelteKit with Svelte 5 (runes only, no legacy `$:` / stores for new code) |
| Database | PostgreSQL only (no SQLite, not even for dev). SQLAlchemy 2.0 async + Alembic, see `docs/decisions/0001-orm.md` |
| Infra | Monorepo, Docker Engine in WSL2, Docker Compose for local dev services |
| Tooling | `uv` (Python), `pnpm` (JS), `ruff`, `pytest`, `svelte-check`, `vitest`, `playwright` |

Exact tool and library versions are not pinned here. Before adding or upgrading a dependency, check its current stable version and docs (web search / official docs). Do not rely on memory.

## Product decisions (from the user)

- Phase 1 is the **catalog** only. Design with the later feature in mind: releases mapped to local folders of mp3 files, playable from the site. Model a media source per release/track (path, format, duration, hash) so a folder scanner can be added as a plain importer.
- Data comes first from the open Genius API (`genius.com/api`), later some fields via the official user API. Imports must be idempotent: keep the raw response (JSONB, table `genius_response`) next to normalized data, store `genius_id`. Lyrics are not available via the API and must not be scraped.
- Local-only project for now. Write for local convenience, but so that going to prod means replacing or removing things, not rewriting.
- Auth is primitive: login + password, no confirmation. Dev-only auto-login as `admin/admin`, controlled by one config flag and a single `current_user` dependency, so it can be removed without touching callers.
- **API-first**: the site is just one client; an Android app will come later. Follow `docs/decisions/0003-api-first-for-multiple-clients.md` for every endpoint (OpenAPI contract, no presentation logic on the server, cookie and Bearer auth, no server-only data paths in SvelteKit).
- Two site modes: viewer and **edit mode**. For now the admin sees a pencil on the artist, album and song pages and can change what exists there (creating and deleting entities is not built). Later this becomes an `editor` role. Enforce permissions on the backend (`require_editor` dependency); the frontend only reflects a `canEdit` flag (`GET /me`).
- Edits are a **layer over the Genius data** (ADR 0006): sidecar `*_edit` tables with `overridden` (the fields set by hand) and per-list edit tables, read through views (`models/views.py`), so the import never touches an edit and a re-import does not bring back what was removed. Every change is one transaction and one `revision` (`editing.py`). A new editable field means: a column in the `*_edit` table, the view, the `*Patch` schema, the draft on the frontend and a test.
- Artist names follow the date (ADR 0006): main names in time, alter egos tied to releases, spellings; every query that shows an artist beside a date uses `artist_name(...)` (`api/names.py`; `scope=` says if the place is a line of artists or a credit, because an alter ego can be tied to a release for one of them).

## Layout (planned)

```
backend/       FastAPI app, uv project
groups/        groups of artists as files (`<genius id>.json`), outside the database: see ADR 0004
frontend-next/ the site: SvelteKit app on shadcn-svelte, pnpm project (`make dev` runs it on :8081)
frontend/      the first version of the site (Svelte UX), kept for comparison on :8080 until it is deleted; do not change it
docs/        architecture notes, decisions/ (ADRs)
compose.yaml local dev services
```

The domain model is approved (`docs/domain-model.md`) and implemented in `backend/src/music_backend/models/` with the initial Alembic migration (one migration while there is no data worth keeping: a schema change is made there and the database is rebuilt with `make reset`). The import (`backend/src/music_backend/imports/`: one handler per entity, a flat task queue, one transaction per entity; see `docs/decisions/0004-import-ui-and-jobs.md`) and its API are implemented, with the group files and the walk over groups and members. The names, the edit layer and the membership with periods (ADR 0006) are implemented: `models/edits.py`, `models/views.py`, `editing.py`, `api/*_edit.py`, `api/nicknames.py`, `api/members.py`. Auth and the other catalog endpoints (creating and deleting entities, lists of the library) are **not designed yet**: discuss with the user before building them. The one exception is a **test** home page of artists (`api/artists.py`, `src/routes/+page.svelte`, `src/lib/features/home/`), kept isolated because it may be dropped. The artist page (`api/artist_page.py`, `src/routes/artists/[id]`, `src/lib/features/artist/`) and the album page (`api/album_page.py`, `src/routes/albums/[id]`, `src/lib/features/album/`) were designed with the user; the album page follows the look of the discography block of the artist page. The song page (`api/song_page.py`, `src/routes/songs/[id]`, `src/lib/features/song/`) was chosen from two prototypes: it is laid out like the album page, with the card of the lyrics (the title and the artists are its top) beside the cover. Lyrics are not in any API and are never scraped: they are text files put by hand in `lyrics/<genius id>.txt` (`lyrics/demo.txt` stands in for songs without a file; the folder is not in git), read by `lyrics.py`.

## Code principles (user's explicit preferences)

1. Use the newest stable idioms of the language and frameworks: modern Python typing (`X | None`, `type` aliases, PEP 695 generics), `match`, `dataclass(slots=True)`, Svelte 5 runes, SvelteKit remote functions only if stable.
2. Code must be readable, fast and clean. Split into modules where it helps readability. **Do not over-split**: no one-function files, no abstraction layers without a second use case.
3. **Trust the data, write the minimum of checks.** Genius is trusted: read its fields directly (`raw["name_components"]["base_name"]`), no `.get(...)`, `or default`, `isinstance` or "just in case" fallbacks. No CHECK constraints, no range or format validation, no business-rule indexes in the database. Add a check only after a test or a real run shows a problem, and say what showed it. What stays: keys (PK, FK, NOT NULL), uniqueness the code looks things up by (`genius_id`, dictionary names, file path, one active import per target), type declarations, auth, and behaviour the user sees (404, 409).
4. Prefer current community-endorsed tools over legacy ones. Avoid deprecated APIs.
5. Comments explain *why*, never *what*. Match surrounding code style.

## Commands

Single source of truth for run/test/lint commands.

Backend (`cd backend`, uv project, `src/music_backend`, tests in `tests/`):
- `uv sync` install, `uv add <pkg>` / `uv add --dev <pkg>` add dependency
- `uv run ruff format .` / `uv run ruff check --fix .`
- `uv run mypy` (strict), `uv run pytest` (async mode auto, coverage on; needs `docker compose up -d db`, tests build their own `music_test` database through the real migrations)
- `uv run fastapi dev` (API on :8000, entrypoint set in pyproject), health: `/api/v1/health`
- `make dev` (repo root): the whole project in one terminal (database, migrations, API on :8000, the new site `frontend-next/` on :8081); `make backend` / `make frontend` run one of them, `make frontend-old` runs the old site `frontend/` on :8080 for comparison
- `make reset` (repo root): deletes the compose database volume and rebuilds the tables from the migrations, a clean start for an import; stop the backend first
- `uv run alembic revision --autogenerate -m "..."`, `uv run alembic upgrade head`, `uv run alembic check`
- Column order is fixed by `sort_order` bands in `models/base.py` (see `docs/domain-model.md`); no JSON columns for modeled data (exceptions are listed there)
- Enum columns: use `enum_column()` (text, no CHECK, room for new values; adding a value needs no migration)
- SQL shared by the API modules (what a role is, the album card, ordering, counting) lives in `api/queries.py`; a change of the schema is a new Alembic migration that keeps the data (`docs/decisions/0005-refactoring-decisions.md`)

Frontend (`cd frontend-next`, SvelteKit 3 + Svelte 5 + TS + shadcn-svelte, pnpm; details and the way the look was matched in `docs/handoff.md` section 5):
- `pnpm install`, `pnpm dev` (site on :8081, `/api` proxied to the backend on :8000), `pnpm build` (`adapter-static`, fallback `index.html`)
- `pnpm gen:api` regenerates `src/lib/api/schema.d.ts` from the backend OpenAPI schema (never write API types by hand)
- `pnpm check` (svelte-check), `pnpm lint` (prettier + eslint), `pnpm format`, `pnpm exec vitest run` (unit tests of the helpers and the drafts), `pnpm test:e2e` (Playwright with the API answered by the test; needs Chromium and uses the server on :8081 if it runs)
- UI: shadcn-svelte parts (Bits UI) in `src/lib/components/ui/`, kept as generated (add one with `pnpm exec shadcn-svelte add <part> -y`, then `pnpm format`; remove a part that nothing uses); our shared blocks in `src/lib/components/`, feature components in `src/lib/features/<feature>/` (`home`, `import`, `artist`, `album`, `song`, `edit`), pure helpers with their tests in `src/lib/utils/`. Tokens and the 16px root with the old rem scale are in `src/app.css`: text levels `foreground` / `body` / `muted-foreground` / `subtle`, colour only for meaning. Imports use `#lib/...` (`package.json` `imports`; TypeScript modules with `.js`, Svelte files with `.svelte`). Svelte 5 runes only. The edit mode is a draft class per page (`*-draft.svelte.ts`) that builds its patch with `PatchBuilder` (`features/edit/patch.ts`); the fields of the edit mode are the shared parts in `features/edit/`. Animations are allowed. Sizes must not depend on content or state; the size of an element is read with `watchWidth` / `watchHeight` (`utils/watch-size.ts`), not `bind:clientWidth`. A detail page loads its entity in `+page.ts` through `loaded()`; a paged list uses `PagedList`; links to other sites go through `components/ext-link.svelte`.

Old frontend (`cd frontend`, Svelte UX, kept for comparison; do not change it):
- `pnpm install`, `pnpm dev` (site on :8080, `/api` proxied to the backend on :8000), `pnpm build` (`adapter-static`, fallback `index.html`)
- `pnpm gen:api` regenerates `src/lib/api/schema.d.ts` from the backend OpenAPI schema (run it after changing the API; never write API types by hand)
- UI: Svelte UX (`svelte-ux@next` 2.x, Tailwind 4 through `@tailwindcss/vite`) in one dark, nearly monochrome theme (`[data-theme='music']` in `src/app.css`, registered through `settings()` in the root layout because Svelte UX owns `<html data-theme>`); colour only for meaning (success, warning, danger). Svelte UX components are written in the old Svelte syntax inside: bind props and pass children, but do not use `on:` events or `slot=` from our runes code. Animations and transitions are allowed (the user dropped the earlier "no animations" rule). What already moves: the height of an album card eases when the view switches between Grid and Rows, so the categories below move smoothly; the text of `ui/ClampList.svelte` opens and closes smoothly; the covers behind the main one slide out and back smoothly on the album page; every link goes white smoothly on hover (`a:hover` in `app.css`, outside of any layer); the gear in the corner of the tracklist turns half a circle on hover; the cover viewer fades in and out (the page darkens behind it); the description moves down smoothly when the tiles of the descriptors open; the bars on the picture of the clip that is playing dance (`.equalizer-bar` in `app.css`); the picture of a clip darkens smoothly under the pointer, the clip in the big player fades out to black and in again when another one is pressed (no growing from the middle), and the button of the clip that is playing pauses and resumes the big player and follows its state; the credits and the description of an album open and close smoothly (`ui/Collapse.svelte`); the clips of the album and the blocks around them glide to their places when one of them is started (`lib/glide.ts`; there is one player, made when a clip is pressed). Sizes must not depend on content or state: one place for a geometry that two states share (for example `CARD` and `perRow` in `src/lib/artists.ts` serve both the strip and the opened grid of an album category). A detail page loads its entity in `+page.ts` through `loaded()` (`src/lib/load.ts`): the site is client-only (`ssr = false`), a 404 or a stopped backend becomes `+error.svelte`. A list read from a paged endpoint uses `PagedList` (`src/lib/paged.svelte.ts`); links to other sites go through `ui/ExtLink.svelte`; the size of an element is read with the `ui/watchSize.ts` actions (`watchWidth`, `watchHeight`), not `bind:clientWidth` (it logs a ResizeObserver error). Own small components in `src/lib/ui/`, feature components in `src/lib/<feature>/` (for example `src/lib/import/`); imports from `src/lib` use `#lib/...` (TypeScript modules with a `.js` extension, Svelte files with `.svelte`)
- `pnpm check` (svelte-check), `pnpm lint` (prettier + eslint), `pnpm format`
- `pnpm test:unit` (vitest; component tests run in a Playwright browser, run `pnpm exec playwright install chromium` once), `pnpm test:e2e`

Infra: `docker compose up -d db` (PostgreSQL).

## Working rules

- **At the start of a session read `docs/handoff.md`** (state of the work, lessons, next steps). It is temporary: shrink or delete it when its open items are closed.
- Ask before architectural decisions, new infrastructure, or new top-level dependencies.
- Never read or print `.env*` files or secrets. Use `.env.example` for documented variables.
- Do not commit unless asked.
- Scoped rules live in `.claude/rules/` (backend, frontend) and load automatically for matching paths.
