"""Pure library fine and borrowing rules. No database, no HTTP.

Every function takes the dates it needs as arguments - nothing here reads the
clock - so each rule can be tested with a fixed calendar.

What is worth testing
---------------------
  * a book returned on or before its due date owes nothing
  * a book inside the grace period owes nothing; the first chargeable day is
    GRACE_DAYS + 1
  * weekends are free. Due Friday, returned the following Tuesday with a
    two-day grace charges two days, not four: the grace eats Saturday and
    Sunday, leaving Monday and Tuesday
  * the fine stops at MAX_FINE however late the book is, and `capped` says so
  * `chargeable_days` with skip_weekends=False charges every day, so the
    weekend rule is visible in a test rather than implied
  * a member already holding MAX_ACTIVE_LOANS books cannot borrow
  * a member owing FINE_BLOCK_AT or more cannot borrow, even with slots free
  * a reference-only title can never be borrowed, whatever the member owes
  * the reasons come back as stable strings, so an API can map them to codes
  * renewals: allowed twice, never when somebody else is waiting, never once
    the book is already overdue
  * `calendar_days_late` must not go negative for an early return
"""
import datetime

GRACE_DAYS = 2          # forgiven before anything is charged
DAILY_RATE = 5.0        # rupees per chargeable day
MAX_FINE = 200.0        # one book can never cost more than this
SKIP_WEEKENDS = True    # the library is shut, so it does not charge
MAX_ACTIVE_LOANS = 4
FINE_BLOCK_AT = 100.0   # owing this much stops you borrowing anything
LOAN_DAYS = 14
RENEWAL_DAYS = 7
MAX_RENEWALS = 2


class LoanError(ValueError):
    pass


def as_date(value):
    """Accept a date, a datetime or an ISO string. Reject everything else."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip()[:10])
        except ValueError:
            raise LoanError(f"{value!r} is not a date")
    raise LoanError(f"{value!r} is not a date")


def is_free_day(day):
    """Saturday and Sunday. The library is closed, so no fine accrues."""
    return as_date(day).weekday() >= 5


def due_date(issued_on, days=LOAN_DAYS):
    if days <= 0:
        raise LoanError("a loan must be at least one day long")
    return as_date(issued_on) + datetime.timedelta(days=days)


def calendar_days_late(due_on, returned_on):
    """Whole days between the due date and the return. Never negative."""
    delta = (as_date(returned_on) - as_date(due_on)).days
    return delta if delta > 0 else 0


def chargeable_days(due_on, returned_on, grace=GRACE_DAYS,
                    skip_weekends=SKIP_WEEKENDS):
    """Count the days that actually cost money.

    The grace period is consumed first, from the day after the due date.
    Whatever is left is charged, minus weekends when skip_weekends is on.
    """
    if grace < 0:
        raise LoanError("the grace period cannot be negative")
    due_on = as_date(due_on)
    returned_on = as_date(returned_on)
    if calendar_days_late(due_on, returned_on) <= grace:
        return 0
    day = due_on + datetime.timedelta(days=grace + 1)
    count = 0
    while day <= returned_on:
        if not (skip_weekends and is_free_day(day)):
            count += 1
        day += datetime.timedelta(days=1)
    return count


def fine_for(due_on, returned_on, rate=DAILY_RATE, grace=GRACE_DAYS,
             cap=MAX_FINE, skip_weekends=SKIP_WEEKENDS):
    """The whole fine decision for one loan, as plain data."""
    if rate < 0:
        raise LoanError("the daily rate cannot be negative")
    billed = chargeable_days(due_on, returned_on, grace, skip_weekends)
    uncapped = round(billed * rate, 2)
    return {
        "days_late": calendar_days_late(due_on, returned_on),
        "chargeable_days": billed,
        "uncapped": uncapped,
        "amount": round(min(uncapped, cap), 2),
        "capped": uncapped > cap,
    }


def outstanding(fines):
    """Sum the unpaid rows of [{"amount": .., "paid": bool}, ...]."""
    return round(sum(float(f["amount"]) for f in fines if not f.get("paid")), 2)


def overdue(loans, today):
    """The still-open loans whose due date has passed."""
    today = as_date(today)
    return [ln for ln in loans
            if not ln.get("returned_on") and as_date(ln["due_on"]) < today]


def can_borrow(active_loans, unpaid_total, copies_available,
               reference_only=False, has_overdue=False,
               max_loans=MAX_ACTIVE_LOANS, block_at=FINE_BLOCK_AT):
    """May this member take this book out right now?

    Returns (allowed, reason). The reason is a stable string even when the
    answer is yes, so a caller never has to compare against None.
    """
    if reference_only:
        return False, "reference_only"
    if copies_available <= 0:
        return False, "no_copies_available"
    if active_loans >= max_loans:
        return False, "loan_limit_reached"
    if unpaid_total >= block_at:
        return False, "unpaid_fines"
    if has_overdue:
        return False, "overdue_book_held"
    return True, "ok"


def can_renew(times_renewed, due_on, today, reserved_by_others=False,
              unpaid_total=0.0, max_renewals=MAX_RENEWALS,
              block_at=FINE_BLOCK_AT):
    """Renewals are a courtesy, not a right."""
    if reserved_by_others:
        return False, "reserved_by_someone_else"
    if times_renewed >= max_renewals:
        return False, "renewal_limit_reached"
    if unpaid_total >= block_at:
        return False, "unpaid_fines"
    if as_date(due_on) < as_date(today):
        return False, "already_overdue"
    return True, "ok"


def renewed_due_date(due_on, today, days=RENEWAL_DAYS):
    """Extend from today, or from the due date if it is still ahead, so a
    member cannot bank unused days by renewing early."""
    base = max(as_date(due_on), as_date(today))
    return base + datetime.timedelta(days=days)


def member_summary(loans, fines, today, max_loans=MAX_ACTIVE_LOANS):
    """Fold a member's loans and fines into the numbers the rules need."""
    open_loans = [ln for ln in loans if not ln.get("returned_on")]
    late = overdue(open_loans, today)
    owed = outstanding(fines)
    return {
        "active_loans": len(open_loans),
        "overdue_loans": len(late),
        "slots_left": max(0, max_loans - len(open_loans)),
        "unpaid_fines": owed,
        "blocked": owed >= FINE_BLOCK_AT or len(late) > 0,
    }


def projected_fine(due_on, today, **kw):
    """What a book costs if it came back today. Used to show a running total
    on a loan that is still out."""
    if as_date(today) <= as_date(due_on):
        return {"days_late": 0, "chargeable_days": 0, "uncapped": 0.0,
                "amount": 0.0, "capped": False}
    return fine_for(due_on, today, **kw)
