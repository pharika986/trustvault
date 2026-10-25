# TrustVault - secure document sharing with an audit trail

Demo video: https://drive.google.com/file/d/1iN1ty42WW-VCZ-cnTQZypC1InC9YC1Vm/view

A Django web app. A document can be opened only by people the owner granted access to. Access can be taken back and it stops working on the very next request. Every action, including refused attempts, is written to an audit log chained with hashes, so changes to old rows can be detected.

## Live site (no setup needed)

https://trustvault-pharika986.onrender.com

Free hosting: it sleeps when idle, so the first page can take about a minute. Uploaded files and data reset on each redeploy; the demo accounts and two sample files are re-created automatically, and the audit log starts empty.

## Demo logins

| Role | Username | Password | Notes |
|---|---|---|---|
| Owner | owner_demo | Owner#Demo2026 | has 2 documents |
| Viewer | viewer_demo | Viewer#Demo2026 | has salary-letter.txt shared (read only) |
| Viewer | viewer2_demo | Viewer2#Demo2026 | nothing shared |
| Admin | admin_demo | Admin#Demo2026 | sees Activity and Users, not document contents |

## What to try (about 3 minutes)

1. Log in as owner_demo. Download a document.
2. In a private window, log in as viewer2_demo. The list is empty. Paste the owner's download link: the result is "Not Found".
3. Log in as viewer_demo. Only salary-letter.txt is listed, and it cannot be edited.
4. Log in as admin_demo. Open Activity: allowed and refused attempts are listed. Click "Verify audit chain".
5. As owner_demo, use Share to give viewer2_demo access, then Revoke. Access stops on viewer2_demo's next click.

## Run it on your machine

Needs Python 3.12 or newer and Git.

```
git clone https://github.com/pharika986/trustvault.git
cd trustvault
python -m venv venv
```

Activate the environment (use one line):

- Windows Git Bash: `source venv/Scripts/activate`
- Mac / Linux: `source venv/bin/activate`
- Windows Command Prompt: `venv\Scripts\activate`
- Windows PowerShell: `venv\Scripts\Activate.ps1`

```
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in with the demo logins above. Keep the terminal running (do not close it or press Ctrl+C). "Connection refused" means the server is not running.

Locally the app uses SQLite (`db.sqlite3`) and stores uploads in `private_files/`. DEBUG is on by default locally and off on the live site.

## Run the tests

```
python manage.py test
```

Expected: `Ran 15 tests` and `OK`.

## Permission model

- **Owner:** uploads documents, grants "read" or "edit" to named users, revokes, deletes (soft delete). Always has access to own documents.
- **Viewer:** can only open documents an owner has shared with them (read, or read plus edit).
- **Admin:** sees the Activity log and manages users. Has no automatic access to document contents.

Every document route calls `can_access()` (`vault/permissions.py`), which reads the database on every request. Refused requests return 404, so the existence of a document is not revealed.

## Routes (who may call each)

| Route | Method | Who |
|---|---|---|
| /accounts/login/ | GET, POST | anyone |
| /accounts/logout/ | POST | logged-in user |
| / | GET | logged-in user (own and shared documents only; admin is sent to Activity) |
| /upload/ | GET, POST | owner role only |
| /docs/&lt;id&gt;/download/ | GET | owner of the document, or a user granted read |
| /docs/&lt;id&gt;/edit/ | GET, POST | owner, or a user granted edit |
| /docs/&lt;id&gt;/delete/ | POST | owner of the document only |
| /docs/&lt;id&gt;/share/ | GET, POST | owner of the document only |
| /docs/&lt;id&gt;/revoke/&lt;user_id&gt;/ | POST | owner of the document only |
| /admin-activity/ | GET | admin role only (audit log, chain check) |
| /admin/ | GET, POST | Django admin, users only (admin_demo) |

Everything except the login page redirects to login when not logged in. A forbidden or non-existent document returns 404 and is logged as "denied".

## Audit log

Each row stores who, action, document, allowed or denied, detail and IP, plus the hash of the previous row. "Verify audit chain" recomputes the chain and names the first row that was altered. Limit: deleting the newest rows is not detected.

## Files to read

- `vault/permissions.py` - the single authorisation function
- `vault/views.py` - every page and action (`get_doc_or_404` is the checkpoint)
- `vault/audit.py` - audit log writer and chain check
- `vault/models.py` - tables
- `vault/tests.py` - 15 tests
- `THREATS.md` - threats, what I did, what I accepted
- `PROMPTS.md` - how AI was used and where it was wrong

## Not finished / known limits

- No login lockout or rate limit (brute force possible).
- No self-registration, password reset, versions, restore of deleted documents, or sharing with people outside the system.
- Audit "append-only" is enforced in Python; there is no database-level INSERT-only permission. Deleting the newest log rows is not detected.
- Failed logins are not written to the audit log.
- admin_demo is a Django superuser: it cannot open documents but could reset another user's password in /admin/.
- Free hosting wipes data and uploads on redeploy.
- Tests do not cover the upload size limit, role_denied logging, or revoke by a non-owner.

See THREATS.md for the full list.

## Tech

Python, Django, SQLite (local and live), gunicorn, WhiteNoise, Argon2 password hashing, deployed on Render (free plan).
