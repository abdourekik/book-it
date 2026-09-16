# Book-it progress

**Started:** 2026-09-15  
**Target launch:** end of month 5  
**Live URL:** not deployed yet (repo: https://github.com/abdourekik/book-it)  
**Current phase:** Phase 1: Project setup

## Checklist

### Phase 0: Foundations (weeks 1-8) — SKIPPED, see Decisions 2026-09-15
- [x] Tools installed: Git, Python 3.12, Node.js LTS, VS Code, Docker Desktop, Claude Code
- [ ] GitHub account, public `book-it` repo created and cloned
- [ ] Python basics: variables, functions, lists, dicts, loops, classes
- [ ] Git basics: commit, branch, merge, pull request
- [ ] SQL basics: SELECT, JOIN, GROUP BY, INSERT, UPDATE
- [ ] HTTP and REST basics: requests, status codes, JSON
- [ ] JavaScript and TypeScript basics
- [ ] Mini-project: command-line budget tracker in Python, pushed to GitHub
- [ ] LinkedIn kickoff post published

### Phase 1: Project setup (weeks 9-10)
- [ ] Monorepo structure with backend/ and frontend/ (backend/ done; frontend/ comes in Phase 5)
- [x] PostgreSQL running with docker compose
- [x] FastAPI "hello world" with health check endpoint
- [x] Linting and formatting (ruff) and pytest configured
- [x] GitHub Actions CI running tests on every push
- [x] README skeleton

### Phase 2: Data model (weeks 11-12)
- [ ] Models: User, Business, Service, AvailabilityRule, Booking
- [ ] Alembic migrations working
- [ ] Seed script with sample data
- [x] Data model diagram in docs/

### Phase 3: Authentication (week 13)
- [ ] Sign up and log in with hashed passwords
- [ ] JWT access tokens
- [ ] Roles: business owner and customer
- [ ] Auth tests

### Phase 4: Booking logic (weeks 14-15)
- [ ] Owners set weekly availability and time off
- [ ] Available slots calculated for a given date and service
- [ ] Customers book, cancel, reschedule
- [ ] Double-booking prevented (tested, including simultaneous requests)
- [ ] Time zones handled, everything stored in UTC
- [ ] Booking logic test coverage above 80%

### Phase 5: Frontend (weeks 16-17)
- [ ] Public business page with service list and slot picker
- [ ] Customer sign up, log in, and "my bookings" page
- [ ] Owner pages: services and availability management
- [ ] Mobile-friendly layout, loading and error states

### Phase 6: Email (week 18)
- [ ] Booking confirmation email
- [ ] Cancellation email
- [ ] Reminder 24 hours before appointment

### Phase 7: Owner dashboard (week 19)
- [ ] Upcoming bookings list
- [ ] Stats: bookings this week, cancellation rate, busiest day

### Phase 8: Launch (week 20)
- [ ] Database on Supabase or Neon
- [ ] Backend deployed on Render
- [ ] Frontend deployed on Vercel with a custom domain
- [ ] Production smoke test by a friend on their phone
- [ ] README complete: GIF, live link, architecture diagram, setup steps, badges
- [ ] 60-90 second demo video recorded
- [ ] LinkedIn launch post published, project added to Featured
- [ ] Repo pinned on GitHub profile

## Session log
<!-- Newest entry on top. Template:
### YYYY-MM-DD | Phase X
**Done:** 
**Learned:** 
**Problems:** 
**Next step:** 
-->

## Decisions
<!-- Example: YYYY-MM-DD: Chose SQLAlchemy over raw SQL because... -->

**2026-09-16: Data model decisions (see docs/data-model.md).**
Four choices settled before writing any models. (1) Single role per user for v1 — a barber
who books elsewhere needs a second account. (2) Availability is per business, not per
service, to keep the Phase 4 slot algorithm tractable. (3) No fixed slot grid: slots are
offered every free minute (`slot_interval_minutes` defaults to 1). Chosen against my
recommendation of a 15-minute grid; stored as a column so it can be raised later without
touching the algorithm. Note that 09:00-17:00 with a 30-minute service yields 451 offered
start times, so the Phase 5 picker will need to handle a long list. (4) Guest booking is
allowed: `customer_id` is nullable with `guest_name`/`guest_email` beside it, guarded by a
CHECK constraint, plus a random `access_token` so guests can cancel via an emailed link.
Better conversion, more edge cases in Phases 4 and 6.

Double-booking will be prevented by a PostgreSQL EXCLUDE constraint using btree_gist
(overlapping tstzrange per business, confirmed bookings only), not by a check-then-insert
in Python, which has a race window between the check and the insert.

**2026-09-16: Local Postgres container published on host port 15432, not 5432.**
This machine already runs native PostgreSQL 15 (port 5432) and 18 (port 5433) as Windows
services. On Windows the Docker port proxy can bind a port that is already taken without
erroring, so connecting to 5433 silently reached the native server instead and failed with
"password authentication failed for user bookit" — a misleading error, since the real cause
was talking to the wrong database entirely. Chose 15432 (outside the 5432-5434 range that
Postgres installers claim) rather than stopping the native services, which belong to other work.

**2026-09-15: Skipped Phase 0 (foundations) and started directly at Phase 1.**
Reason: preference for learning by building rather than by exercises. Consequence:
concepts that Phase 0 would have covered (Python syntax, SQL, HTTP, TypeScript) get
explained inline as they come up, so Phase 1-2 will move slower than planned. Phase 0
checklist items are left unticked on purpose — they are still genuine gaps, not done work.


## LinkedIn ideas
<!-- One line each: a bug, a lesson, a before/after, a screenshot worth sharing -->
