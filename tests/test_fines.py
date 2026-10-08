"""Unit tests for app/fines.py.

No database and no network. Pure logic testing.
"""
import datetime
import pytest

from app.fines import (
    DAILY_RATE,
    FINE_BLOCK_AT,
    GRACE_DAYS,
    LOAN_DAYS,
    MAX_ACTIVE_LOANS,
    MAX_FINE,
    MAX_RENEWALS,
    RENEWAL_DAYS,
    LoanError,
    as_date,
    calendar_days_late,
    can_borrow,
    can_renew,
    chargeable_days,
    due_date,
    fine_for,
    is_free_day,
    member_summary,
    outstanding,
    overdue,
    projected_fine,
    renewed_due_date,
)


class TestAsDate:
    def test_as_date_from_datetime(self):
        dt = datetime.datetime(2026, 4, 15, 14, 30, 0)
        assert as_date(dt) == datetime.date(2026, 4, 15)

    def test_as_date_from_date(self):
        d = datetime.date(2026, 4, 15)
        assert as_date(d) == d

    def test_as_date_from_iso_string(self):
        assert as_date("2026-04-15") == datetime.date(2026, 4, 15)
        assert as_date("2026-04-15T10:00:00") == datetime.date(2026, 4, 15)
        assert as_date("  2026-04-15 12:00:00  ") == datetime.date(2026, 4, 15)

    def test_as_date_invalid_string(self):
        with pytest.raises(LoanError, match="not a date"):
            as_date("not-a-date")

    def test_as_date_invalid_type(self):
        with pytest.raises(LoanError, match="not a date"):
            as_date(12345)
        with pytest.raises(LoanError, match="not a date"):
            as_date(None)


class TestIsFreeDay:
    def test_weekdays_are_not_free(self):
        # 2026-05-01 is Friday
        friday = datetime.date(2026, 5, 1)
        assert is_free_day(friday) is False
        # 2026-05-04 is Monday
        monday = datetime.date(2026, 5, 4)
        assert is_free_day(monday) is False

    def test_weekends_are_free(self):
        # 2026-05-02 is Saturday, 2026-05-03 is Sunday
        saturday = datetime.date(2026, 5, 2)
        sunday = datetime.date(2026, 5, 3)
        assert is_free_day(saturday) is True
        assert is_free_day(sunday) is True


class TestDueDate:
    def test_default_loan_days(self):
        issued = datetime.date(2026, 5, 1)
        expected = issued + datetime.timedelta(days=LOAN_DAYS)
        assert due_date(issued) == expected

    def test_custom_loan_days(self):
        issued = "2026-05-01"
        assert due_date(issued, days=7) == datetime.date(2026, 5, 8)

    def test_non_positive_days_raises_loan_error(self):
        with pytest.raises(LoanError, match="must be at least one day long"):
            due_date("2026-05-01", days=0)
        with pytest.raises(LoanError, match="must be at least one day long"):
            due_date("2026-05-01", days=-5)


class TestCalendarDaysLate:
    def test_returned_on_or_before_due_date(self):
        assert calendar_days_late("2026-05-10", "2026-05-05") == 0
        assert calendar_days_late("2026-05-10", "2026-05-10") == 0

    def test_returned_after_due_date(self):
        assert calendar_days_late("2026-05-10", "2026-05-14") == 4


class TestChargeableDays:
    def test_negative_grace_raises_loan_error(self):
        with pytest.raises(LoanError, match="grace period cannot be negative"):
            chargeable_days("2026-05-01", "2026-05-05", grace=-1)

    def test_returned_on_due_date_owes_nothing(self):
        assert chargeable_days("2026-05-01", "2026-05-01") == 0

    def test_returned_inside_grace_period_owes_nothing(self):
        # Due on Monday May 4, returned Wednesday May 6 (2 days late, within 2-day grace)
        assert chargeable_days("2026-05-04", "2026-05-06", grace=2) == 0

    def test_friday_due_returned_following_tuesday_with_grace(self):
        """Pick a Friday, return the book the following Tuesday.

        Due: Friday 2026-05-01.
        Returned: Tuesday 2026-05-05 (4 calendar days late).
        Grace: 2 days (eats Saturday 05-02 and Sunday 05-03).
        Remaining days: Monday 05-04 (chargeable) and Tuesday 05-05 (chargeable).
        Chargeable days = 2.
        """
        friday = "2026-05-01"
        tuesday = "2026-05-05"
        assert chargeable_days(friday, tuesday, grace=2, skip_weekends=True) == 2

    def test_chargeable_days_without_skip_weekends(self):
        """When skip_weekends=False, Saturday and Sunday count if they fall after grace."""
        # Due Wednesday 2026-04-29, returned Monday 2026-05-04 (5 days late).
        # Grace = 1 day (Thursday 2026-04-30 consumed).
        # Remaining: Friday, Saturday, Sunday, Monday = 4 days without skip_weekends.
        wednesday = "2026-04-29"
        monday = "2026-05-04"
        assert chargeable_days(wednesday, monday, grace=1, skip_weekends=False) == 4
        # With skip_weekends=True, Sat & Sun excluded -> 2 days (Fri, Mon).
        assert chargeable_days(wednesday, monday, grace=1, skip_weekends=True) == 2


class TestFineFor:
    def test_default_constants(self):
        assert DAILY_RATE == 5.0
        assert GRACE_DAYS == 2
        assert MAX_FINE == 200.0

    def test_negative_rate_raises_error(self):
        with pytest.raises(LoanError, match="rate cannot be negative"):
            fine_for("2026-05-01", "2026-05-05", rate=-2.0)

    def test_no_fine_within_grace(self):
        result = fine_for("2026-05-01", "2026-05-02")
        assert result["days_late"] == 1
        assert result["chargeable_days"] == 0
        assert result["uncapped"] == 0.0
        assert result["amount"] == 0.0
        assert result["capped"] is False

    def test_fine_calculation_standard(self):
        # Friday to Tuesday = 2 chargeable days * 5.0 = 10.0
        result = fine_for("2026-05-01", "2026-05-05", rate=5.0, grace=2)
        assert result["days_late"] == 4
        assert result["chargeable_days"] == 2
        assert result["uncapped"] == 10.0
        assert result["amount"] == 10.0
        assert result["capped"] is False

    def test_fine_capped_at_max_fine(self):
        # 100 chargeable days * 5.0 = 500.0, cap is 200.0
        # Returned far in the future
        result = fine_for("2026-01-01", "2026-06-01", rate=5.0, cap=200.0)
        assert result["uncapped"] > 200.0
        assert result["amount"] == 200.0
        assert result["capped"] is True


class TestOutstandingAndOverdue:
    def test_outstanding_fines_sum(self):
        fines = [
            {"amount": "25.50", "paid": False},
            {"amount": 50.00, "paid": False},
            {"amount": 30.00, "paid": True},
        ]
        assert outstanding(fines) == 75.50
        assert outstanding([]) == 0.0

    def test_overdue_loans_detection(self):
        today = datetime.date(2026, 5, 10)
        loans = [
            {"id": 1, "due_on": "2026-05-01", "returned_on": None},               # overdue
            {"id": 2, "due_on": "2026-05-01", "returned_on": "2026-05-05"},       # returned (not open)
            {"id": 3, "due_on": "2026-05-15", "returned_on": None},               # not overdue
            {"id": 4, "due_on": "2026-05-10", "returned_on": None},               # due today (not overdue yet)
        ]
        result = overdue(loans, today)
        assert len(result) == 1
        assert result[0]["id"] == 1


class TestCanBorrow:
    def test_reference_only_rejected(self):
        allowed, reason = can_borrow(active_loans=0, unpaid_total=0.0, copies_available=1, reference_only=True)
        assert allowed is False
        assert reason == "reference_only"

    def test_no_copies_available_rejected(self):
        allowed, reason = can_borrow(active_loans=0, unpaid_total=0.0, copies_available=0)
        assert allowed is False
        assert reason == "no_copies_available"

    def test_loan_limit_reached_rejected(self):
        allowed, reason = can_borrow(active_loans=MAX_ACTIVE_LOANS, unpaid_total=0.0, copies_available=1)
        assert allowed is False
        assert reason == "loan_limit_reached"

    def test_unpaid_fines_rejected(self):
        allowed, reason = can_borrow(active_loans=1, unpaid_total=FINE_BLOCK_AT, copies_available=1)
        assert allowed is False
        assert reason == "unpaid_fines"

    def test_overdue_book_held_rejected(self):
        allowed, reason = can_borrow(active_loans=1, unpaid_total=0.0, copies_available=1, has_overdue=True)
        assert allowed is False
        assert reason == "overdue_book_held"

    def test_can_borrow_ok(self):
        allowed, reason = can_borrow(active_loans=2, unpaid_total=25.0, copies_available=2)
        assert allowed is True
        assert reason == "ok"


class TestCanRenew:
    def test_reserved_by_others_rejected(self):
        allowed, reason = can_renew(times_renewed=0, due_on="2026-05-20", today="2026-05-10", reserved_by_others=True)
        assert allowed is False
        assert reason == "reserved_by_someone_else"

    def test_renewal_limit_reached_rejected(self):
        allowed, reason = can_renew(times_renewed=MAX_RENEWALS, due_on="2026-05-20", today="2026-05-10")
        assert allowed is False
        assert reason == "renewal_limit_reached"

    def test_unpaid_fines_rejected(self):
        allowed, reason = can_renew(times_renewed=0, due_on="2026-05-20", today="2026-05-10", unpaid_total=FINE_BLOCK_AT)
        assert allowed is False
        assert reason == "unpaid_fines"

    def test_already_overdue_rejected(self):
        allowed, reason = can_renew(times_renewed=0, due_on="2026-05-05", today="2026-05-10")
        assert allowed is False
        assert reason == "already_overdue"

    def test_can_renew_ok(self):
        allowed, reason = can_renew(times_renewed=1, due_on="2026-05-15", today="2026-05-10", unpaid_total=50.0)
        assert allowed is True
        assert reason == "ok"


class TestRenewedDueDate:
    def test_renewed_when_due_date_still_ahead(self):
        # Extending from due_on
        due_on = "2026-05-15"
        today = "2026-05-10"
        expected = datetime.date(2026, 5, 15) + datetime.timedelta(days=RENEWAL_DAYS)
        assert renewed_due_date(due_on, today) == expected

    def test_renewed_when_today_is_after_due_date(self):
        due_on = "2026-05-08"
        today = "2026-05-10"
        expected = datetime.date(2026, 5, 10) + datetime.timedelta(days=RENEWAL_DAYS)
        assert renewed_due_date(due_on, today) == expected


class TestMemberSummary:
    def test_member_summary_calculation(self):
        today = datetime.date(2026, 5, 10)
        loans = [
            {"id": 1, "due_on": "2026-05-01", "returned_on": None},
            {"id": 2, "due_on": "2026-05-15", "returned_on": None},
            {"id": 3, "due_on": "2026-04-20", "returned_on": "2026-04-25"},
        ]
        fines = [
            {"amount": 30.0, "paid": False},
            {"amount": 20.0, "paid": True},
        ]
        summary = member_summary(loans, fines, today)
        assert summary["active_loans"] == 2
        assert summary["overdue_loans"] == 1
        assert summary["slots_left"] == MAX_ACTIVE_LOANS - 2
        assert summary["unpaid_fines"] == 30.0
        assert summary["blocked"] is True  # blocked because overdue_loans > 0

    def test_member_blocked_by_fines(self):
        today = datetime.date(2026, 5, 10)
        loans = [{"id": 1, "due_on": "2026-05-20", "returned_on": None}]
        fines = [{"amount": 100.0, "paid": False}]
        summary = member_summary(loans, fines, today)
        assert summary["blocked"] is True

    def test_member_slots_left_bounded_at_zero(self):
        today = datetime.date(2026, 5, 10)
        loans = [{"id": i, "due_on": "2026-05-20", "returned_on": None} for i in range(6)]
        summary = member_summary(loans, [], today, max_loans=4)
        assert summary["slots_left"] == 0


class TestProjectedFine:
    def test_projected_fine_before_or_on_due_date(self):
        res = projected_fine("2026-05-10", "2026-05-10")
        assert res["amount"] == 0.0
        assert res["days_late"] == 0
        assert res["chargeable_days"] == 0

        res_early = projected_fine("2026-05-10", "2026-05-05")
        assert res_early["amount"] == 0.0

    def test_projected_fine_past_due_date(self):
        res = projected_fine("2026-05-01", "2026-05-05")
        assert res["chargeable_days"] == 2
        assert res["amount"] == 10.0
