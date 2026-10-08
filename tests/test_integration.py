"""Integration tests against live Postgres and Redis.

Tests verify actual HTTP endpoints, database state, cache interactions,
and concurrency safety.
"""
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import cache, db


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestIntegrationEndpoints:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["postgres"] is True
        assert data["redis"] is True

    def test_get_books(self, client):
        resp = client.get("/books")
        assert resp.status_code == 200
        books = resp.json().get("books", [])
        assert len(books) >= 6
        # Book 1 has copies
        book1 = next(b for b in books if b["id"] == 1)
        assert book1["title"] == "Designing Data-Intensive Applications"
        assert book1["copies"] == 3

    def test_books_availability_caching(self, client):
        # Clear any existing cache for book 2
        cache.drop("avail:2")

        # 1st call: Cache miss
        resp1 = client.get("/books/2/availability")
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["book_id"] == 2
        assert data1["cached"] is False

        # 2nd call: Cache hit
        resp2 = client.get("/books/2/availability")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["book_id"] == 2
        assert data2["cached"] is True
        assert data2["available"] == data1["available"]

    def test_get_member_summary(self, client):
        resp = client.get("/members/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["member"]["name"] == "Vikram Rao"
        # Vikram Rao has 4 active loans in seed
        assert data["summary"]["active_loans"] == 4
        assert data["summary"]["slots_left"] == 0

    def test_borrowing_constraints(self, client):
        # 1. Reference-only title (Book 6)
        resp_ref = client.post("/borrow", json={"member_id": 1, "book_id": 6})
        assert resp_ref.status_code == 409
        assert resp_ref.json()["detail"] == "reference_only"

        # 2. Member reached active loan limit (Member 2 has 4 loans)
        resp_limit = client.post("/borrow", json={"member_id": 2, "book_id": 4})
        assert resp_limit.status_code == 409
        assert resp_limit.json()["detail"] == "loan_limit_reached"

        # 3. Member holds an overdue book (Member 3 has 3-week overdue loan)
        resp_overdue = client.post("/borrow", json={"member_id": 3, "book_id": 4})
        assert resp_overdue.status_code == 409
        assert resp_overdue.json()["detail"] == "overdue_book_held"

        # 4. Member has unpaid fines >= 100 (Member 4 owes 115)
        resp_fines = client.post("/borrow", json={"member_id": 4, "book_id": 4})
        assert resp_fines.status_code == 409
        assert resp_fines.json()["detail"] == "unpaid_fines"

    def test_concurrency_last_copy_race(self, client):
        """Book 3 has only ONE copy (LIB-0006).

        Simulate two concurrent borrowers attempting to take the last copy.
        Exactly one must succeed (201), and the loser must be rejected with 409.
        """
        # Ensure book 3 copy is available before test
        db.query("UPDATE copies SET status='available' WHERE book_id=3", fetch=False)
        cache.drop("avail:3", "lock:borrow:3")

        def attempt_borrow(member_id):
            return client.post("/borrow", json={"member_id": member_id, "book_id": 3})

        with ThreadPoolExecutor(max_workers=2) as executor:
            # Member 1 and Member 5 are eligible to borrow
            f1 = executor.submit(attempt_borrow, 1)
            f2 = executor.submit(attempt_borrow, 5)
            res1 = f1.result()
            res2 = f2.result()

        status_codes = [res1.status_code, res2.status_code]
        assert 201 in status_codes, "At least one borrow must succeed"
        assert 409 in status_codes, "The other concurrent borrow must be rejected with 409"

    def test_renew_loan(self, client):
        # Loan 8 belongs to Member 5, not overdue in seed
        resp = client.post("/loans/8/renew")
        assert resp.status_code in [200, 409]
        if resp.status_code == 200:
            data = resp.json()
            assert data["loan_id"] == 8
            assert data["renewals"] >= 1

    def test_return_and_fines_flow(self, client):
        # Create a clean member and borrow a book
        new_member = db.query(
            "INSERT INTO members (name, email) VALUES ('Test Returner', 'returner@test.edu') RETURNING id"
        )[0]
        member_id = new_member["id"]

        # Borrow book 4
        borrow_resp = client.post("/borrow", json={"member_id": member_id, "book_id": 4})
        assert borrow_resp.status_code == 201
        loan_id = borrow_resp.json()["loan_id"]

        # Return the loan
        return_resp = client.post("/return", json={"loan_id": loan_id})
        assert return_resp.status_code == 200
        assert return_resp.json()["loan_id"] == loan_id

        # Second return must fail with 409
        dup_return = client.post("/return", json={"loan_id": loan_id})
        assert dup_return.status_code == 409

    def test_pay_fines(self, client):
        # Member 4 has unpaid fines
        resp = client.post("/members/4/fines/pay")
        assert resp.status_code == 200
        data = resp.json()
        assert data["member_id"] == 4
        assert data["cleared"] > 0
        assert data["paid"] > 0

        # Paying again when cleared gives 409
        resp2 = client.post("/members/4/fines/pay")
        assert resp2.status_code == 409
