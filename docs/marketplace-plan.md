# Plan: turning Book-it into a marketplace

## The change in one sentence

Today a customer needs a link. After this, a customer can **arrive at the homepage, browse
businesses by category and city, and book** — the Booksy model instead of the Calendly one.

## What this does NOT change

Worth being explicit, because it is most of the project:

- the data model for services, hours, time off, and bookings
- the slot-availability engine and all its timezone handling
- the exclusion constraint that prevents double-booking
- authentication, roles, and the owner dashboard
- email

**The booking engine is untouched.** This is a front door on a finished building.

---

## 1. Data model

Four columns on `businesses`. One migration, all additive, so it is safe to deploy while
the app is running.

| Column | Type | Why |
|---|---|---|
| `category` | enum | The primary filter. An enum, not free text, so "Barber", "barber" and "barbershop" cannot become three categories. |
| `city` | `VARCHAR(80)`, nullable | The second filter. Free text for now — a proper places table is a different project. |
| `image_url` | `TEXT`, nullable | A directory of businesses with no photos looks broken. |
| `is_listed` | `BOOLEAN`, default `true` | Lets a business opt out of the directory and keep the private-link behaviour it has today. |

Starting categories: `barber`, `salon`, `clinic`, `dentist`, `tutor`, `fitness`, `other`.
Adding one later is a migration, which is the point of an enum — the list is deliberate
rather than accidental.

### On `is_listed`

Defaulting to `true` means every existing business appears in the directory the moment
this ships. That is the right default for a product whose homepage is a directory, but it
is a real change in posture: someone who signed up for a private link is now publicly
listed. With two demo businesses that is fine. On a real product it would need an
announcement, and arguably the opposite default.

### On images: paste a URL, do not upload (yet)

Store a URL, never image bytes. Bytes in Postgres bloat every backup and turn an image
load into a database query.

Two ways to get a URL in:

**Now — the owner pastes one.** Any image they already host. One text field, zero
infrastructure, ~20 minutes.

**Later — real uploads via Supabase Storage.** A bucket, signed upload URLs, file type and
size validation, and handling the case where the upload succeeds but the database write
fails. Two hours or so, and worth doing eventually because "paste a URL" is not something
a real salon owner will do.

Ship the first, leave the door open for the second.

---

## 2. Backend

### `GET /businesses` — public, no auth

```
/businesses?q=barber&category=barber&city=Sfax&limit=24&offset=0
```

| Parameter | Behaviour |
|---|---|
| `q` | Case-insensitive match on name and description |
| `category` | Exact match on the enum |
| `city` | Case-insensitive exact match |
| `limit` / `offset` | Paging, `limit` capped at 50 so nobody can ask for everything |

Returns `{ items: [...], total: n }` — the total is needed to render "24 of 137".

Each item is a **card**, not a full business: name, slug, category, city, image_url, a
truncated description, and `from_price` (the cheapest active service). Deliberately not the
full service list — a directory page showing 24 businesses should not carry every service
of every one of them.

Only businesses that are `is_listed` **and have at least one active service** appear. A
business with nothing bookable in a directory is a dead end for the customer.

### `GET /businesses/categories`

Returns the categories that actually have listed businesses, with counts. Filter chips
showing "Dentist (0)" look broken.

### Owner endpoints

`POST /me/business` and `PATCH /me/business` accept the four new fields. `BusinessRead`
returns them so the settings form can show current values.

### Tests

- filtering by category, city, and `q`, and the three combined
- unlisted businesses are excluded
- a business with no active services is excluded
- paging returns the right window and a correct `total`
- `limit` above the cap is rejected rather than honoured
- an unknown category is a 422, not an empty list — a typo should be loud

---

## 3. Frontend

### `/` becomes the directory

- search box, category chips, city filter
- a responsive grid of business cards
- empty state that suggests clearing filters rather than just saying "no results"

**Filters live in the URL**, exactly like the slot picker: `/?category=barber&city=Sfax`.
Same benefits — server-rendered results, no loading spinner, shareable links, working back
button, and no client-side fetching to get wrong.

### `/b/[slug]` gains a header image

Cover photo, category, and city above the existing service list. The booking flow below it
does not change at all.

### Owner settings

Four more fields: category dropdown, city, image URL, and a "List in the public directory"
toggle. The image field shows a live preview — a broken URL should be obvious before it
reaches a customer.

---

## 4. Demo data

Extend `scripts/demo_data.py` to create **six businesses across four categories in two
cities**, each with photos, services, hours, and a few bookings.

This matters more than it sounds. A directory with one business in it does not look like a
directory, and this script is what makes the deployed app demonstrate itself to anyone who
opens the link.

---

## Order of work

| # | Step | Rough effort |
|---|---|---|
| 1 | Migration + model columns | 20 min |
| 2 | `GET /businesses` + categories endpoint + tests | 45 min |
| 3 | Owner settings fields | 30 min |
| 4 | Directory homepage | 45 min |
| 5 | Business page header image | 15 min |
| 6 | Demo data for six businesses | 20 min |
| 7 | Deploy and verify | 15 min |

**About three hours**, and every step leaves the app working — nothing here breaks the
current behaviour, so it can be stopped after any step.

---

## Explicitly out of scope

Marketplaces attract features endlessly. These are all reasonable, and none of them belong
in this version:

- reviews and ratings
- favourites or saved businesses
- maps and geographic search
- payments and deposits
- multiple businesses per owner
- messaging between customer and business
- staff members within a business

Any one of them is a project. The line is: **browse, filter, book.**

---

## The honest counter-argument

The app works and is deployed. The remaining Phase 8 work — demo video, README with
screenshots, launch post — is what actually gets the project *seen*, and it is maybe two
hours.

Building the marketplace first risks ending the week with a half-finished pivot instead of
a finished project.

**The mitigation is to tag what exists first.** Commit, tag `v1.0`, and write the README
for the version that works today. Then the marketplace is an improvement on top of
something complete, rather than a replacement for it.
