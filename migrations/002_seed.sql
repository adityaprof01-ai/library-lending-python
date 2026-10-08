-- Seeds are applied on every `docker compose up`, so every statement here
-- has to be safe to run twice.

INSERT INTO books (id, title, author, isbn, reference_only) VALUES
 (1,'Designing Data-Intensive Applications','Martin Kleppmann','9781449373320',FALSE),
 (2,'The Pragmatic Programmer','Hunt & Thomas','9780135957059',FALSE),
 (3,'Operating Systems: Three Easy Pieces','Arpaci-Dusseau','9781985086593',FALSE),
 (4,'Introduction to Algorithms','Cormen et al.','9780262046305',FALSE),
 (5,'Compilers: Principles, Techniques and Tools','Aho et al.','9780321486813',FALSE),
 (6,'IEEE Standards Handbook 2026','IEEE','9780000000001',TRUE)
ON CONFLICT DO NOTHING;
SELECT setval('books_id_seq', (SELECT max(id) FROM books));

-- Book 3 deliberately has ONE copy. That is the last-copy race.
INSERT INTO copies (id, book_id, barcode) VALUES
 (1,1,'LIB-0001'),(2,1,'LIB-0002'),(3,1,'LIB-0003'),
 (4,2,'LIB-0004'),(5,2,'LIB-0005'),
 (6,3,'LIB-0006'),
 (7,4,'LIB-0007'),(8,4,'LIB-0008'),(9,4,'LIB-0009'),(10,4,'LIB-0010'),
 (11,5,'LIB-0011'),(12,5,'LIB-0012'),
 (13,6,'LIB-0013')
ON CONFLICT DO NOTHING;
SELECT setval('copies_id_seq', (SELECT max(id) FROM copies));

INSERT INTO members (id, name, email) VALUES
 (1,'Asha Menon','asha@example.edu'),
 (2,'Vikram Rao','vikram@example.edu'),
 (3,'Priya Nair','priya@example.edu'),
 (4,'Rahul Das','rahul@example.edu'),
 (5,'Fatima Sheikh','fatima@example.edu')
ON CONFLICT DO NOTHING;
SELECT setval('members_id_seq', (SELECT max(id) FROM members));

-- Vikram is at the four-book limit. Priya has a book three weeks overdue.
-- Rahul already owes money. Asha is clean and can borrow.
INSERT INTO loans (id, copy_id, member_id, issued_on, due_on, returned_on) VALUES
 (1, 1,  2, CURRENT_DATE - 5,  CURRENT_DATE + 9,  NULL),
 (2, 4,  2, CURRENT_DATE - 5,  CURRENT_DATE + 9,  NULL),
 (3, 7,  2, CURRENT_DATE - 3,  CURRENT_DATE + 11, NULL),
 (4, 11, 2, CURRENT_DATE - 1,  CURRENT_DATE + 13, NULL),
 (5, 2,  3, CURRENT_DATE - 35, CURRENT_DATE - 21, NULL),
 (6, 8,  4, CURRENT_DATE - 60, CURRENT_DATE - 46, CURRENT_DATE - 30),
 (7, 5,  1, CURRENT_DATE - 40, CURRENT_DATE - 26, CURRENT_DATE - 25),
 (8, 12, 5, CURRENT_DATE - 9,  CURRENT_DATE + 5,  NULL)
ON CONFLICT DO NOTHING;
SELECT setval('loans_id_seq', (SELECT max(id) FROM loans));

-- Rahul's historical late return left him over the blocking threshold.
INSERT INTO fines (id, loan_id, member_id, amount, paid) VALUES
 (1, 6, 4, 60.00, FALSE),
 (2, 6, 4, 55.00, FALSE),
 (3, 7, 1, 20.00, TRUE)
ON CONFLICT DO NOTHING;
SELECT setval('fines_id_seq', (SELECT max(id) FROM fines));

-- Keep copy status consistent with whatever is actually on loan.
UPDATE copies SET status='on_loan'
 WHERE id IN (SELECT copy_id FROM loans WHERE returned_on IS NULL);
UPDATE copies SET status='available'
 WHERE status='on_loan'
   AND id NOT IN (SELECT copy_id FROM loans WHERE returned_on IS NULL);
