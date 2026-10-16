from datetime import date
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from . import cache, db
from .fines import (LOAN_DAYS, can_borrow, can_renew, due_date, fine_for,
                    member_summary, projected_fine, renewed_due_date)
from .ui import UI_HTML

app = FastAPI(title="library-lending")

AVAIL_TTL = 30          # seconds; short, because availability changes fast
LOCK_MS = 4000          # how long a borrow may hold the per-book lock


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=UI_HTML)


@app.get("/health")
def health():
    out = {"status": "ok", "postgres": False, "redis": False}
    try:
        db.query("SELECT 1")
        out["postgres"] = True
    except Exception as e:
        out["pg_error"] = str(e)
    try:
        cache.client().ping()
        out["redis"] = True
    except Exception as e:
        out["redis_error"] = str(e)
    return out if out["postgres"] and out["redis"] else JSONResponse(out, status_code=503)


def _lock(key, token, ms=LOCK_MS):
    """SET NX PX. Returns True if we now hold the lock."""
    return bool(cache.client().set(key, token, nx=True, px=ms))


def _unlock(key, token):
    """Only release a lock we still own - never delete somebody else's."""
    c = cache.client()
    if c.get(key) == token:
        c.delete(key)


def _available(book_id):
    hit = cache.get_json(f"avail:{book_id}")
    if hit is not None:
        return int(hit["available"]), True
    row = db.one("SELECT count(*) FILTER (WHERE status='available') AS n"
                 " FROM copies WHERE book_id=%s", (book_id,))
    n = int(row["n"]) if row else 0
    cache.set_json(f"avail:{book_id}", {"available": n}, ttl=AVAIL_TTL)
    return n, False


def _member_state(member_id):
    loans = db.query("SELECT id, copy_id, issued_on, due_on, returned_on, renewals"
                     " FROM loans WHERE member_id=%s ORDER BY id", (member_id,))
    fines = db.query("SELECT id, loan_id, amount, paid FROM fines WHERE member_id=%s",
                     (member_id,))
    fines = [{"id": f["id"], "loan_id": f["loan_id"],
              "amount": float(f["amount"]), "paid": f["paid"]} for f in fines]
    return loans, fines, member_summary(loans, fines, date.today())


@app.get("/books")
def books():
    return {"books": db.query(
        "SELECT b.id, b.title, b.author, b.reference_only,"
        " count(c.id) AS copies,"
        " count(c.id) FILTER (WHERE c.status='available') AS available"
        " FROM books b LEFT JOIN copies c ON c.book_id=b.id"
        " GROUP BY b.id ORDER BY b.id")}


@app.post("/books", status_code=201)
def create_book(payload: dict = Body(...)):
    title = payload.get("title")
    author = payload.get("author")
    copies_count = payload.get("copies_count", 1)
    reference_only = bool(payload.get("reference_only", False))

    if not title or not author:
        raise HTTPException(400, "title and author are required")
    try:
        copies_count = int(copies_count)
        if copies_count < 1 or copies_count > 50:
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(400, "copies_count must be an integer between 1 and 50")

    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO books (title, author, reference_only) VALUES (%s, %s, %s) RETURNING id",
            (str(title).strip(), str(author).strip(), reference_only),
        )
        book_id = cur.fetchone()["id"]
        for i in range(copies_count):
            barcode = f"LIB-{book_id:04d}-{i+1:02d}"
            cur.execute(
                "INSERT INTO copies (book_id, barcode, status) VALUES (%s, %s, 'available')",
                (book_id, barcode),
            )

    cache.drop(f"avail:{book_id}")
    return {
        "id": book_id,
        "title": str(title).strip(),
        "author": str(author).strip(),
        "reference_only": reference_only,
        "copies_created": copies_count,
    }


@app.get("/books/{book_id}")
def get_book(book_id: int):
    book = db.one("SELECT id, title, author, reference_only FROM books WHERE id=%s", (book_id,))
    if not book:
        raise HTTPException(404, "no such book")
    copies = db.query(
        "SELECT id, barcode, status FROM copies WHERE book_id=%s ORDER BY id", (book_id,)
    )
    n, cached = _available(book_id)
    return {
        "book": book,
        "copies": copies,
        "available_copies": n,
        "total_copies": len(copies),
        "cached": cached,
    }


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    book = db.one("SELECT id, title FROM books WHERE id=%s", (book_id,))
    if not book:
        raise HTTPException(404, "no such book")

    active_loans = db.one(
        "SELECT count(*) AS n FROM loans l JOIN copies c ON c.id=l.copy_id "
        "WHERE c.book_id=%s AND l.returned_on IS NULL",
        (book_id,),
    )
    if active_loans and int(active_loans["n"]) > 0:
        raise HTTPException(409, "book_has_active_loans")

    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM loans WHERE copy_id IN (SELECT id FROM copies WHERE book_id=%s)",
            (book_id,),
        )
        cur.execute("DELETE FROM copies WHERE book_id=%s", (book_id,))
        cur.execute("DELETE FROM books WHERE id=%s", (book_id,))

    cache.drop(f"avail:{book_id}")
    return {"status": "deleted", "book_id": book_id, "title": book["title"]}


@app.get("/books/{book_id}/availability")
def availability(book_id: int):
    book = db.one("SELECT id, title, reference_only FROM books WHERE id=%s", (book_id,))
    if not book:
        raise HTTPException(404, "no such book")
    n, cached = _available(book_id)
    return {"book_id": book_id, "title": book["title"], "available": n,
            "reference_only": book["reference_only"], "cached": cached}


@app.get("/members/{member_id}")
def member(member_id: int):
    row = db.one("SELECT id, name, email FROM members WHERE id=%s", (member_id,))
    if not row:
        raise HTTPException(404, "no such member")
    loans, fines, summary = _member_state(member_id)
    out = []
    for ln in loans:
        entry = dict(ln)
        if not ln["returned_on"]:
            entry["fine_if_returned_today"] = projected_fine(ln["due_on"], date.today())
        out.append(entry)
    return {"member": row, "loans": out, "fines": fines, "summary": summary}


@app.post("/borrow", status_code=201)
def borrow(payload: dict = Body(...)):
    """Hand out one copy. Two students racing for the last copy: exactly one wins."""
    try:
        member_id = int(payload.get("member_id"))
        book_id = int(payload.get("book_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "member_id and book_id are required integers")

    if not db.one("SELECT 1 FROM members WHERE id=%s", (member_id,)):
        raise HTTPException(404, "no such member")
    book = db.one("SELECT id, title, reference_only FROM books WHERE id=%s", (book_id,))
    if not book:
        raise HTTPException(404, "no such book")

    _, fines, summary = _member_state(member_id)
    free, _ = _available(book_id)
    ok, reason = can_borrow(summary["active_loans"], summary["unpaid_fines"], free,
                            reference_only=book["reference_only"],
                            has_overdue=summary["overdue_loans"] > 0)
    if not ok:
        raise HTTPException(409, reason)

    token = uuid4().hex
    key = f"lock:borrow:{book_id}"
    if not _lock(key, token):
        raise HTTPException(409, "another borrow for this book is in flight")
    try:
        # One connection, one transaction. The conditional UPDATE is what makes
        # this safe - the Redis lock above is only a politeness.
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE copies SET status='on_loan' WHERE id = ("
                "  SELECT id FROM copies WHERE book_id=%s AND status='available'"
                "  ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING id, barcode",
                (book_id,))
            copy = cur.fetchone()
            if not copy:
                raise HTTPException(409, "no_copies_available")
            issued = date.today()
            cur.execute(
                "INSERT INTO loans (copy_id, member_id, issued_on, due_on)"
                " VALUES (%s,%s,%s,%s) RETURNING id",
                (copy["id"], member_id, issued, due_date(issued, LOAN_DAYS)))
            loan_id = cur.fetchone()["id"]
    finally:
        cache.drop(f"avail:{book_id}")
        _unlock(key, token)

    return {"loan_id": loan_id, "member_id": member_id, "book": book["title"],
            "barcode": copy["barcode"], "issued_on": str(date.today()),
            "due_on": str(due_date(date.today(), LOAN_DAYS))}


@app.post("/return")
def give_back(payload: dict = Body(...)):
    try:
        loan_id = int(payload.get("loan_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "loan_id is required")
    loan = db.one("SELECT l.id, l.copy_id, l.member_id, l.due_on, l.returned_on,"
                  " c.book_id FROM loans l JOIN copies c ON c.id=l.copy_id"
                  " WHERE l.id=%s", (loan_id,))
    if not loan:
        raise HTTPException(404, "no such loan")
    if loan["returned_on"]:
        raise HTTPException(409, "that loan was already returned")

    today = date.today()
    charge = fine_for(loan["due_on"], today)
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute("UPDATE loans SET returned_on=%s WHERE id=%s AND returned_on IS NULL",
                    (today, loan_id))
        if cur.rowcount != 1:
            raise HTTPException(409, "that loan was already returned")
        cur.execute("UPDATE copies SET status='available' WHERE id=%s", (loan["copy_id"],))
        if charge["amount"] > 0:
            cur.execute("INSERT INTO fines (loan_id, member_id, amount) VALUES (%s,%s,%s)",
                        (loan_id, loan["member_id"], charge["amount"]))
    cache.drop(f"avail:{loan['book_id']}")
    return {"loan_id": loan_id, "returned_on": str(today), "fine": charge}


@app.post("/loans/{loan_id}/renew")
def renew(loan_id: int):
    loan = db.one("SELECT id, member_id, due_on, returned_on, renewals"
                  " FROM loans WHERE id=%s", (loan_id,))
    if not loan:
        raise HTTPException(404, "no such loan")
    if loan["returned_on"]:
        raise HTTPException(409, "that loan is closed")
    _, fines, summary = _member_state(loan["member_id"])
    ok, reason = can_renew(loan["renewals"], loan["due_on"], date.today(),
                           unpaid_total=summary["unpaid_fines"])
    if not ok:
        raise HTTPException(409, reason)
    new_due = renewed_due_date(loan["due_on"], date.today())
    db.query("UPDATE loans SET due_on=%s, renewals=renewals+1 WHERE id=%s",
             (new_due, loan_id), fetch=False)
    return {"loan_id": loan_id, "due_on": str(new_due), "renewals": loan["renewals"] + 1}


@app.post("/members/{member_id}/fines/pay")
def pay(member_id: int):
    if not db.one("SELECT 1 FROM members WHERE id=%s", (member_id,)):
        raise HTTPException(404, "no such member")
    rows = db.query("UPDATE fines SET paid=TRUE, paid_at=now()"
                    " WHERE member_id=%s AND NOT paid RETURNING id, amount", (member_id,))
    if not rows:
        raise HTTPException(409, "nothing to pay")
    return {"member_id": member_id, "cleared": len(rows),
            "paid": round(sum(float(r["amount"]) for r in rows), 2)}
