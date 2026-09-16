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
- [x] Models: User, Business, Service, AvailabilityRule, Booking (+ TimeOff)
- [x] Alembic migrations working
- [x] Seed script with sample data
- [x] Data model diagram in docs/

### Phase 3: Authentication (week 13)
- [x] Sign up and log in with hashed passwords
- [x] JWT access tokens
- [x] Roles: business owner and customer
- [x] Auth tests (49 tests: hashing, JWT, signup, login, role protection)

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

**2026-09-16: Authorisation reads the database, not the token's role claim.**
`get_current_user` loads the User by id on every request rather than trusting the `role`
claim inside the JWT. A token is a snapshot of who someone was at login; by the time it is
used, the account may have been deleted or demoted, and a JWT cannot be revoked. Trusting
the claim would give a demoted owner up to 30 more minutes of owner powers over other
people's calendars. The cost is one indexed primary-key lookup per request. The `role`
claim is kept so the frontend can render the right UI without an extra call, but it is
never what the server authorises against. Tested: changing a role in the database takes
effect on the very next request with the same token.

401 and 403 are used distinctly: 401 means "credentials missing or invalid, try
authenticating"; 403 means "we know who you are and the answer is still no". Retrying
after a 401 can work; retrying a 403 cannot.

**2026-09-16: Auth stack - argon2 for passwords, PyJWT for tokens.**
argon2id rather than bcrypt (no 72-byte truncation limit) and rather than passlib (which
has known friction with modern bcrypt releases). PyJWT rather than python-jose, which is
better maintained. `SECRET_KEY` is a required setting with no default: a default secret
ships to production unnoticed and lets anyone who read the source mint a token for any
user. It is a pydantic `SecretStr`, so it shows as `**********` in logs and tracebacks.

A test caught a real bug: `verify_password` caught `VerifyMismatchError`, but a malformed
argon2 hash raises its PARENT class `VerificationError`. In production that would have
turned a login into a 500 rather than a clean 401 - both a crash and a signal that
something is unusual about that specific account.

Login returns one identical response for "no such email" and "wrong password", and hashes
a dummy value when the user does not exist so the two paths take similar time. Different
responses (or response times) turn the endpoint into an account-enumeration oracle, which
for a booking app reveals who is a customer of which business.

**2026-09-16: Tests run against a real PostgreSQL, not SQLite.**
`tests/conftest.py` derives a `bookit_test` database from `DATABASE_URL`, creates it if
absent, and builds it with the real Alembic migrations rather than `create_all()` - so
drift between models and migrations fails the tests instead of hiding. Each test runs
inside a transaction that is rolled back afterwards, so tests are isolated without paying
to recreate the schema. CI gained a `services: postgres` block for the same reason:
SQLite cannot reproduce the exclusion constraint that Phase 4 depends on, so testing
against it would prove nothing about the behaviour that matters most.

**2026-09-16: Alembic reads DATABASE_URL from app settings, not alembic.ini.**
The generated `alembic.ini` ships with a hardcoded `sqlalchemy.url`. That line is commented
out and `alembic/env.py` imports `app.config.settings` instead, so there is one source of
truth and no password is ever committed. `env.py` also uses `create_engine` directly rather
than `engine_from_config`, because the latter routes the URL through configparser, where a
`%` in a password is treated as an escape character.

Autogenerate captured the ExcludeConstraint correctly but missed two things that had to be
added by hand: `CREATE EXTENSION IF NOT EXISTS btree_gist` in `upgrade()` (without it the
constraint fails with "data type integer has no default operator class for access method
gist"), and dropping the `user_role` and `booking_status` enum types in `downgrade()`
(`drop_table` leaves them behind, so a second upgrade failed with "type already exists").
Verified by a full upgrade -> downgrade -> upgrade round trip, then a drift check that
generated an empty migration.

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
