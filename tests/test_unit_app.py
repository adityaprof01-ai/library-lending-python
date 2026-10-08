"""Unit tests for app/main.py, app/db.py, and app/cache.py with mocked DB and Redis.

Tests HTTP routing, error handling, status codes, and helper functions
without requiring external network or live database infrastructure.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import (
    app,
    _lock,
    _unlock,
    _available,
    _member_state,
)
from app import db, cache


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_success(self, client):
        with patch.object(db, "query", return_value=[{"?column?": 1}]), \
             patch.object(cache, "client") as mock_cache:
            mock_cache.return_value.ping.return_value = True
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["postgres"] is True
            assert data["redis"] is True

    def test_health_postgres_failure(self, client):
        with patch.object(db, "query", side_effect=Exception("DB connection failed")), \
             patch.object(cache, "client") as mock_cache:
            mock_cache.return_value.ping.return_value = True
            resp = client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["postgres"] is False
            assert "pg_error" in data

    def test_health_redis_failure(self, client):
        with patch.object(db, "query", return_value=[{"?column?": 1}]), \
             patch.object(cache, "client") as mock_cache:
            mock_cache.return_value.ping.side_effect = Exception("Redis unreachable")
            resp = client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["redis"] is False
            assert "redis_error" in data


class TestLockingAndAvailability:
    def test_lock_and_unlock(self):
        with patch.object(cache, "client") as mock_cache:
            mock_redis = MagicMock()
            mock_cache.return_value = mock_redis

            mock_redis.set.return_value = True
            assert _lock("lock:key", "token123") is True

            mock_redis.set.return_value = None
            assert _lock("lock:key", "token123") is False

            # Unlock when token matches
            mock_redis.get.return_value = "token123"
            _unlock("lock:key", "token123")
            mock_redis.delete.assert_called_with("lock:key")

            # Unlock when token does not match (lock lost/expired)
            mock_redis.get.return_value = "different_token"
            mock_redis.delete.reset_mock()
            _unlock("lock:key", "token123")
            mock_redis.delete.assert_not_called()

    def test_available_cache_hit(self):
        with patch.object(cache, "get_json", return_value={"available": 3}):
            count, hit = _available(1)
            assert count == 3
            assert hit is True

    def test_available_cache_miss(self):
        with patch.object(cache, "get_json", return_value=None), \
             patch.object(db, "one", return_value={"n": 2}), \
             patch.object(cache, "set_json") as mock_set:
            count, hit = _available(1)
            assert count == 2
            assert hit is False
            mock_set.assert_called_once_with("avail:1", {"available": 2}, ttl=30)

    def test_member_state_direct(self):
        with patch.object(db, "query", side_effect=[
            [{"id": 1, "copy_id": 2, "issued_on": date.today(), "due_on": date.today(), "returned_on": None, "renewals": 0}],
            [{"id": 1, "loan_id": 1, "amount": 15.0, "paid": False}]
        ]):
            loans, fines, summary = _member_state(1)
            assert len(loans) == 1
            assert len(fines) == 1
            assert summary["active_loans"] == 1
            assert summary["unpaid_fines"] == 15.0



class TestBooksAndMembersRoutes:
    def test_get_books(self, client):
        fake_books = [{"id": 1, "title": "Book 1", "copies": 2, "available": 2}]
        with patch.object(db, "query", return_value=fake_books):
            resp = client.get("/books")
            assert resp.status_code == 200
            assert resp.json() == {"books": fake_books}

    def test_book_availability_not_found(self, client):
        with patch.object(db, "one", return_value=None):
            resp = client.get("/books/999/availability")
            assert resp.status_code == 404

    def test_book_availability_success(self, client):
        with patch.object(db, "one", return_value={"id": 1, "title": "Book 1", "reference_only": False}), \
             patch("app.main._available", return_value=(2, True)):
            resp = client.get("/books/1/availability")
            assert resp.status_code == 200
            data = resp.json()
            assert data["available"] == 2
            assert data["cached"] is True

    def test_get_member_not_found(self, client):
        with patch.object(db, "one", return_value=None):
            resp = client.get("/members/999")
            assert resp.status_code == 404

    def test_get_member_success(self, client):
        member_row = {"id": 1, "name": "Alice", "email": "alice@test.edu"}
        loans = [
            {"id": 10, "copy_id": 1, "issued_on": date.today() - timedelta(days=20),
             "due_on": date.today() - timedelta(days=6), "returned_on": None, "renewals": 0}
        ]
        fines = [{"id": 1, "loan_id": 10, "amount": 10.0, "paid": False}]
        with patch.object(db, "one", return_value=member_row), \
             patch("app.main._member_state", return_value=(loans, fines, {"active_loans": 1, "unpaid_fines": 10.0})):
            resp = client.get("/members/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["member"]["name"] == "Alice"
            assert "fine_if_returned_today" in data["loans"][0]


class TestBorrowRoute:
    def test_borrow_invalid_payload(self, client):
        resp = client.post("/borrow", json={"member_id": "not-an-int"})
        assert resp.status_code == 400

    def test_borrow_member_not_found(self, client):
        with patch.object(db, "one", return_value=None):
            resp = client.post("/borrow", json={"member_id": 999, "book_id": 1})
            assert resp.status_code == 404
            assert "member" in resp.json()["detail"]

    def test_borrow_book_not_found(self, client):
        with patch.object(db, "one", side_effect=[{"id": 1}, None]):
            resp = client.post("/borrow", json={"member_id": 1, "book_id": 999})
            assert resp.status_code == 404
            assert "book" in resp.json()["detail"]

    def test_borrow_ineligible_member(self, client):
        with patch.object(db, "one", side_effect=[
            {"id": 1},
            {"id": 1, "title": "Book 1", "reference_only": True}
        ]), patch("app.main._member_state", return_value=([], [], {"active_loans": 0, "unpaid_fines": 0.0, "overdue_loans": 0})), \
           patch("app.main._available", return_value=(1, False)):
            resp = client.post("/borrow", json={"member_id": 1, "book_id": 1})
            assert resp.status_code == 409
            assert resp.json()["detail"] == "reference_only"

    def test_borrow_lock_contention(self, client):
        with patch.object(db, "one", side_effect=[
            {"id": 1},
            {"id": 1, "title": "Book 1", "reference_only": False}
        ]), patch("app.main._member_state", return_value=([], [], {"active_loans": 0, "unpaid_fines": 0.0, "overdue_loans": 0})), \
           patch("app.main._available", return_value=(1, False)), \
           patch("app.main._lock", return_value=False):
            resp = client.post("/borrow", json={"member_id": 1, "book_id": 1})
            assert resp.status_code == 409
            assert "flight" in resp.json()["detail"]

    def test_borrow_no_copies_available_in_db(self, client):
        with patch.object(db, "one", side_effect=[
            {"id": 1},
            {"id": 1, "title": "Algorithms", "reference_only": False}
        ]), patch("app.main._member_state", return_value=([], [], {"active_loans": 0, "unpaid_fines": 0.0, "overdue_loans": 0})), \
           patch("app.main._available", return_value=(1, False)), \
           patch("app.main._lock", return_value=True), \
           patch("app.main._unlock"), \
           patch.object(cache, "drop"), \
           patch.object(db, "connect") as mock_connect:

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchone.return_value = None  # No copy returned from UPDATE SKIP LOCKED

            resp = client.post("/borrow", json={"member_id": 1, "book_id": 1})
            assert resp.status_code == 409
            assert resp.json()["detail"] == "no_copies_available"

    def test_borrow_successful_flow(self, client):
        with patch.object(db, "one", side_effect=[
            {"id": 1},
            {"id": 1, "title": "Algorithms", "reference_only": False}
        ]), patch("app.main._member_state", return_value=([], [], {"active_loans": 0, "unpaid_fines": 0.0, "overdue_loans": 0})), \
           patch("app.main._available", return_value=(1, False)), \
           patch("app.main._lock", return_value=True), \
           patch("app.main._unlock"), \
           patch.object(cache, "drop"), \
           patch.object(db, "connect") as mock_connect:

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_cur.fetchone.side_effect = [
                {"id": 10, "barcode": "LIB-0010"},
                {"id": 42}
            ]

            resp = client.post("/borrow", json={"member_id": 1, "book_id": 1})
            assert resp.status_code == 201
            assert resp.json()["loan_id"] == 42
            assert resp.json()["barcode"] == "LIB-0010"


class TestReturnAndRenewRoutes:
    def test_return_invalid_payload(self, client):
        resp = client.post("/return", json={})
        assert resp.status_code == 400

    def test_return_loan_not_found(self, client):
        with patch.object(db, "one", return_value=None):
            resp = client.post("/return", json={"loan_id": 999})
            assert resp.status_code == 404

    def test_return_already_returned(self, client):
        with patch.object(db, "one", return_value={"id": 1, "returned_on": date.today()}):
            resp = client.post("/return", json={"loan_id": 1})
            assert resp.status_code == 409

    def test_return_success_with_fine(self, client):
        loan = {
            "id": 1, "copy_id": 5, "member_id": 2, "book_id": 3,
            "due_on": date.today() - timedelta(days=10), "returned_on": None
        }
        with patch.object(db, "one", return_value=loan), \
             patch.object(db, "connect") as mock_connect, \
             patch.object(cache, "drop"):
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.rowcount = 1
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            resp = client.post("/return", json={"loan_id": 1})
            assert resp.status_code == 200
            data = resp.json()
            assert data["loan_id"] == 1
            assert data["fine"]["amount"] > 0

    def test_return_concurrent_rowcount_zero(self, client):
        loan = {
            "id": 1, "copy_id": 5, "member_id": 2, "book_id": 3,
            "due_on": date.today() - timedelta(days=10), "returned_on": None
        }
        with patch.object(db, "one", return_value=loan), \
             patch.object(db, "connect") as mock_connect, \
             patch.object(cache, "drop"):
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.rowcount = 0  # another worker already updated returned_on
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            resp = client.post("/return", json={"loan_id": 1})
            assert resp.status_code == 409

    def test_renew_loan_not_found(self, client):
        with patch.object(db, "one", return_value=None):
            resp = client.post("/loans/999/renew")
            assert resp.status_code == 404

    def test_renew_loan_closed(self, client):
        with patch.object(db, "one", return_value={"id": 1, "returned_on": date.today()}):
            resp = client.post("/loans/1/renew")
            assert resp.status_code == 409

    def test_renew_rejected_by_policy(self, client):
        loan = {
            "id": 1, "member_id": 2, "due_on": date.today() + timedelta(days=5),
            "returned_on": None, "renewals": 2
        }
        with patch.object(db, "one", return_value=loan), \
             patch("app.main._member_state", return_value=([], [], {"unpaid_fines": 0.0})):
            resp = client.post("/loans/1/renew")
            assert resp.status_code == 409
            assert resp.json()["detail"] == "renewal_limit_reached"

    def test_renew_loan_success(self, client):
        loan = {
            "id": 1, "member_id": 2, "due_on": date.today() + timedelta(days=5),
            "returned_on": None, "renewals": 0
        }
        with patch.object(db, "one", return_value=loan), \
             patch("app.main._member_state", return_value=([], [], {"unpaid_fines": 0.0})), \
             patch.object(db, "query"):
            resp = client.post("/loans/1/renew")
            assert resp.status_code == 200
            assert resp.json()["renewals"] == 1


class TestPayRoute:
    def test_pay_member_not_found(self, client):
        with patch.object(db, "one", return_value=None):
            resp = client.post("/members/999/fines/pay")
            assert resp.status_code == 404

    def test_pay_nothing_to_pay(self, client):
        with patch.object(db, "one", return_value={"id": 1}), \
             patch.object(db, "query", return_value=[]):
            resp = client.post("/members/1/fines/pay")
            assert resp.status_code == 409

    def test_pay_success(self, client):
        with patch.object(db, "one", return_value={"id": 1}), \
             patch.object(db, "query", return_value=[{"id": 1, "amount": 25.0}]):
            resp = client.post("/members/1/fines/pay")
            assert resp.status_code == 200
            data = resp.json()
            assert data["cleared"] == 1
            assert data["paid"] == 25.0


class TestDbAndCacheHelpers:
    def test_db_url_and_query_fetch_none(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test:test@localhost/test"}):
            assert db.url() == "postgresql://test:test@localhost/test"

        with patch.object(db, "connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.description = None
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            assert db.query("UPDATE foo SET bar=1", fetch=False) == []
            assert db.one("UPDATE foo SET bar=1") is None

    def test_cache_helpers(self):
        with patch.object(cache, "client") as mock_cache:
            mock_redis = MagicMock()
            mock_cache.return_value = mock_redis

            cache.set_json("mykey", {"a": 1})
            mock_redis.set.assert_called_once()

            mock_redis.get.return_value = '{"a": 1}'
            assert cache.get_json("mykey") == {"a": 1}

            mock_redis.get.return_value = None
            assert cache.get_json("missing") is None

            cache.drop("k1", "k2")
            mock_redis.delete.assert_called_with("k1", "k2")

            cache.drop()  # No-op when no keys

            mock_redis.scan_iter.return_value = ["pre:1", "pre:2"]
            cache.drop_prefix("pre:")
            assert mock_redis.delete.call_count >= 2
