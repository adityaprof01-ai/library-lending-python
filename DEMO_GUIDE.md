# Demo Day & Presentation Guide: Library Lending Pipeline
**Course:** 3rd Year ISE · Capstone Assignment · 80 Marks

---

## ⏱️ Demo Time Allocation (10 min Demo + 5 min Questions)

Follow this order strictly during your 10-minute live demo:
- **0:00 – 2:00:** Git history, branch ruleset, PR promotion, zero branch inconsistencies.
- **2:00 – 5:00:** Local Docker Compose demo, Web UI in browser, API CRUD, data in PostgreSQL.
- **5:00 – 7:00:** CircleCI dashboard: full pipeline green on `main`, build-only on `staging`/`prod`.
- **7:00 – 10:00:** Kubernetes: 3 namespaces (`qa`, `stage`, `prod`), live rollout restart, Image ID digest verification.
- **10:00 – 15:00:** Viva / Examiner Technical Questions.

> 💡 **Tip:** Trigger your CircleCI pipeline or merge your PR at the very start of your slot so it builds while you present Git and Compose!

---

## 📋 Part-by-Part Live Walkthrough

### Part 1: Git and Branch Promotion (15 Marks)

1. **Show Branch Ruleset:**
   - In GitHub repository: `Settings` → `Rules` → `Rulesets` → `protected-branches`.
   - Point out: Status is **Active**, bypass list is **Empty**, targets `main`, `staging`, and `prod`.
   - Blocks force pushes, blocks deletions, requires Pull Requests.

2. **Demonstrate Ruleset Enforcement:**
   Run in terminal:
   ```bash
   git checkout main
   git commit --allow-empty -m "testing direct push"
   git push origin main
   ```
   *Expected result:* GitHub immediately rejects the push with:
   `remote: error: GH013: Repository rule violations found for refs/heads/main`
   Clean up:
   ```bash
   git reset --hard origin/main
   ```

3. **Show Clean Commit & Promotion History:**
   ```bash
   git log --oneline --graph --all
   ```
   Point out:
   - Feature was developed on `feature/book-management-and-ui`.
   - Merged into `main` via PR.
   - Promoted to `staging` via merge commit.
   - Promoted to `prod` via merge commit.

4. **Prove Zero Branch Inconsistencies:**
   ```bash
   git diff main staging
   git diff staging prod
   ```
   *Expected result:* Both commands return completely empty output!

---

### Part 2: Dockerfile & Docker Compose (15 Marks)

1. **Highlight Dockerfile Security & Best Practices:**
   - Base image pinned: `python:3.12-slim`.
   - Non-root user: `appuser` (created via `groupadd` / `useradd`, run via `USER appuser`).
   - Layer caching: `COPY requirements.txt .` and `pip install` before copying source code.
   - Non-sensitive: No secrets or `.env` baked into image.
   - Complete `.dockerignore` included.

2. **Run Docker Compose:**
   ```bash
   docker compose up -d
   ```
   - Point out that migrations run automatically via `migrations` container.
   - `depends_on` with `condition: service_healthy` ensures Postgres and Redis are fully healthy before the application boots.

3. **Browser UI Demo:**
   - Open `http://localhost:8080/` in your browser.
   - Point out:
     - Real-time health indicators (PostgreSQL and Redis connected).
     - Live Catalogue: Click "Check Cache" to demonstrate Redis cache hit/miss speed.
     - Add a new book via the UI: Enter title, author, copies, and hit "Save".
     - Borrow a book: Select book and member, see immediate confirmation and barcode.
     - Return a book: Enter loan ID, see calculated fines and returned status.
     - Member Lookup: Inspect Vikram Rao (ID 2), view active loans, and clear fines.

4. **Demonstrate API CRUD & Database Persistence:**
   Run in terminal:
   ```bash
   # 1. Create a record (POST)
   curl -X POST http://localhost:8080/books \
     -H "Content-Type: application/json" \
     -d '{"title": "The Phoenix Project", "author": "Gene Kim", "copies_count": 2}'

   # 2. Read it back (GET)
   curl http://localhost:8080/books/7

   # 3. Show data physically persisted in Postgres
   docker compose exec db psql -U postgres -d library -c "SELECT id, title, author FROM books WHERE title LIKE '%Phoenix%';"
   docker compose exec db psql -U postgres -d library -c "SELECT id, book_id, barcode, status FROM copies WHERE book_id=7;"

   # 4. Delete the record (DELETE)
   curl -X DELETE http://localhost:8080/books/7
   ```

---

### Part 3: CircleCI Pipeline (20 Marks)

1. **Show CircleCI Pipelines:**
   - Open CircleCI project dashboard.
   - **On `main` (QA):**
     1. `secret-scan` (Gitleaks scan across commits)
     2. `lint` (Ruff linter)
     3. `unit-tests` (Pytest with 98% coverage, >70% minimum)
     4. `integration-tests` (Real Postgres 16 and Redis 7 service containers)
     5. `image-build-and-push`
   - **On `staging` and `prod`:**
     - Build-only pipeline (`image-build-and-push`), no test stages.

2. **Show Dual Tags on Docker Hub:**
   - Open your Docker Hub repository page.
   - Show the two tags pushed for the commit:
     - Moving tag: `:qa` (or `:stage` / `:prod`)
     - Immutable tag: `:<branch>-<short-sha>` (e.g. `main-163b79b`)

3. **CircleCI Environment Variables:**
   - Open CircleCI Project Settings → Environment Variables.
   - Show `DOCKERHUB_USER` and `DOCKERHUB_TOKEN` (never committed to repository).

---

### Part 4: Kubernetes Across 3 Namespaces (20 Marks)

1. **Show 3 Namespaces:**
   ```bash
   kubectl get namespaces
   ```
   Points out: `qa`, `stage`, `prod`.

2. **Show Secrets and Pods:**
   ```bash
   kubectl get secrets -n qa
   kubectl get pods -n qa
   kubectl get pods -n stage
   kubectl get pods -n prod
   ```

3. **Demonstrate the Continuous Deployment Loop:**
   ```bash
   # Trigger rolling restart
   kubectl rollout restart deployment/library-app -n qa
   kubectl rollout status deployment/library-app -n qa
   ```

4. **Verify Running Image and Digest:**
   ```bash
   # Check pod image
   kubectl get pods -n qa -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}'

   # Check exact Image ID digest
   POD_NAME=$(kubectl get pods -n qa -l app=library-app -o jsonpath='{.items[0].metadata.name}')
   kubectl describe pod $POD_NAME -n qa | grep -i "image id"
   ```
   *Explain:* The Image ID digest matches the exact image digest pushed by CircleCI.

---

## 🎯 Viva / Oral Exam Questions (10 Marks)

Here are the exact answers to the 7 questions listed in the assignment:

### 1. "Why is this a Deployment and not a Pod?"
> **Answer:** A Pod is an ephemeral, single instance with no self-healing capabilities; if a Pod crashes or the underlying Kubernetes node dies, it is gone forever. A Deployment manages a ReplicaSet, ensuring the desired number of Pod replicas remain healthy, handles automated self-healing, supports declarative zero-downtime rolling updates, and enables rollback to previous revisions.

### 2. "Your integration test talks to localhost on CircleCI but to db in Compose. Why are those different?"
> **Answer:** In Docker Compose, each service runs in its own network container namespace, so containers discover each other via Docker's embedded DNS using their service names (`db`, `redis`). In CircleCI, secondary service containers share the primary executor's network namespace (the Linux host loopback), meaning PostgreSQL and Redis are bound directly to `localhost`.

### 3. "What happens if I delete one of your Pods right now?"
> **Answer:** The Deployment controller detects that current replicas (0) no longer match desired replicas (1) and immediately schedules and starts a brand new Pod to restore the desired state.

### 4. "Why does your Dockerfile create a user instead of running as root?"
> **Answer:** Principle of Least Privilege. If a container running as `root` (UID 0) suffers a remote code execution exploit or container escape vulnerability, the attacker would have full root access to the host kernel and filesystem. Running as a dedicated unprivileged user (`appuser`) contains the damage inside the container process space.

### 5. "Your Service says Running but the page does not load. Where do you look first?"
> **Answer:** Check the Service endpoints using `kubectl get endpoints <service-name> -n <namespace>`. If the `ENDPOINTS` column is `<none>`, the Service's `selector` labels do not match the Pod's `metadata.labels`. Second, check port mapping (`outside:inside` / `targetPort`). Third, check container logs with `kubectl logs <pod-name> -n <namespace>`.

### 6. "Why :qa and :stage rather than one :latest tag for everything?"
> **Answer:** Environment isolation and promotion safety. `:latest` causes all environments to pull the same moving target simultaneously, breaking the progression of testing in QA before staging. Separate moving tags (`:qa`, `:stage`, `:prod`) allow each environment to track its own lifecycle stage, while immutable tags (`:<branch>-<short-sha>`) ensure full auditability of the exact commit running in production.

### 7. "What exactly does rollout restart do — does it rebuild anything?"
> **Answer:** It does **not** rebuild anything. `rollout restart` injects/updates a timestamp annotation (`kubectl.kubernetes.io/restartedAt`) in the Deployment Pod template. This triggers a rolling update where new Pods are scheduled, pull the image according to `imagePullPolicy: Always`, and replace the old Pods once healthy.
