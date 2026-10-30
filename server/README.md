# Teacher Planner server

A small FastAPI app that holds accounts, sign-in sessions and each teacher's
planner in one SQLite file. It costs nothing to run beyond the machine it runs on.

## What it does

- `POST /register`, `POST /login` return the user and a session token.
- Every other request needs `Authorization: Bearer <token>`. Tokens are random,
  only their SHA-256 hash is stored, and they expire after 60 days
  (`PLANNER_SESSION_DAYS`).
- `POST /logout` ends the session. `POST /change-password` changes the password
  for whoever owns the token (it ignores any `user_id` sent) and signs out the
  account's other devices.
- `GET /planner`, `GET /planner/version`, `PUT /planner` store the planner.
  `PUT` must say which version it was based on. If another computer saved
  first, the server answers `409` and the app merges the two copies.
- Passwords need 8+ characters and are hashed with scrypt. Ten wrong passwords
  for one login in 15 minutes locks that login out for the rest of the window.

## Running it

```bash
cd server
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PLANNER_DB_PATH=/var/lib/teacherplanner/planner.db uvicorn app:app --host 127.0.0.1 --port 8000
```

Put it behind HTTPS (for example nginx or Caddy in front of uvicorn) at the
address the app uses, `https://planner.ventro.it.com`. Run a single uvicorn
worker: the sign-in rate limit is kept in memory.

Back up the database file regularly (`sqlite3 planner.db ".backup backup.db"`
works while the server runs).

## Switching from the old server

Accounts from the old server aren't carried over, because its code and
password format aren't in this repo. Teachers create their account again,
and their existing planner on each computer uploads the first time they sign
in. Deploy this server before shipping the new app build: the new app needs a
session token, so against the old server it would ask for a sign-in on every launch.

## Testing against a local copy

```bash
TEACHERPLANNER_SERVER_URL=http://127.0.0.1:8000 python -m planner_app.main
```
