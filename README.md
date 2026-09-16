# Book-it

[![CI](https://github.com/abdourekik/book-it/actions/workflows/ci.yml/badge.svg)](https://github.com/abdourekik/book-it/actions/workflows/ci.yml)

Appointment booking for small businesses. Barbers, clinics, and tutors publish their
availability; customers pick a slot and book it in a few taps.

> **Status: in development.** The backend API is complete — authentication, availability,
> and booking with database-enforced protection against double-booking. The frontend and
> deployment are not built yet. See [Roadmap](#roadmap).

<!-- TODO once deployed: live link, demo GIF, coverage badge -->

**Live demo:** not deployed yet
**Demo video:** not recorded yet

---

## Features

Planned for v1. Ticked items are built and tested.

- [x] Business owners publish services with duration and price
- [x] Owners set weekly availability and block out time off
- [x] Customers see real available slots for a chosen service and date
- [x] Customers book, cancel, and reschedule appointments
- [x] Double-booking is impossible, even under simultaneous requests
- [ ] Email confirmations, cancellations, and 24-hour reminders
- [ ] Owner dashboard with upcoming bookings and simple stats
- [x] Correct across time zones — everything stored in UTC

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12, FastAPI | Type hints drive validation and free API docs |
| ORM | SQLAlchemy 2.0 + Alembic | Versioned schema changes, not hand-run SQL |
| Validation | Pydantic v2 | One definition validates requests and settings |
| Database | PostgreSQL 16 | Real constraints; the last line of defense against double-booking |
| Frontend | Next.js (App Router), TypeScript, Tailwind | <!-- TODO: not built yet --> |
| Email | Resend | Simple transactional email API |
| Tests | pytest + ruff | Fast feedback locally and in CI |
| CI | GitHub Actions | Lint and tests on every push |
| Hosting | Render (API), Vercel (web), Supabase/Neon (database) | <!-- TODO: not deployed yet --> |

## Architecture

Three separate pieces: a Next.js frontend that draws the screens, a FastAPI backend that
decides what is allowed, and PostgreSQL that remembers it. The browser never talks to the
database directly — only the backend does, which is what makes the rules enforceable.

Full write-up with diagrams: **[docs/architecture.md](docs/architecture.md)**

## Local setup

**Requirements:** Python 3.12, Docker Desktop, Git. (Node.js 20+ once the frontend exists.)

```bash
git clone https://github.com/abdourekik/book-it.git
cd book-it
```

**1. Start PostgreSQL**

```bash
docker compose up -d
docker compose ps        # wait for "Up (healthy)"
```

The container publishes port **15432** on the host, not the usual 5432, to avoid clashing
with any PostgreSQL already installed on your machine.

**2. Set up the backend**

```bash
cd backend
py -3.12 -m venv .venv          # Windows
.venv\Scripts\activate
# macOS/Linux: python3.12 -m venv .venv && source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env          # Windows;  cp .env.example .env  elsewhere
```

**3. Create the database tables**

```bash
alembic upgrade head
```

This applies every migration in `backend/alembic/versions/` in order. Run it again after
any `git pull` that brings new migrations.

**4. Load sample data (optional but recommended)**

```bash
python -m scripts.seed
```

Creates two businesses in two different timezones, six services, weekly opening hours,
and a handful of bookings. Re-run with `--reset` to wipe and start over. The script
refuses to run unless `ENVIRONMENT` is a development value, and seeded accounts cannot
log in.

**5. Run the API**

```bash
python -m uvicorn app.main:app --reload
```

| URL | What it is |
|---|---|
| http://localhost:8000/health | Liveness check |
| http://localhost:8000/docs | Interactive API documentation |

### Configuration

All settings come from environment variables, loaded from `backend/.env` in development.
Start from `backend/.env.example`. **`.env` is gitignored and must never be committed.**

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string; the app refuses to start without it |
| `ENVIRONMENT` | no | `development` or `production` (default: `development`) |
| `DEBUG` | no | Extra logging (default: `false`) |
| `APP_NAME` | no | Title shown in the API docs |

## API

| Method | Path | Who |
|---|---|---|
| `POST` | `/auth/signup` · `/auth/login` | anyone |
| `GET` | `/auth/me` | any signed-in user |
| `GET` | `/businesses/{slug}/slots` | anyone — no login needed to see availability |
| `POST` | `/bookings` | anyone (guest or signed in) |
| `GET` `POST` | `/bookings/{token}` · `/cancel` · `/reschedule` | whoever holds the token |
| `GET` `POST` `PATCH` | `/me/business` | owners |
| `GET` `POST` `PATCH` `DELETE` | `/me/services` | owners |
| `GET` `PUT` | `/me/availability` | owners |
| `GET` `POST` `DELETE` | `/me/time-off` | owners |

Full interactive docs at `/docs` when the server is running.

## Tests

```bash
cd backend
pytest                  # run the test suite
pytest --cov=app        # with a coverage report
ruff check .            # lint
ruff format .           # auto-format
```

## Database migrations

The schema is versioned with Alembic. Tables are never created by hand, and never with
`create_all()` — every change is a reviewable, numbered script that runs the same way on
a laptop and in production.

```bash
cd backend
alembic upgrade head                              # apply all pending migrations
alembic revision --autogenerate -m "add x to y"   # draft a migration from model changes
alembic downgrade -1                              # undo the most recent migration
alembic current                                   # which revision is this database on?
alembic history                                   # list all migrations
```

**Always read an autogenerated migration before running it.** Autogenerate compares the
models against the live database and guesses; it cannot see things it was never told
about. The first migration needed `CREATE EXTENSION btree_gist` added by hand, and enum
types dropped by hand in `downgrade()`.

CI runs all three on every push and pull request — see
[.github/workflows/ci.yml](.github/workflows/ci.yml).

<!-- TODO: add coverage reporting once booking logic exists (target: >80% on booking) -->

## Deployment

<!-- TODO: fill in during Phase 8 -->
Not deployed yet. Planned: database on Supabase or Neon, backend on Render, frontend on
Vercel, with migrations run as a release step.

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Project setup, CI, local database | done |
| 2 | Data model and migrations | done |
| 3 | Authentication and roles | done |
| 4 | Availability and booking logic | done |
| 5 | Frontend | next |
| 6 | Email notifications | planned |
| 7 | Owner dashboard | planned |
| 8 | Deployment and polish | planned |

Detailed checklist and session-by-session log: **[PROGRESS.md](PROGRESS.md)**

## Notes

This is the first of five portfolio projects, built while learning software engineering.
Technical decisions and the reasoning behind them are recorded in
[PROGRESS.md](PROGRESS.md) under *Decisions*.

## License

<!-- TODO: add a LICENSE file (MIT is a reasonable default for a portfolio project) -->
