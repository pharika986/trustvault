TRUSTVAULT - secure document sharing with an audit trail
=========================================================

WHAT IT IS
A Django web app. A document can be opened only by people the owner granted
access to. Access can be taken back and it stops working on the very next
request. Every action, including refused attempts, is written to an audit log
that is chained with hashes so that changes to old rows can be detected.

LIVE SITE (no setup needed)
  https://trustvault-pharika986.onrender.com/accounts/login/
  Free hosting: it sleeps when idle, so the first page can take about a minute.
  Uploaded files and data reset on each redeploy; the demo accounts and two
  sample files are re-created automatically.

DEMO LOGINS
  Role     Username        Password
  Owner    owner_demo      Owner#Demo2026
  Viewer   viewer_demo     Viewer#Demo2026     (has salary-letter.txt shared)
  Viewer   viewer2_demo    Viewer2#Demo2026    (nothing shared)
  Admin    admin_demo      Admin#Demo2026

WHAT TO TRY (about 3 minutes)
  1. Log in as owner_demo. You see two documents. Download one.
  2. In a private window, log in as viewer2_demo. The list is empty.
     Paste the owner's download link: the result is "Not Found".
  3. Log in as viewer_demo. Only salary-letter.txt is listed.
  4. Log in as admin_demo, open Activity: refused attempts are listed.
     Click "Verify audit chain".
  5. As owner_demo, use Share to give viewer2_demo access, then Revoke.
     The access stops on viewer2_demo's next click.

RUN IT ON YOUR MACHINE
Needs Python 3.12 or newer and Git.

  git clone https://github.com/pharika986/trustvault.git
  cd trustvault
  python -m venv venv

  Activate the environment (pick the line for your shell):
    Git Bash / Mac / Linux :  source venv/Scripts/activate     (Windows Git Bash)
                              source venv/bin/activate         (Mac / Linux)
    Command Prompt         :  venv\Scripts\activate
    PowerShell             :  venv\Scripts\Activate.ps1

  pip install -r requirements.txt
  python manage.py migrate
  python manage.py seed
  python manage.py runserver

Open http://127.0.0.1:8000/ and log in with the demo logins above.
Keep the terminal running (do not close it or press Ctrl+C). If the browser
says "connection refused", the server is not running.

Locally the app uses SQLite (db.sqlite3) and stores uploads in private_files/.
DEBUG is on by default locally. On the live site it is off.

RUN THE TESTS
  python manage.py test
Expected: "Ran 14 tests" and "OK".

THE PERMISSION MODEL (in short)
  Owner : uploads documents, grants "read" or "edit" to named users, revokes,
          deletes (soft delete). Always has access to own documents.
  Viewer: can only open documents an owner has shared with them
          (read, or read plus edit).
  Admin : manages users and sees the activity log and permission changes.
          Has NO automatic access to document contents.
  Every document route calls can_access() (vault/permissions.py), which reads
  the database on every request. Refused requests return 404 so that the
  existence of a document is not revealed.

API / ROUTES (who is allowed to call each)
  Route                                   Method     Who
  /accounts/login/                        GET, POST  anyone
  /accounts/logout/                       POST       logged-in user
  /                                       GET        logged-in user (own and shared documents only)
  /upload/                                GET, POST  owner role only
  /docs/<id>/download/                    GET        owner of the document, or a user granted read
  /docs/<id>/edit/                        GET, POST  owner, or a user granted edit
  /docs/<id>/delete/                      POST       owner of the document only
  /docs/<id>/share/                       GET, POST  owner of the document only
  /docs/<id>/revoke/<user_id>/            POST       owner of the document only
  /admin-activity/                        GET        admin role only (audit log, chain check)
  /admin/                                 GET, POST  Django admin (admin_demo only; users only)
  Everything except the login page redirects to login when not logged in.
  A forbidden or non-existent document returns 404 and is logged as "denied".

AUDIT LOG
  Each row stores who, action, document, allowed or denied, detail and IP, plus
  the hash of the previous row. "Verify audit chain" on the Activity page
  recomputes the chain and names the first row that was altered.
  Limit: deleting the newest rows is not detected.

FILES TO READ
  vault/permissions.py    the single authorisation function
  vault/views.py          every page and action (get_doc_or_404 is the checkpoint)
  vault/audit.py          audit log writer and chain check
  vault/models.py         tables
  vault/tests.py          14 tests
  THREATS.md              threats, what I did, what I accepted
  PROMPTS.md              how AI was used and where it was wrong
  PROJECT_GUIDE.md        full code-flow walkthrough

NOT FINISHED / KNOWN LIMITS
  - No login lockout or rate limit (brute force possible).
  - No self-registration, password reset, versions, restore of deleted
    documents, or sharing with people outside the system.
  - Audit "append-only" is enforced in Python; there is no database-level
    INSERT-only permission. Deleting the newest log rows is not detected.
  - Failed logins are not written to the audit log.
  - admin_demo is a Django superuser: it cannot open documents but could reset
    another user's password in /admin/.
  - The document list shows an Edit link to read-only viewers; the server
    refuses it with 404.
  - Free hosting wipes data and uploads on redeploy.
  - Tests do not cover the upload size limit, role_denied logging, or revoke
    by a non-owner.
  See THREATS.md for the full list.

TECH
  Python, Django, SQLite (local and live), gunicorn, WhiteNoise, Argon2
  password hashing, deployed on Render (free plan).
