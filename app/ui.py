"""Interactive Modern Web UI for Library Lending System."""

UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Library Lending System — Operational Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-card: rgba(30, 41, 59, 0.7);
      --border-color: #334155;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent: #38bdf8;
      --accent-hover: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --purple: #8b5cf6;
      --radius: 12px;
      --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 15% 15%, #1e1b4b 0%, #0f172a 50%, #020617 100%);
      color: var(--text-primary);
      min-height: 100vh;
      line-height: 1.5;
      padding-bottom: 60px;
    }

    header {
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .header-content {
      max-width: 1200px;
      margin: 0 auto;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, var(--accent), var(--purple));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
    }

    .brand-title {
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #ffffff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .health-strip {
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(0, 0, 0, 0.2);
      padding: 6px 14px;
      border-radius: 9999px;
      border: 1px solid var(--border-color);
    }

    .health-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--text-secondary);
    }

    .indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--text-muted);
      display: inline-block;
      transition: var(--transition);
    }

    .indicator.active {
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
    }

    .indicator.error {
      background: var(--danger);
      box-shadow: 0 0 8px var(--danger);
    }

    main {
      max-width: 1200px;
      margin: 32px auto 0;
      padding: 0 24px;
    }

    .nav-tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 24px;
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 0.95rem;
      font-weight: 600;
      padding: 12px 18px;
      cursor: pointer;
      position: relative;
      transition: var(--transition);
      border-radius: 8px 8px 0 0;
    }

    .tab-btn:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.04);
    }

    .tab-btn.active {
      color: var(--accent);
    }

    .tab-btn.active::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--accent);
      box-shadow: 0 0 8px var(--accent);
    }

    .tab-pane {
      display: none;
      animation: fadeIn 0.25s ease;
    }

    .tab-pane.active {
      display: block;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }

    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.01em;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 24px;
    }

    .table-container {
      overflow-x: auto;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.9rem;
    }

    th {
      background: rgba(15, 23, 42, 0.7);
      padding: 12px 16px;
      font-weight: 600;
      color: var(--text-secondary);
      border-bottom: 1px solid var(--border-color);
    }

    td {
      padding: 12px 16px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.5);
      color: var(--text-primary);
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .badge-success { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .badge-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
    .badge-purple { background: rgba(139, 92, 246, 0.2); color: #c084fc; }
    .badge-info { background: rgba(56, 189, 248, 0.2); color: #7dd3fc; }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }

    input, select, textarea {
      width: 100%;
      padding: 10px 14px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      color: var(--text-primary);
      font-family: inherit;
      font-size: 0.9rem;
      transition: var(--transition);
    }

    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 9px 18px;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: var(--transition);
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--accent), #0284c7);
      color: #0f172a;
    }

    .btn-primary:hover {
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35);
      transform: translateY(-1px);
    }

    .btn-danger {
      background: rgba(239, 68, 68, 0.2);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }

    .btn-danger:hover {
      background: rgba(239, 68, 68, 0.3);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-primary);
      border: 1px solid var(--border-color);
    }

    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.12);
    }

    .btn-sm {
      padding: 5px 10px;
      font-size: 0.78rem;
      border-radius: 6px;
    }

    .alert {
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 0.88rem;
      margin-top: 14px;
      display: none;
      font-family: 'JetBrains Mono', monospace;
    }

    .alert-success {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid var(--success);
      color: #a7f3d0;
    }

    .alert-error {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid var(--danger);
      color: #fecaca;
    }

    .stats-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-box {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 18px 20px;
    }

    .stat-label {
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.05em;
    }

    .stat-val {
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-top: 4px;
    }

    code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85em;
      background: rgba(0,0,0,0.3);
      padding: 2px 5px;
      border-radius: 4px;
    }
  </style>
</head>
<body>

<header>
  <div class="header-content">
    <div class="brand">
      <div class="brand-icon">📚</div>
      <div>
        <div class="brand-title">Library Lending System</div>
        <div class="brand-sub">PostgreSQL • Redis • FastAPI • High-Concurrency Engine</div>
      </div>
    </div>
    <div class="health-strip">
      <div class="health-pill">
        <span id="pg-dot" class="indicator"></span>
        <span>PostgreSQL</span>
      </div>
      <div class="health-pill">
        <span id="redis-dot" class="indicator"></span>
        <span>Redis</span>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="checkHealth()">↻ Refresh</button>
    </div>
  </div>
</header>

<main>
  <div class="stats-row">
    <div class="stat-box">
      <div class="stat-label">Total Titles</div>
      <div class="stat-val" id="stat-titles">-</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Available Copies</div>
      <div class="stat-val" id="stat-avail">-</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Redis Cache</div>
      <div class="stat-val" style="color: var(--accent); font-size: 1.3rem; margin-top:8px;">TTL 30s • SET NX PX</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Concurrency Model</div>
      <div class="stat-val" style="color: var(--success); font-size: 1.3rem; margin-top:8px;">SKIP LOCKED</div>
    </div>
  </div>

  <div class="nav-tabs">
    <button class="tab-btn active" onclick="switchTab('catalogue')">📖 Catalogue & Books</button>
    <button class="tab-btn" onclick="switchTab('borrow')">🔄 Borrow & Return</button>
    <button class="tab-btn" onclick="switchTab('members')">👤 Member Management</button>
  </div>

  <!-- TAB 1: CATALOGUE -->
  <div id="tab-catalogue" class="tab-pane active">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Book Catalogue</div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-primary btn-sm" onclick="toggleAddBookForm()">+ Add New Book</button>
          <button class="btn btn-secondary btn-sm" onclick="loadBooks()">↻ Refresh</button>
        </div>
      </div>

      <!-- Add Book Inline Form -->
      <div id="add-book-box" style="display:none; background: rgba(15,23,42,0.6); padding: 18px; border-radius: 8px; margin-bottom: 20px; border: 1px solid var(--border-color);">
        <h4 style="margin-bottom: 12px; font-size: 0.95rem;">Add New Title to Catalogue</h4>
        <div style="display: grid; grid-template-columns: 2fr 2fr 1fr auto; gap: 12px; align-items: flex-end;">
          <div>
            <label>Title</label>
            <input type="text" id="new-title" placeholder="e.g. Clean Architecture">
          </div>
          <div>
            <label>Author</label>
            <input type="text" id="new-author" placeholder="e.g. Robert C. Martin">
          </div>
          <div>
            <label>Copies</label>
            <input type="number" id="new-copies" value="2" min="1" max="10">
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary" onclick="submitCreateBook()">Save</button>
            <button class="btn btn-secondary" onclick="toggleAddBookForm()">Cancel</button>
          </div>
        </div>
        <div style="margin-top: 8px;">
          <label style="display: inline-flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" id="new-ref" style="width: auto;"> Reference Only (non-circulating)
          </label>
        </div>
        <div id="add-book-alert" class="alert"></div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Author</th>
              <th>Availability</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="books-tbody">
            <tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">Loading catalogue...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 2: BORROW & RETURN -->
  <div id="tab-borrow" class="tab-pane">
    <div class="grid-2">
      <!-- Borrow Card -->
      <div class="card">
        <div class="card-title" style="margin-bottom: 16px;">Borrow a Book</div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">
          Validates loan limit (max 4), no existing overdue loans, unpaid fines &lt; $100, and uses atomic PostgreSQL row-level locks.
        </p>
        <div class="form-group">
          <label>Member ID</label>
          <input type="number" id="borrow-member-id" placeholder="e.g. 1" value="1">
        </div>
        <div class="form-group">
          <label>Book ID</label>
          <input type="number" id="borrow-book-id" placeholder="e.g. 1" value="1">
        </div>
        <button class="btn btn-primary" style="width: 100%;" onclick="submitBorrow()">Checkout Book</button>
        <div id="borrow-alert" class="alert"></div>
      </div>

      <!-- Return Card -->
      <div class="card">
        <div class="card-title" style="margin-bottom: 16px;">Return a Book</div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">
          Calculates late fines with weekend exemptions and 3-day grace period. Restores copy availability.
        </p>
        <div class="form-group">
          <label>Loan ID</label>
          <input type="number" id="return-loan-id" placeholder="e.g. 1">
        </div>
        <button class="btn btn-secondary" style="width: 100%;" onclick="submitReturn()">Process Return</button>
        <div id="return-alert" class="alert"></div>
      </div>
    </div>
  </div>

  <!-- TAB 3: MEMBERS -->
  <div id="tab-members" class="tab-pane">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Member Account Lookup</div>
      </div>
      <div style="display: flex; gap: 12px; margin-bottom: 20px; max-width: 500px;">
        <input type="number" id="lookup-member-id" placeholder="Member ID (1 to 5)" value="2">
        <button class="btn btn-primary" onclick="lookupMember()">Inspect</button>
      </div>

      <div id="member-details-container" style="display:none;">
        <div class="stats-row" style="margin-bottom: 20px;">
          <div class="stat-box">
            <div class="stat-label">Active Loans</div>
            <div class="stat-val" id="mem-active">-</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Overdue Loans</div>
            <div class="stat-val" id="mem-overdue" style="color: var(--danger);">-</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Unpaid Fines</div>
            <div class="stat-val" id="mem-fines" style="color: var(--warning);">-</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">Can Borrow</div>
            <div class="stat-val" id="mem-eligible" style="font-size: 1.3rem; margin-top:8px;">-</div>
          </div>
        </div>

        <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
          <h4 style="font-size: 1rem;">Current Loans</h4>
          <button id="pay-fines-btn" class="btn btn-primary btn-sm" onclick="payMemberFines()">Clear Outstanding Fines</button>
        </div>

        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Loan ID</th>
                <th>Copy Barcode</th>
                <th>Issued</th>
                <th>Due</th>
                <th>Status</th>
                <th>Renewals</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="member-loans-tbody"></tbody>
          </table>
        </div>
        <div id="member-action-alert" class="alert"></div>
      </div>
    </div>
  </div>
</main>

<script>
  function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
  }

  async function checkHealth() {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      document.getElementById('pg-dot').className = 'indicator ' + (data.postgres ? 'active' : 'error');
      document.getElementById('redis-dot').className = 'indicator ' + (data.redis ? 'active' : 'error');
    } catch (e) {
      document.getElementById('pg-dot').className = 'indicator error';
      document.getElementById('redis-dot').className = 'indicator error';
    }
  }

  async function loadBooks() {
    try {
      const res = await fetch('/books');
      const data = await res.json();
      const tbody = document.getElementById('books-tbody');
      tbody.innerHTML = '';
      let totalTitles = data.books.length;
      let totalAvail = 0;

      data.books.forEach(b => {
        totalAvail += parseInt(b.available || 0);
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code>#${b.id}</code></td>
          <td style="font-weight:600;">${escapeHtml(b.title)}</td>
          <td style="color:var(--text-secondary);">${escapeHtml(b.author)}</td>
          <td>
            <span class="badge ${b.available > 0 ? 'badge-success' : 'badge-danger'}">
              ${b.available} / ${b.copies} available
            </span>
          </td>
          <td>
            ${b.reference_only ? '<span class="badge badge-purple">Reference</span>' : '<span class="badge badge-info">Circulating</span>'}
          </td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary btn-sm" onclick="checkAvail(${b.id})">Check Cache</button>
              <button class="btn btn-danger btn-sm" onclick="deleteBook(${b.id}, '${escapeHtml(b.title)}')">Delete</button>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      });

      document.getElementById('stat-titles').innerText = totalTitles;
      document.getElementById('stat-avail').innerText = totalAvail;
    } catch (err) {
      console.error(err);
    }
  }

  async function checkAvail(bookId) {
    const t0 = performance.now();
    const res = await fetch(`/books/${bookId}/availability`);
    const data = await res.json();
    const elapsed = Math.round(performance.now() - t0);
    alert(`Book: ${data.title}\\nAvailable: ${data.available}\\nRedis Cache Hit: ${data.cached}\\nTime: ${elapsed}ms`);
  }

  function toggleAddBookForm() {
    const box = document.getElementById('add-book-box');
    box.style.display = box.style.display === 'none' ? 'block' : 'none';
  }

  async function submitCreateBook() {
    const title = document.getElementById('new-title').value.trim();
    const author = document.getElementById('new-author').value.trim();
    const copies = parseInt(document.getElementById('new-copies').value);
    const ref = document.getElementById('new-ref').checked;
    const alertBox = document.getElementById('add-book-alert');

    if (!title || !author) {
      showAlert(alertBox, 'Title and Author are required', false);
      return;
    }

    try {
      const res = await fetch('/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, author, copies_count: copies, reference_only: ref })
      });
      const data = await res.json();
      if (res.ok) {
        showAlert(alertBox, `✓ Added "${data.title}" with ${data.copies_created} copies`, true);
        document.getElementById('new-title').value = '';
        document.getElementById('new-author').value = '';
        loadBooks();
        setTimeout(() => toggleAddBookForm(), 1200);
      } else {
        showAlert(alertBox, `Error: ${data.detail || JSON.stringify(data)}`, false);
      }
    } catch (e) {
      showAlert(alertBox, 'Network error', false);
    }
  }

  async function deleteBook(id, title) {
    if (!confirm(`Delete book "${title}" (ID: ${id})?`)) return;
    try {
      const res = await fetch(`/books/${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (res.ok) {
        loadBooks();
      } else {
        alert(`Cannot delete: ${data.detail}`);
      }
    } catch (e) {
      alert('Delete failed');
    }
  }

  async function submitBorrow() {
    const member_id = parseInt(document.getElementById('borrow-member-id').value);
    const book_id = parseInt(document.getElementById('borrow-book-id').value);
    const box = document.getElementById('borrow-alert');
    try {
      const res = await fetch('/borrow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ member_id, book_id })
      });
      const data = await res.json();
      if (res.ok) {
        showAlert(box, `✓ Loan Issued! Loan ID: ${data.loan_id} | Due: ${data.due_on} | Barcode: ${data.barcode}`, true);
        loadBooks();
      } else {
        showAlert(box, `Rejected (409/400): ${data.detail}`, false);
      }
    } catch (e) {
      showAlert(box, 'Request failed', false);
    }
  }

  async function submitReturn() {
    const loan_id = parseInt(document.getElementById('return-loan-id').value);
    const box = document.getElementById('return-alert');
    try {
      const res = await fetch('/return', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ loan_id })
      });
      const data = await res.json();
      if (res.ok) {
        showAlert(box, `✓ Returned! Fine charged: $${data.fine.amount} (${data.fine.chargeable_days} days overdue)`, true);
        loadBooks();
      } else {
        showAlert(box, `Error: ${data.detail}`, false);
      }
    } catch (e) {
      showAlert(box, 'Request failed', false);
    }
  }

  async function lookupMember() {
    const id = document.getElementById('lookup-member-id').value;
    try {
      const res = await fetch(`/members/${id}`);
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail);
        return;
      }
      document.getElementById('member-details-container').style.display = 'block';
      document.getElementById('mem-active').innerText = data.summary.active_loans;
      document.getElementById('mem-overdue').innerText = data.summary.overdue_loans;
      document.getElementById('mem-fines').innerText = '$' + data.summary.unpaid_fines.toFixed(2);
      document.getElementById('mem-eligible').innerText = data.summary.eligible_to_borrow ? '✓ Eligible' : '✗ Blocked';
      document.getElementById('mem-eligible').style.color = data.summary.eligible_to_borrow ? 'var(--success)' : 'var(--danger)';

      const tbody = document.getElementById('member-loans-tbody');
      tbody.innerHTML = '';
      data.loans.forEach(l => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code>#${l.id}</code></td>
          <td><code>${l.copy_id}</code></td>
          <td>${l.issued_on}</td>
          <td>${l.due_on}</td>
          <td>${l.returned_on ? '<span class="badge badge-success">Returned</span>' : '<span class="badge badge-warning">Active</span>'}</td>
          <td>${l.renewals} / 2</td>
          <td>
            ${!l.returned_on ? `<button class="btn btn-secondary btn-sm" onclick="renewLoan(${l.id})">Renew</button>` : '-'}
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      alert('Error fetching member');
    }
  }

  async function renewLoan(id) {
    const box = document.getElementById('member-action-alert');
    try {
      const res = await fetch(`/loans/${id}/renew`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        showAlert(box, `✓ Renewed! New Due Date: ${data.due_on}`, true);
        lookupMember();
      } else {
        showAlert(box, `Cannot renew: ${data.detail}`, false);
      }
    } catch (e) {
      showAlert(box, 'Renew failed', false);
    }
  }

  async function payMemberFines() {
    const id = document.getElementById('lookup-member-id').value;
    const box = document.getElementById('member-action-alert');
    try {
      const res = await fetch(`/members/${id}/fines/pay`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        showAlert(box, `✓ Paid! Cleared ${data.cleared} fine(s) totaling $${data.paid}`, true);
        lookupMember();
      } else {
        showAlert(box, `Notice: ${data.detail}`, false);
      }
    } catch (e) {
      showAlert(box, 'Payment failed', false);
    }
  }

  function showAlert(el, msg, success) {
    el.className = 'alert ' + (success ? 'alert-success' : 'alert-error');
    el.innerText = msg;
    el.style.display = 'block';
  }

  function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Initialize
  checkHealth();
  loadBooks();
  setInterval(checkHealth, 10000);
</script>

</body>
</html>
"""
