# Library Lending System

**Language:** Python (FastAPI) &nbsp;|&nbsp; **Needs:** Postgres + Redis

This is a **starter**. The application already works. Your job is everything
that gets it building, tested and running in CI.

---

## You do not need Python installed

You will build this into a container, and the container brings its own
Python 3.12. You are not being asked to extend the app — you are being asked
to ship it.

---

## 1. What this app needs

| | |
|---|---|
| **Runtime** | Python 3.12 |
| **Install dependencies** | `pip install -r requirements.txt` |
| **Start the app** | `uvicorn app.main:app --host 0.0.0.0 --port 8080` |
| **Listens on** | port 8080, bound to `0.0.0.0` |
| **Environment variables** | `DATABASE_URL`, `REDIS_URL` |
| **Needs running first** | Postgres, Redis, and the migrations applied |

### What it does

Students borrow and return books. The system tracks due dates, charges a late fine with a grace period and a weekend exemption, caps how many books one person may hold, and refuses to lend to anyone with unpaid fines or an overdue book already out.

### Endpoints

```
GET  /health
GET  /books                          every title with copies / available
GET  /books/{id}/availability        Redis-cached, says whether it was a cache hit
GET  /members/{id}                   loans, fines, and the running fine on open loans
POST /borrow                         {"member_id":1,"book_id":3}
POST /return                         {"loan_id":5}   -> returns the fine charged
POST /loans/{id}/renew               extends the due date, twice at most
POST /members/{id}/fines/pay         clears everything outstanding
```

`/health` reports Postgres and Redis **separately**. If it says
`postgres: false` the app started fine and your compose wiring is wrong —
do not go looking in the application code.

### Migrations

`migrations/` holds `.sql` files applied **in filename order** before the app
starts. They create the tables and insert sample data. A container running
`psql` over them in order is enough; you do not need a migration tool.

---

## 2. What you must write

| File | What it has to do |
|---|---|
| `Dockerfile` | Install dependencies **before** copying source, pin the base image, do not run as root. |
| `docker-compose.yml` | App + Postgres + Redis + a migration step, one `docker compose up`. |
| `.circleci/config.yml` | lint → unit tests → integration tests → secret scan → image build |
| Unit tests | For `app/fines.py`. No database, no network. |
| Integration tests | Against a real Postgres and Redis as CircleCI service containers. |

Then push your image to **your own Docker Hub account**, tagged `:1.0`.

### When it works

```bash
docker compose up --build
curl localhost:8080/health
```

```json
{"status":"ok","postgres":true,"redis":true}
```

---

## Where the marks are

`app/fines.py` is **pure logic** — plain functions over plain data, no
database and no HTTP. Start your tests there. Use pytest:
`pytest --cov=app --cov-report=term-missing`. Minimum 70%.

Start with `chargeable_days`. Pick a Friday, return the book the following Tuesday, and work out on paper what the answer should be before you write the assertion.

## Why Redis is here

Two different jobs, and it is worth keeping them apart in your head. `avail:{book_id}` caches the answer to "has this book got a free copy" for 30 seconds, because the catalogue page asks it constantly. `lock:borrow:{book_id}` is a short SET NX PX lock held only while one borrow is being confirmed, released with a token check so a slow request can never delete a lock that has already expired and been taken by somebody else.

## The hard part

The last copy of a book, requested by two students at once. Exactly one should succeed.

The Redis lock in `app/main.py` is not the answer - it is a convenience. Redis locks expire, and a process can be paused between taking the lock and using it. Find the two things in this codebase that make the guarantee real: the conditional `UPDATE ... WHERE status='available' ... RETURNING` inside a single transaction, and the partial unique index `loans_one_active_per_copy`. Explain why either one alone would still be correct, why the UPDATE must not be split into a SELECT followed by an UPDATE on a second connection, and what the client should see when it loses - a 409, not a 500.

### Concurrency Guarantee: Architectural Analysis

#### 1. Why the Redis Lock is a Convenience, Not the Guarantee
The Redis lock (`lock:borrow:{book_id}` via `SET NX PX` with a 4000ms TTL) in [app/main.py](file:///c:/Users/rasen/library-lending-python/app/main.py) is a cooperative application-level optimization to fast-fail or serialize contention before touching the database. It cannot provide absolute safety because:
- **Lock Expiration & Client Pauses:** If an application worker acquires the Redis lock and experiences an unexpected pause (such as Python garbage collection, OS thread preemption, or network latency) lasting longer than 4000ms, Redis will automatically expire the key. A second worker can then acquire the lock while the first is still running.
- **Split-Brain / Failover:** Redis without fencing tokens cannot guarantee mutual exclusion in distributed failure or failover conditions.

Therefore, the database alone must enforce data integrity.

#### 2. The Two Real Database Guarantees
The codebase relies on two database mechanisms to guarantee that two students racing for the last copy will result in exactly one winner:

1. **Conditional `UPDATE ... WHERE status='available' ... RETURNING` with `SKIP LOCKED`:**
   ```sql
   UPDATE copies SET status='on_loan' WHERE id = (
     SELECT id FROM copies WHERE book_id=%s AND status='available'
     ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
   ) RETURNING id, barcode
   ```
   - **How it works:** Within a single transaction and connection, PostgreSQL row-level locks the available copy. When two concurrent requests run this query simultaneously, one transaction locks and updates the candidate row to `'on_loan'`. The second transaction skips that locked row (`SKIP LOCKED`), finds no remaining rows satisfying `status='available'`, and updates zero rows. `cur.fetchone()` returns `None`, and the code explicitly raises `HTTPException(409, "no_copies_available")`.
   - **Why this alone is sufficient:** Row updates in PostgreSQL are strictly serialized at the row level. A row cannot simultaneously transition from `'available'` to `'on_loan'` twice.

2. **Partial Unique Index `loans_one_active_per_copy`:**
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS loans_one_active_per_copy
       ON loans (copy_id) WHERE returned_on IS NULL;
   ```
   - **How it works:** Defined in [migrations/001_schema.sql](file:///c:/Users/rasen/library-lending-python/migrations/001_schema.sql), this partial unique index enforces that for any given `copy_id`, there can be at most one row in `loans` where `returned_on IS NULL`.
   - **Why this alone is sufficient:** Even if the copy status update did not exist or failed to lock, two simultaneous `INSERT INTO loans` statements for the same `copy_id` would conflict at the index level. PostgreSQL will abort the losing transaction with a unique constraint violation (`unique_violation`), guaranteeing that two active loans can never exist for a single physical book copy.

#### 3. Why the UPDATE Must NOT Be Split (Check-Then-Act Antipattern)
If the operation were split into:
1. `SELECT id FROM copies WHERE book_id=%s AND status='available'` on Connection 1; followed by
2. `UPDATE copies SET status='on_loan' WHERE id=%s` on Connection 2;

both connections could read the same available copy ID at the exact same moment (Time-of-Check to Time-of-Use / TOCTOU race condition). Both would believe they own the copy and execute the update, resulting in double-allocation or race bugs. Combining the selection, locking (`FOR UPDATE SKIP LOCKED`), and status transition in a single atomic statement inside one transaction eliminates the time gap between check and mutation.

#### 4. Why the Client Must Receive 409 Conflict, Not 500
- **HTTP 500 (Internal Server Error)** signifies an unhandled bug, unhandled exception, or unexpected crash in the system.
- **HTTP 409 (Conflict)** is the standard REST status code when a request cannot be processed due to a conflict with the current state of the resource.
Contention for the last copy of a book is an expected business reality in a concurrent library system, not a system failure. The losing client is cleanly informed that the resource was taken (`409 Conflict`), allowing frontend interfaces to present an informative notice (e.g. "This book has just been checked out by another student") rather than an ambiguous crash screen.

---

## Getting unstuck

| Symptom | Almost always |
|---|---|
| `/health` says `postgres: false` | Wrong hostname. In compose the host is the **service name**, not `localhost`. |
| Page will not load, logs fine | No `ports:` mapping, or bound to `127.0.0.1` not `0.0.0.0`. |
| `relation "..." does not exist` | Migrations did not run, or the app started before they finished. |
| Build takes minutes each time | `COPY . .` is above your dependency install. |
| CI cannot reach the database | In CircleCI service containers the host **is** `localhost` — opposite of compose. |
