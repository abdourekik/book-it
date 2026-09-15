# Book-it: project instructions for Claude Code

## What we are building
Book-it is a web app where small businesses (barbers, clinics, tutors) publish their
availability and customers book appointments. This is project 1 of a 5-project,
2-year portfolio. The owner of this repo is **learning software engineering**, so
teaching matters as much as shipping.

## Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest
- Database: PostgreSQL (Docker locally, Supabase or Neon in production)
- Frontend: Next.js (App Router) with TypeScript and Tailwind CSS
- Email: Resend
- CI: GitHub Actions
- Deploy: Render (backend), Vercel (frontend)

## Repo structure
```
book-it/
  backend/        FastAPI app, models, migrations, tests
  frontend/       Next.js app
  docs/           architecture diagram, screenshots, decisions
  .github/        CI workflows
  CLAUDE.md
  PROGRESS.md
  README.md
  docker-compose.yml
```

## How to work with me (teaching mode)
1. **Plan before code.** For any task, first explain the approach in plain language
   and list the files you will create or change. Wait for my "go" before writing code.
2. **Small steps.** Change at most a few files per step. After each step, stop and
   let me run and test it.
3. **Explain new concepts.** When you use something I probably haven't seen
   (dependency injection, migrations, JWT, async), explain it in 3-5 sentences with
   a simple analogy.
4. **Let me write some code.** For simple parts (a Pydantic schema, a basic test,
   a small component), describe what's needed and ask me to write it, then review
   my version honestly.
5. **Git is my job.** Don't run `git commit` or `git push` yourself. At the end of
   each step, suggest a commit message in Conventional Commits format
   (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`) and show me the commands.
6. **Quality rules.** Never hardcode secrets; use `.env` files and keep them in
   `.gitignore`. Every piece of booking logic gets tests. Store all times in UTC.
   Run tests and the linter before saying a step is done.
7. **Be honest.** If my idea or code has a problem, say so directly and explain why.

## Progress tracking (required every session)
At the end of every working session, or when I say "wrap up":
1. Update the checklist in `PROGRESS.md` (tick finished items, never delete items).
2. Add a new entry at the top of the **Session log** in `PROGRESS.md` using the
   template in that file: date, phase, what was done, what I learned, problems,
   next step.
3. If a meaningful technical decision was made (library choice, data model change),
   add a short entry under **Decisions**.
4. If something is worth sharing publicly, add one line under **LinkedIn ideas**.
5. Show me the final `git add`, `git commit`, and `git push` commands.

At the start of every session, read `PROGRESS.md` first and tell me in 2-3 sentences
where we left off and what the next step is.
