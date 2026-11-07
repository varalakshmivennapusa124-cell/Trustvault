# TrustVault



Secure document sharing with a real audit trail. Built for the Snovasys Fresher Hiring Challenge 2026 (RISE).



- **Live:** https://trustvault-osye.onrender.com  (free instance: the first request after idle can take about a minute)

- **Stack:** Django 6, PostgreSQL (SQLite locally), Gunicorn, WhiteNoise, hosted on Render

- Related files: `THREATS.md` (threat model), `PROMPTS.md` (AI usage log), `DESIGN.md` (permission model)



## Demo accounts (seed data, one per role)

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `CHANGE-ME` |
| Document owner | `owner1` | `CHANGE-ME` |
| Viewer | `viewer1` | `CHANGE-ME` |



Suggested walkthrough: log in as `owner1`, upload a document, share it (read) with `viewer1`, log in as `viewer1` and open it, go back and revoke, then reload as `viewer1` (the document is gone and the link returns 404). Finally open **Activity** as `admin` to see every attempt, including refused ones.



## What it does

- Login with three roles. Upload (PDF, PNG, JPG, TXT, max 5 MB), list, search by name, owner, category and date, rename/recategorise, delete.

- Per-document grants (`read`, `edit`) given to named users, taken back at any time.

- Audit trail of uploads, downloads, edits, deletions and permission changes, **including refused attempts**.

- Admin Activity page with filters and a check that the audit chain is intact.



## Roles and permission model

Global roles: **admin** (sees the Activity page, can upload), **owner** (can upload and share their own documents), **viewer** (can only open what was shared with them).



Per document, one function decides everything: `can(user, document, action)` in `vault/permissions.py`. Default is deny.



| Who | read | edit | delete | share |
|---|---|---|---|---|
| Document owner | yes | yes | yes | yes |
| Grant `edit` | yes | yes | no | no |
| Grant `read` | yes | no | no | no |
| Everyone else, **including admin** | no | no | no | no |



- Admin deliberately has no special read access to other people's documents. If admin is compromised, documents do not leak.

- Not allowed and does-not-exist look identical (HTTP 404), so a stranger cannot learn that a document exists.

- Files are stored in the database. No file path exists, so nothing can be fetched around the permission check.

- No share links or tokens are issued. Every request re-checks the `Grant` table, so revoking works on the very next request. The cost: one database query per request, and a copy someone already downloaded cannot be recalled.

- Audit log: each entry stores a hash of the previous entry. The model refuses edits and deletes. The Activity page recomputes the chain and shows where it breaks. It detects editing and removal in the middle; it does **not** stop someone who owns the database (see THREATS.md C4, C5).



## Endpoints (API documentation)

All endpoints except login require a logged-in session. Unauthenticated requests are redirected to the login page.



| Method and path | Who may call it | Outcome when not allowed |
|---|---|---|
| `GET /` (query: `q`, `owner`, `category`, `date_from`, `date_to`) | any logged-in user. Lists only documents they own or were granted | empty list |
| `GET, POST /upload/` | `owner` and `admin` roles | 403, logged |
| `GET /documents/<id>/download/` | document owner, or a user with a `read` or `edit` grant | 404, logged |
| `GET, POST /documents/<id>/share/` (form: `username`, `level`, `action=grant\|revoke`) | document owner only | 404, logged |
| `GET, POST /documents/<id>/edit/` | document owner, or a user with an `edit` grant | 404, logged |
| `POST /documents/<id>/delete/` (GET returns 405) | document owner only | 404, logged |
| `GET /activity/` (query: `outcome`, `page`) | role `admin` only | 404, logged |
| `GET, POST /accounts/login/` | anyone | |
| `POST /accounts/logout/` | logged-in user | |



## Database

Tables (see `*/migrations/`): `accounts_user` (Django user plus `role`), `vault_document` (owner, name, category, content type, size, `data` bytes, timestamps), `vault_grant` (document, user, level, granted_by, unique per document and user), `vault_auditentry` (time, actor, action, document id and name, outcome, detail, prev_hash, entry_hash).



## Run locally (Windows)
