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
- [x] Owners set weekly availability and time off
- [x] Available slots calculated for a given date and service
- [x] Customers book, cancel, reschedule
- [x] Double-booking prevented (tested, including simultaneous requests)
- [x] Time zones handled, everything stored in UTC (incl. daylight saving, tested)
- [x] Booking logic test coverage above 80% (availability.py 99%; project 95%, 127 tests)

### Phase 5: Frontend (weeks 16-17)
- [x] Public business page with service list and slot picker
- [x] Customer sign up, log in, and "my bookings" page
- [x] Owner pages: services and availability management
- [x] Mobile-friendly layout, loading and error states

### Phase 6: Email (week 18)
- [x] Booking confirmation email
- [x] Cancellation email
- [x] Reminder 24 hours before appointment (hourly cron, idempotent)

### Phase 7: Owner dashboard (week 19)
- [x] Upcoming bookings list
- [x] Stats: bookings this week, cancellation rate, busiest day

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

### 2026-09-16 | Phases 1-7 (Phase 8 prepared)
**Done:** Built the whole application in one session. Project setup with Docker Postgres,
ruff, pytest and GitHub Actions CI. Six-table data model with migrations and a two-timezone
seed script. Authentication with argon2 and JWTs, role-protected routes. The availability
engine and booking endpoints, including cancel and reschedule. Owner management for
services, weekly hours and time off. A Next.js frontend: auth pages, the public booking
page, my-bookings, and an owner dashboard. Transactional email with an hourly reminder job.
Deployment blueprint, deployment guide, and demo script written. 163 backend tests, 95%
coverage; frontend lint, typecheck and build clean.

**Learned:**
- An error message that contradicts what you believe about the system is a reason to check
  the belief, not the message. "Password authentication failed" turned out to be two
  processes bound to the same port and me talking to the wrong database entirely.
- Coverage says a line ran; mutation testing says it matters. Breaking the slot engine seven
  ways on purpose caught one genuinely weak spot the green suite had hidden.
- Some correctness cannot live in application code. Double-booking is prevented by a
  PostgreSQL exclusion constraint because the gap between "check if free" and "insert" is
  where the bug lives, and no amount of careful Python closes it.
- Storing a JWT in localStorage means one XSS bug is full account takeover. An httpOnly
  cookie is invisible to JavaScript, which I confirmed by typing `document.cookie` into the
  console while signed in and getting an empty string back.
- The App Router's answer to "fetch when state changes" is usually "put the state in the
  URL and let the server render it" - which removed an entire class of race conditions
  along with the useEffect.

**Problems:**
- The concurrency test found a real bug in the booking endpoint: under load PostgreSQL
  aborts the losers with deadlock_detected (40P01), not the exclusion violation I was
  catching, so those requests would have returned 500 instead of a clean 409.
- `verify_password` caught VerifyMismatchError but a malformed hash raises its parent
  VerificationError, which would have turned a login into a 500. Caught by a test written
  specifically to check that garbage fails closed.
- Alembic autogenerate missed `CREATE EXTENSION btree_gist` and left the enum types behind
  on downgrade, so the second upgrade failed. Both only surfaced by actually running the
  migration up, down, and up again.
- Two Next.js 16 rules cost a build each: a "use server" file may export only async
  functions, and redirect() must sit outside try/catch because it works by throwing.

**Next step:** Deploy. Database on Supabase or Neon, API on Render using render.yaml,
frontend on Vercel - the checklist is in docs/deployment.md. Then record the demo, finish
the README with a GIF and the live link, and publish the launch post.

## Decisions
<!-- Example: YYYY-MM-DD: Chose SQLAlchemy over raw SQL because... -->

**2026-09-16: The slot picker keeps its state in the URL, not in React.**
First version fetched slots in a useEffect and called setState. The linter rejected it
(react-hooks/set-state-in-effect) and it was right - the App Router has a better answer.
Service and date now live in the query string, so the Server Component renders the slot
list itself: the times arrive with the HTML, there is no loading spinner, API_BASE_URL is
never sent to the browser, the URL is shareable, the back button works, and the whole
class of stale-response races disappears because nothing is fetched on change. Only the
date input and the confirm form are Client Components.

Two rendering rules that look contradictory but are not: the slot picker formats times in
the BUSINESS's timezone (a customer in London booking a Paris barber must see the time the
barber expects them), while the confirmation page formats in the VISITOR's timezone and
locale (their own calendar, their own language). Verified live - the confirmation rendered
"mardi 22 septembre 2026" on a French browser.

The full journey was exercised in a real browser, not assumed: choose service, choose day,
pick 09:00, book as a guest, land on the capability URL, cancel, and confirm the slot
returned to the list. The seeded bookings show through correctly too - 09:30 jumps to
10:30 around an existing 10:00 appointment, 10:30 itself is offered (back-to-back works),
and 11:30 jumps to 14:00 across the lunch break.

The "every free minute" decision is now visible: 254 buttons for one 30-minute service on
one day. The grid is capped with overflow scrolling so it stays usable, but if it feels
wrong in practice, raising slot_interval_minutes to 15 is a config change.

**2026-09-16: The frontend stores the session in an httpOnly cookie, not localStorage.**
localStorage is what most tutorials use and it is why one XSS bug becomes full account
takeover: any injected script can read the token and send it anywhere. An httpOnly cookie
is invisible to JavaScript entirely. Our API returns the token in a JSON body, so a Next.js
Server Action does the bridging - the form posts to server code, which calls FastAPI and
writes the cookie, and the token never enters the browser's JavaScript at any point.

Verified in the running app rather than assumed: while signed in, `document.cookie` is the
empty string and both localStorage and sessionStorage are empty objects. With localStorage
that first value would have printed the access token.

Side benefit: because the frontend calls FastAPI from the server, there is no cross-origin
request and therefore no CORS configuration to get wrong. `sameSite=lax` covers the CSRF
exposure that cookies would otherwise introduce. `src/lib/session.ts` starts with
`import "server-only"`, so if a client component ever imports it the build fails instead of
quietly shipping token-handling code to the browser.

Two Next.js 16 rules cost a build failure and are worth remembering: a `"use server"` file
may export ONLY async functions (a plain exported object is a build error, because every
export becomes a callable server endpoint), and `redirect()` must be called OUTSIDE a
try/catch because it works by throwing - inside, the catch swallows it and the redirect
silently never happens.

**2026-09-16: Owner endpoints are addressed as /me/..., never /businesses/{id}/...**
Every owner route reaches the business through the authenticated user rather than an id in
the URL. A route shaped `/businesses/{id}/services` has to remember an ownership check on
every handler, and eventually one will not have it. With `/me/services` there is nothing
to forget - an owner can only ever address their own business. Where an id is unavoidable
(a service id), a wrong one returns 404 rather than 403, so ids cannot be enumerated.

Weekly hours are replaced wholesale with PUT /me/availability rather than per-rule CRUD.
An owner thinks "these are my hours", not "delete rule 7"; sending the complete set makes
the update atomic, so a half-applied schedule cannot exist.

Time off that clashes with a confirmed booking is refused with 409. Availability changes
are not checked the same way, and the asymmetry is deliberate: narrowing opening hours only
affects what is offered in future, while time off is an explicit claim to be absent - and
accepting it would leave the owner committed to an appointment and away at the same time,
with the customer finding out at a closed door.

**2026-09-16: Double-booking is prevented by the database constraint, not by row locking.**
Two options were weighed. `SELECT ... FOR UPDATE` works but is a discipline that must be
reapplied at every write site forever, and it serialises all bookings for a business
including non-conflicting ones. The exclusion constraint cannot be forgotten, only fails
actual conflicts, and also protects against writes that never pass through this code.
Python still checks availability first, but only for a friendly message - correctness
comes from PostgreSQL.

Proved rather than assumed: 10 threads on 10 real connections, released together by a
threading.Barrier, all inserting the same slot. Exactly one wins. With the constraint
dropped, all ten won - ten people booked the same haircut - so the test has real teeth.

That test found a genuine production bug. Under concurrent conflicting inserts,
PostgreSQL often aborts the losers with **deadlock_detected (40P01)** rather than an
exclusion violation, because each transaction waits to learn whether the others commit
and the waits form a cycle. The endpoint caught only IntegrityError, so those requests
would have returned 500 instead of a clean 409. Now both IntegrityError and the transient
SQLSTATE codes (40P01, 40001) map to 409. Note the cost: deadlock detection takes about a
second per cycle, which makes this the slowest test in the suite at up to ~10s.

Guests cancel and reschedule through a capability URL - the random `access_token` from the
booking row. An unknown token returns 404 rather than 403, because confirming that a token
exists but belongs to someone else would help an attacker guess them. Cancelling twice
returns 200 rather than an error, so clicking the emailed link twice is harmless.

**2026-09-16: available_slots() is a pure function; the database layer sits outside it.**
It takes rules, bookings, and time off as arguments instead of querying for them, so the
hardest logic in the project is testable with no database, no fixtures, and no mocking -
32 tests run in 0.14s. Interval arithmetic is half-open `[start, end)` throughout, which
is what lets a 09:30-10:00 booking sit against a 10:00-10:30 one without counting as
overlapping. It matches the `tstzrange` semantics of the database exclusion constraint, so
Python and PostgreSQL agree on what "taken" means.

Daylight saving needs no special case: opening rules are stored as wall-clock TIME and
converted to UTC per date, so the shop opens at 09:00 local all year. Verified across the
25 October 2026 Paris transition - same local time, different UTC instant.

Mutation testing found the suite's one real weakness. Six of seven deliberate bugs were
caught; `Interval.overlaps` using `<=` instead of `<` was not, because overlaps() is only
reached via minus(), which recomputes the right pieces anyway - an equivalent mutant. But
booking creation (4.2) will call overlaps() directly, where that bug would reject every
back-to-back appointment. Added seven boundary tests pinning the contract; all seven
mutations are now caught.

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
- Signed into my app, opened the console, typed `document.cookie` — empty string. localStorage — empty. Yet I'm logged in. That's the difference between storing a JWT in localStorage and in an httpOnly cookie, and it's the difference between one XSS bug being annoying and being account takeover.
- I wrote a test that fires 10 simultaneous requests at the same appointment slot. Exactly one wins. Then I dropped the database constraint and re-ran it: all 10 won. That's the difference between code that looks correct and code that is.
- The concurrency test found a bug I'd never have reasoned my way to: under load, PostgreSQL rejects the losers with a DEADLOCK, not a constraint violation. My handler only caught the latter, so those users would have seen a 500.
- Mutation testing on my booking engine: I broke my own code 7 ways on purpose to see if the tests noticed. They caught 6. The 7th taught me more than the 6 combined.
- "Password authentication failed" - except the password was fine. Two processes were bound to the same port and I was talking to the wrong database entirely. When an error contradicts what you believe about the system, check the belief first.
- Why my booking app stores "Tuesdays 09:00" as wall-clock time but appointments as UTC - and how that one distinction makes daylight saving a non-event.
