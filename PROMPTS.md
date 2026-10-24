# PROMPTS.md

AI tool used: Claude (chat). It planned the design and wrote the first version of the Django code, templates and tests. I ran everything myself, found the problems below, and fixed them.

## My prompts (quoted from the conversation)

1. 21 Oct 2026, after attaching the assignment screenshots:
   > How to do this assignment, do n't know how to do this. which source is suitable?
2. 21 Oct 2026:
   > for above given scren shots,which language is best to develop this?
3. 21 Oct 2026:
   > just give me the implementing steps..because i dont have that much time to learn..my only target is to complete that assignment with in a given deadline..so help me to do..early and fast..so just give the step by step process..i will follow

Claude recommended Python with Django. Its first answer was a step-by-step plan, and after prompt 3 it gave the full code (models, permission check, audit log, views, templates, seed command, tests) to paste in.

## Entries

### Entry 1 - 21 Oct 2026 - Audit trail: empty `audit.py` passed my check
- **Asked:** Claude to create `vault/permissions.py` and `vault/audit.py` (the hash-chained audit log).
- **Produced:** correct code. But VS Code created my first copies inside `vault/migrations/`, and the `audit.py` I later made in `vault/` was empty.
- **What was wrong:** the syntax check Claude suggested (`ast.parse`) printed "both OK" on an empty file. When I ran `python manage.py check`, it failed with `ImportError: cannot import name 'log' from 'vault.audit'`.
- **What I did:** rewrote the file from the terminal with the full code, reran `manage.py check` (no issues), and committed. Commit `5c9b848`.
- **Lesson:** a syntax check does not show that the functions exist. The audit log is the evidence trail, so I now check that the import works.

### Entry 2 - 21 Oct 2026 - Database and cache files committed to Git
- **Asked:** Claude for the steps to commit my progress.
- **Produced:** a `.gitignore` step that came at the end of the plan, after I had already committed.
- **What was wrong:** my first commit (`9fba027`) included `db.sqlite3` (the database, with users and password hashes) and the `__pycache__` files.
- **What I did:** created `.gitignore`, ran `git rm -r --cached` on those files, and committed. Commit `e3afc66`. I did not rewrite history. `db.sqlite3` still exists in the first commit's history, which is why the live site uses new secrets and re-seeds its demo accounts on each deploy.

### Entry 3 - 22 Oct 2026 - Wrong test count
- **Asked:** Claude for automated access-control tests.
- **Produced:** a test file. Claude said it contained 15 tests.
- **What was wrong:** I ran `python manage.py test` and it ran 14. Claude had miscounted.
- **What I did:** checked the file myself, and recorded 14 as the real number. All 14 pass.
- **Also done:** to check the tests really guard authorisation, I removed the `can_access` call from `get_doc_or_404`. The tests failed (`FAILED (failures=6)`, `AssertionError: 200 != 404`). I restored the file with `git checkout` and all 14 passed again.

### Entry 4 - 22 Oct 2026 - Render start command pasted wrongly
- **Asked:** Claude for the Render deployment settings.
- **What was wrong:** I pasted the start command next to Render's default text, giving `gunicorn app:appgunicorn config.wsgi`, which would not start. Claude spotted it in my screenshot.
- **What I did:** replaced it with `gunicorn config.wsgi`. The deploy succeeded. (No code commit, because this was a setting on Render.)

### Entry 5 - 22 Oct 2026 - Access control: Edit link shown to read-only viewers (NOT FIXED)
- **Asked:** Claude for the document list page.
- **Produced:** a template that shows the Edit link to everyone who can see a document.
- **What was wrong:** on the live site, `viewer_demo` (read-only) sees an Edit link. The server correctly refuses it with 404, and the tests cover that, but the page offers an action that will fail.
- **What I did:** nothing yet. The server-side check is correct, so this is a usability fault and not an access hole. It is listed as unfinished.

## Context and instructions I reused
- The assignment brief (security first: the server decides on every request, an audit trail that can't be quietly changed, access removal that works immediately).
- Design rule I gave myself: one central `can_access(user, doc, action)` function, called by every route, checking the database each time. Return 404 instead of 403. Admin sees activity but not document contents.
