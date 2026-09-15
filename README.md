# Book-it

Appointment booking for small businesses. Barbers, clinics, and tutors publish their
availability; customers pick a slot and book it in a few taps.

> **Status: in development.** Backend skeleton and local database are running.
> Booking logic, frontend, and deployment are not built yet. See [Roadmap](#roadmap).

<!-- TODO once deployed: live link, demo GIF, CI and coverage badges -->

**Live demo:** not deployed yet
**Demo video:** not recorded yet

---

## Features

Planned for v1. Ticked items are built and tested.

- [ ] Business owners publish services with duration and price
- [ ] Owners set weekly availability and block out time off
- [ ] Customers see real available slots for a chosen service and date
- [ ] Customers book, cancel, and reschedule appointments
- [ ] Double-booking is impossible, even under simultaneous requests
- [ ] Email confirmations, cancellations, and 24-hour reminders
- [ ] Owner dashboard with upcoming bookings and simple stats
- [ ] Correct across time zones — everything stored in UTC

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
git clone https://github.com/<your-username>/book-it.git
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

**3. Run the API**

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

## Tests

```bash
cd backend
pytest                  # run the test suite
ruff check .            # lint
ruff format .           # auto-format
```

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
| 2 | Data model and migrations | next |
| 3 | Authentication and roles | planned |
| 4 | Availability and booking logic | planned |
| 5 | Frontend | planned |
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
