# 90-second demo video script

Record at 1280×720 or larger. Two browser windows side by side — one as the owner, one
as a customer in a private window — so you never have to log in and out on camera.

**Before you press record:** create the business, add two or three services, set opening
hours, and make one booking so the dashboard is not empty. Nobody wants to watch you fill
in forms, and an empty dashboard looks like a broken app.

---

### 0:00–0:10 — What it is

> "Book-it is an appointment booking app for small businesses — barbers, clinics,
> tutors. They publish their hours, customers pick a slot, and the app makes sure two
> people can never book the same one."

*On screen: the public booking page for your business.*

---

### 0:10–0:30 — Booking as a customer

*Click a service. Pick a date. The times appear.*

> "Times come from the business's opening hours, minus their time off, minus whatever is
> already booked. Everything is stored in UTC and shown in the shop's timezone, so
> daylight saving never shifts anyone's appointment."

*Click a slot, type a name and email, confirm.*

> "No account needed."

---

### 0:30–0:45 — The confirmation

*The confirmation page appears.*

> "This link is the customer's handle on the booking — it arrives by email, and it is how
> they cancel without ever creating a password."

*Cancel it. Go back. The slot is available again.*

---

### 0:45–1:05 — The hard part

*Show `tests/test_bookings.py`, the concurrency test.*

> "The interesting problem is two people clicking the same slot at the same moment.
> Checking in Python does not fix it — there is a gap between the check and the insert.
> So PostgreSQL enforces it with an exclusion constraint."

*Show the constraint, then the test run: 10 threads, one winner.*

> "Ten simultaneous requests for the same slot. Exactly one succeeds. Drop the
> constraint and all ten get in."

---

### 1:05–1:20 — The owner side

*Switch to the dashboard.*

> "Owners get their week at a glance — bookings, cancellation rate, busiest day — and
> manage services, hours, and time off. Blocking out time that clashes with a confirmed
> booking is refused, so you can't be double-promised."

---

### 1:20–1:30 — Close

> "FastAPI and PostgreSQL on the backend, Next.js on the front. Around 160 tests,
> including the concurrency one. Code and live link below."

---

## Recording notes

- **Zoom the browser to 125%.** Default text is unreadable when the video is scaled down
  in a LinkedIn feed.
- **Use realistic names.** "Joe's Barbershop" and "Haircut — 30 min — €25" read as a real
  product; "test test 123" reads as a toy.
- **Cut every loading pause.** Even one second of nothing feels long on video.
- **No audio?** Add captions. Most people watch feed video muted.
- Keep it under 90 seconds. The concurrency demo is the memorable part — if you have to
  cut something, cut the owner dashboard, not that.
