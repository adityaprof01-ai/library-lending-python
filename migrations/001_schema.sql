CREATE TABLE IF NOT EXISTS books (
    id             SERIAL PRIMARY KEY,
    title          TEXT NOT NULL,
    author         TEXT NOT NULL DEFAULT '',
    isbn           TEXT NOT NULL DEFAULT '',
    reference_only BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS copies (
    id      SERIAL PRIMARY KEY,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    barcode TEXT UNIQUE NOT NULL,
    status  TEXT NOT NULL DEFAULT 'available'
            CHECK (status IN ('available','on_loan','lost'))
);
CREATE INDEX IF NOT EXISTS copies_book ON copies (book_id, status);

CREATE TABLE IF NOT EXISTS members (
    id     SERIAL PRIMARY KEY,
    name   TEXT NOT NULL,
    email  TEXT UNIQUE NOT NULL,
    joined DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS loans (
    id          SERIAL PRIMARY KEY,
    copy_id     INT NOT NULL REFERENCES copies(id),
    member_id   INT NOT NULL REFERENCES members(id),
    issued_on   DATE NOT NULL DEFAULT CURRENT_DATE,
    due_on      DATE NOT NULL,
    returned_on DATE,
    renewals    INT NOT NULL DEFAULT 0
);
-- The database guarantee behind the race: a copy can be out exactly once.
CREATE UNIQUE INDEX IF NOT EXISTS loans_one_active_per_copy
    ON loans (copy_id) WHERE returned_on IS NULL;
CREATE INDEX IF NOT EXISTS loans_member ON loans (member_id, returned_on);

CREATE TABLE IF NOT EXISTS fines (
    id         SERIAL PRIMARY KEY,
    loan_id    INT NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    member_id  INT NOT NULL REFERENCES members(id),
    amount     NUMERIC(8,2) NOT NULL CHECK (amount >= 0),
    paid       BOOLEAN NOT NULL DEFAULT FALSE,
    paid_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fines_member ON fines (member_id, paid);
