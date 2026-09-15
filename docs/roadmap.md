# Book-it: Claude Code prompts, in order

Use one prompt per session (or split a phase over several sessions). `CLAUDE.md` already
tells Claude Code to teach, plan first, and update `PROGRESS.md`, so these prompts stay short.

**Start every session with:**
```
Read CLAUDE.md and PROGRESS.md. Tell me where we left off and what's next.
```

**End every session with:**
```
Wrap up: update PROGRESS.md following the rules in CLAUDE.md, then give me the git commands.
```

---
    
## Phase 0: Foundations (weeks 1-8)

Do these in a separate folder or repo called `learning` so `book-it` stays clean.

**0.1 Personal tutor**
```
I'm starting to learn programming. Act as my tutor, not my coder. This week's topic is
[Python basics / Git / SQL / HTTP and REST / TypeScript]. Teach me in short lessons.
After each lesson give me 3 exercises, from easy to hard. Don't show solutions until I
submit my attempt, then review my code honestly and point out one habit to improve.
```

**0.2 Mini-project**
```
Help me plan a command-line budget tracker in Python: add expenses, list them, show
totals by category, and save to a JSON file. Break it into 6 small steps. For each step,
explain what to build and let me write the code. Review each step before we continue.
```

---

## Phase 1: Project setup (weeks 9-10)

**1.1 Architecture plan**
```
We're starting Book-it. Before any code, explain the overall architecture: how the
Next.js frontend, FastAPI backend, and PostgreSQL talk to each other. Draw it as a
Mermaid diagram and save it to docs/architecture.md. Then list the setup steps for
Phase 1 and wait for my go.
```

**1.2 Backend skeleton and database**
```
Set up the backend folder: FastAPI app with a /health endpoint, settings loaded from a
.env file, docker-compose.yml for PostgreSQL, ruff for linting, and pytest with one test
for /health. Add a .gitignore and .env.example. Go step by step and explain each file.
```

**1.3 CI and README**
```
Create a GitHub Actions workflow that installs dependencies, runs ruff, and runs pytest
on every push and pull request. Then create a README skeleton with sections: overview,
features, tech stack, architecture, local setup, tests, deployment, roadmap.
```

---

## Phase 2: Data model (weeks 11-12)

**2.1 Design the models**
```
Help me design the database for Book-it: User (with role), Business, Service (name,
duration, price), AvailabilityRule (weekday, start, end), TimeOff, and Booking (status,
start and end in UTC). Explain the relationships and draw an ER diagram in Mermaid in
docs/data-model.md. Let me ask questions before we write any models.
```

**2.2 Implement with migrations**
```
Implement the approved models with SQLAlchemy 2.0 and create the first Alembic
migration. Explain what a migration is and why we don't just create tables directly.
Let me write the Pydantic schemas for Service myself, then review them.
```

**2.3 Seed data**
```
Write a seed script that creates 2 businesses, 3 services each, weekly availability,
and a few bookings, so I can test with realistic data. Show me how to run it.
```

---

## Phase 3: Authentication (week 13)

```
Add authentication: sign up, log in, password hashing, and JWT access tokens, with
roles for business owner and customer. First explain how JWT works with an analogy and
what could go wrong security-wise. Then implement it in small steps, add a dependency
that protects routes by role, and write tests. Let me write the test for a wrong password.
```

---

## Phase 4: Booking logic (weeks 14-15)

**4.1 Available slots**
```
Build the function that calculates available slots for a business, service, and date,
using availability rules, time off, existing bookings, and service duration. This is the
heart of the app, so write the tests first with me: list the edge cases (overlapping
bookings, end of day, time off, time zones) and let me write 3 of the tests before you
implement the function.
```

**4.2 Book, cancel, reschedule**
```
Add API endpoints to create, cancel, and reschedule bookings. Prevent double booking
even if two customers click at the same moment. Explain the race condition and compare
two ways to prevent it (database constraint vs row locking) before choosing. Add tests
and show me the coverage report.
```

---

## Phase 5: Frontend (weeks 16-17)

**5.1 Frontend setup**
```
Set up the frontend folder with Next.js (App Router), TypeScript, and Tailwind. Create a
typed API client for our backend and explain how the frontend stores the login token
safely. Build the log in and sign up pages first.
```

**5.2 Customer booking flow**
```
Build the public business page: business info, list of services, a date picker, and
available slots from the API. Clicking a slot books it after login. Include loading,
empty, and error states, and make it work well on a phone. Let me build the service
list component myself first.
```

**5.3 Owner pages**
```
Build the owner pages: manage services (create, edit, delete) and set weekly availability
and time off. Keep the forms simple and validated on both frontend and backend.
```

---

## Phase 6: Email (week 18)

```
Add email with Resend: confirmation on booking, email on cancellation, and a reminder
24 hours before the appointment using a scheduled background job. Explain options for
scheduling jobs on Render and pick the simplest one. Emails must never block the API
response.
```

---

## Phase 7: Owner dashboard (week 19)

```
Build the owner dashboard: upcoming bookings for the next 7 days, and stats for bookings
this week, cancellation rate, and busiest weekday. Let me write the SQL query for the
busiest weekday myself first, then compare it with the SQLAlchemy version.
```

---

## Phase 8: Launch (week 20)

**8.1 Deploy**
```
Walk me through deploying: database on Supabase (or Neon), backend on Render, frontend on
Vercel, environment variables in each, CORS, running migrations in production, and a
custom domain. Give me a checklist and help me debug anything that fails. Don't paste any
secrets into files.
```

**8.2 Portfolio polish**
```
Help me finish the README like a product page: short pitch, GIF placeholder, live link,
features, architecture diagram, tech decisions and why, how to run locally, tests and CI
badges, and what I'd improve next. Then write a 90-second demo video script.
```

**8.3 Launch post**
```
Read PROGRESS.md (session log, decisions, and LinkedIn ideas) and draft a LinkedIn launch
post: what I built, one hard problem I solved, what I learned, the live link and repo
link. Keep it honest, under 200 words, no hype words.
```

---

## Week 1 LinkedIn kickoff post (edit it in your own voice)

> I'm starting a 2-year challenge: building and deploying 5 real software projects,
> from web apps to data pipelines to AI products, all public on GitHub.
>
> Project 1 is Book-it, an appointment booking app for small businesses like barbers,
> clinics, and tutors. The first weeks are about foundations: Python, Git, SQL, and how
> the web works.
>
> I'll share what I build, what breaks, and what I learn along the way. If you've been
> through this journey, I'd love your advice.
