# Spec: User Registration

## Overview
Step 2 turns the existing static `/register` page into a working sign-up flow. Today `GET /register` renders a fully built form (`name`, `email`, `password`) that posts to itself, but `app.py` declares no `methods=["POST"]`, so submitting it returns 405 and nothing is ever written to the database. This step adds POST handling, server-side validation, werkzeug password hashing, duplicate-email rejection, and a new `create_user()` / `get_user_by_email()` pair in `database/db.py`. It is the first feature that writes user data, so it establishes the account records that login (Step 3), profile (Step 4), and all per-user expense routes (Steps 7–9) depend on. Registration deliberately stops at account creation — it does **not** log the user in, because `session` and `app.secret_key` are owned by Step 3.

## Depends on
- **Step 1 — Database setup.** Complete. `database/db.py` implements `get_db()` (with `PRAGMA foreign_keys = ON`), `init_db()`, and `seed_db()`, and the `users` table already exists with the exact columns this step needs. No schema work is required.
- Nothing else. This step does not depend on login/session work and must not implement it.

> **Note:** CLAUDE.md states "`database/db.py` is currently empty — do not assume helpers exist". That line is **stale**: the file is implemented (2819 bytes, three functions). Update that warning in CLAUDE.md as part of this step.

## Routes
- `POST /register` — accepts the sign-up form, validates input, hashes the password, inserts the user, redirects to `GET /login` on success; re-renders `register.html` with `error` on failure — public

Implementation detail: this is **not** a new route function. Change the existing decorator to `@app.route("/register", methods=["GET", "POST"])` and branch on `request.method` inside `register()`. GET behaviour must stay exactly as it is today.

No other new routes. `GET /login` already exists and is the redirect target; do **not** implement its POST handler — that is Step 3.

## Database changes
**No database changes.** Verified against `database/db.py`: the `users` table already carries everything registration needs, including the `UNIQUE` constraint that backs duplicate-email detection.

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
```

Two **new helper functions** go in `database/db.py` (no schema migration):

- `get_user_by_email(email)` — `SELECT * FROM users WHERE email = ?`, returns a `sqlite3.Row` or `None`.
- `create_user(name, email, password)` — hashes with `generate_password_hash`, inserts via `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)`, returns `cursor.lastrowid`. Mirror the existing `try/commit/finally: conn.close()` pattern used by `init_db()` and `seed_db()`.

Handle the race between the duplicate check and the insert by catching `sqlite3.IntegrityError` inside `create_user()` and returning `None`, rather than trusting the pre-check alone.

## Templates

**Create:** None. `templates/register.html` already exists and already renders `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}`.

**Modify:**
- `templates/register.html` — change `action="/register"` to `action="{{ url_for('register') }}"`. The hardcoded URL violates CLAUDE.md's `url_for()` rule. Also re-populate `name` and `email` on a failed submit via `value="{{ name or '' }}"` / `value="{{ email or '' }}"` so a user does not retype everything after one error. Never re-populate the password field.
- `templates/login.html` — change `action="/login"` to `action="{{ url_for('login') }}"`. Same hardcoded-URL violation; fixing it here keeps the two auth forms consistent and costs nothing, since the POST handler is still Step 3's job.

Do **not** add a flash-message block to `base.html`. Flash requires `app.secret_key`, which belongs to Step 3; this step uses the `error=` template-variable convention the templates were already built around.

## Files to change
- `app.py` — add `request`, `redirect`, `url_for` to the Flask import; change the `/register` decorator to accept POST; implement the POST branch in `register()`; import `create_user` and `get_user_by_email` from `database.db`.
- `database/db.py` — add `get_user_by_email()` and `create_user()`; add `sqlite3.IntegrityError` handling.
- `templates/register.html` — `url_for()` in the form action; sticky `name`/`email` values.
- `templates/login.html` — `url_for()` in the form action.
- `static/css/style.css` — only if a new class is genuinely needed. `.auth-error`, `.form-group`, `.form-input`, and `.btn-submit` already exist and should be reused as-is. If touched, note that `.auth-error` currently hardcodes `border: 1px solid #f5c6c2`; replace it with a variable rather than adding more hex.
- `tests/conftest.py` — add a fixture that points `database.db.DB_PATH` at a temp file for tests that write users (see below).
- `CLAUDE.md` — mark `POST /register` implemented in the status table; correct the stale "`database/db.py` is currently empty" warning.

## Files to create
- `tests/test_register.py` — the test suite for this feature.

No new templates, no new CSS files, no new Python modules.

## New dependencies
**No new dependencies.** `werkzeug==3.1.6` is already pinned in `requirements.txt` and `generate_password_hash` is already imported in `database/db.py`. `requirements.txt` is unchanged.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only.
- Parameterised queries only (`?` placeholders). Never an f-string or `%` interpolation in SQL.
- Passwords hashed with werkzeug (`generate_password_hash`). Never store or log a plaintext password, and never put one in a template variable.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- **No DB logic in route functions.** `register()` must not call `get_db()` or write SQL; it calls the `database/db.py` helpers only.
- **No sessions, no `flash()`, no `app.secret_key`.** Registration succeeds and redirects to `/login`; it does not log the user in. That is Step 3.
- Routes stay in `app.py` — no blueprints.
- `url_for()` for every internal link and form action.
- PEP 8, snake_case.
- Do not touch any stub route other than `/register`.
- Port stays 5001.
- **Test isolation is mandatory.** `tests/test_db.py::test_seed_db_is_idempotent` asserts `user_count == 1` against the real `expense_tracker.db`. Any test that registers a user will break it unless the new tests monkeypatch `database.db.DB_PATH` to a `tmp_path` file and call `init_db()` against it. Fix this in `conftest.py`; do not weaken the existing assertion.

### Validation rules
Server-side, in the route, before calling `create_user()`. All failures re-render `register.html` with a single `error` string and HTTP 200 — no `abort()`, since these are user input errors, not HTTP errors.

| Rule | Message |
|---|---|
| All three fields present after `.strip()` | `"All fields are required."` |
| `email` well-formed: exactly one `@`, non-empty local part, ≥2 non-empty domain labels, no whitespace | `"Please enter a valid email address."` |
| `password` at least 8 characters | `"Password must be at least 8 characters."` |
| `email` not already in `users` | `"An account with that email already exists."` |

Normalise email with `.strip().lower()` before both the lookup and the insert. Strip whitespace from `name`. Never strip or alter the password.

## Definition of done
Verified by running `python app.py` on port 5001 and by `pytest`.

- [ ] `GET /register` still returns 200 and renders the form unchanged.
- [ ] Submitting the form with valid new details returns a 302 redirect to `/login` (previously returned 405).
- [ ] After that submit, `sqlite3 expense_tracker.db "SELECT name, email FROM users"` shows the new row alongside the demo user.
- [ ] The stored `password_hash` starts with `scrypt:` or `pbkdf2:` and the plaintext password appears nowhere in the database.
- [ ] Registering the same email twice re-renders the page with "An account with that email already exists." and does **not** create a second row.
- [ ] Registering with the seeded `demo@spendly.com` is rejected with the same message.
- [ ] Submitting an empty form re-renders with "All fields are required." and creates no row.
- [ ] A 7-character password is rejected with "Password must be at least 8 characters."
- [ ] `nitish@example` (no TLD) is rejected with "Please enter a valid email address."
- [ ] `a@@b.com`, `@example.com`, `nitish@.com`, `nitish@example.` and addresses containing spaces are all rejected server-side (HTML5 `type="email"` blocks these in a browser, so verify with `curl`, not the form).
- [ ] After a failed submit, the name and email fields are still filled in and the password field is empty.
- [ ] `curl -s localhost:5001/register | grep 'action='` shows `action="/register"` generated by `url_for()`, and no template contains a hardcoded internal URL.
- [ ] `pytest` passes fully, including the pre-existing `tests/test_db.py`, `tests/test_hero.py`, and `tests/test_terms_privacy.py`.
- [ ] Running `pytest` twice in a row passes both times and leaves `expense_tracker.db` with exactly 1 user and 8 expenses.
- [ ] `/logout`, `/profile`, and the `/expenses/*` routes still return their original stub strings — untouched.
