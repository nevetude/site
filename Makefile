.PHONY: dev tmux stop backend frontend frontend-old reset

# The whole project in one terminal: the database, then the API (:8000) and the site (:8081, `frontend-next/`) side by side.
# Ctrl+C stops both. The migrations run first, so a fresh database is ready to use.
dev:
	docker compose up -d --wait db
	$(MAKE) --no-print-directory -j2 backend frontend

# The same in two panes of tmux, side by side, each one a terminal of its own (a pane that crashes stays open to show the
# error; the mouse picks a pane and scrolls). Ctrl+b d leaves it running, `make tmux` comes back, `make stop` ends it.
tmux:
	docker compose up -d --wait db
	tmux has-session -t music 2>/dev/null || { \
		tmux new-session -d -s music -c $(CURDIR)/backend 'uv run alembic upgrade head && uv run fastapi dev' && \
		tmux split-window -h -t music -c $(CURDIR)/frontend-next 'pnpm dev' && \
		tmux set-option -t music remain-on-exit on && tmux set-option -t music mouse on; }
	tmux attach -t music

stop:
	tmux kill-session -t music

backend:
	cd backend && uv run alembic upgrade head && uv run fastapi dev

frontend:
	cd frontend-next && pnpm dev

# The old site (Svelte UX, :8080), kept for comparison until it is deleted. It uses the same API.
frontend-old:
	cd frontend && pnpm dev

# A clean database: the volume of the compose database is deleted (nothing else can be touched, so no question and
# no check of the host), then the migrations build the tables again. Stop the backend first.
reset:
	docker compose down -v
	docker compose up -d --wait db
	cd backend && uv run alembic upgrade head
