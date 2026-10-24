# THREATS.md

How I think TrustVault could be broken, what I did about each, and what I knowingly accepted.
Status key: VERIFIED = I tried it on the running app or a test covers it. DESIGNED = built in, but I have not attacked it directly. ACCEPTED = a known weakness I chose not to fix.

Core rule: the server decides on every request. `can_access(user, doc, action)` in `vault/permissions.py` reads the database each time, and every document route goes through `get_doc_or_404` or `get_owned_doc_or_404`.

## A. Reaching documents without a grant

| # | Threat | What I did | Status |
|---|---|---|---|
| 1 | A logged-in stranger opens another user's download link (IDOR) | `get_doc_or_404` calls `can_access`; refused requests return 404 and write a denied audit row | VERIFIED: live site returned Not Found for viewer2_demo; test `test_stranger_cannot_reach_document_on_any_route` |
| 2 | Same attack on edit, delete, share | Same helper (`edit`) or `get_owned_doc_or_404` (`delete`, `share`, `revoke`) | VERIFIED: tests for each route; read-only viewer got 404 on the live edit URL |
| 3 | Guessing document ids | Ids are random UUIDs; 404 is returned for both "missing" and "forbidden" so existence is not revealed | DESIGNED |
| 4 | Not logged in | `@login_required` on every view; redirects to login | VERIFIED: `test_anonymous_is_sent_to_login` |
| 5 | Search results leaking names of documents the user cannot see | The list query starts from "owned or granted" before any search filter | VERIFIED: `test_search_does_not_leak_names` |
| 6 | Read-only user edits or deletes | `edit` needs `can_edit`; `delete`, `share`, `revoke` are owner only | VERIFIED: `test_read_only_cannot_edit_or_delete`, `test_edit_permission_allows_edit_but_not_delete` |
| 7 | Non-owner grants access to themselves or friends | `share` uses `get_owned_doc_or_404` | VERIFIED for share (`test_non_owner_cannot_grant`). No separate test for revoke by a non-owner (same helper). |
| 8 | Admin reads private documents | `can_access` never looks at role, so admin has no content access | VERIFIED: `test_admin_has_no_content_access` |
| 9 | Direct URL to the stored file | Files are saved in `private_files/` under random names. That folder is not under static or media, and no URL serves it. Downloads go only through the checked view | DESIGNED |
| 10 | Deleted document still reachable | Soft delete sets `is_deleted`; `can_access` returns False for everyone | DESIGNED (no dedicated test) |

## B. Taking access away

| # | Threat | What I did | Status |
|---|---|---|---|
| 11 | A revoked user keeps access through an old link or session | No permissions are cached in sessions or tokens. The Permission row is read on every request, so deleting it blocks the next request | VERIFIED: `test_revoke_takes_effect_immediately` |
| 12 | A removed user's session stays valid | Not handled: deactivating a user does not log out existing sessions on its own | ACCEPTED for now (see section F) |

## C. The audit trail

| # | Threat | What I did | Status |
|---|---|---|---|
| 13 | Refused attempts leave no record | Every refusal writes a `denied` row, including role refusals | VERIFIED: `test_denied_attempt_is_audited` |
| 14 | Someone edits an old audit row | Each row stores a SHA-256 hash that includes the previous row's hash. "Verify audit chain" (admin page) recomputes it and reports the first broken row | VERIFIED: `test_audit_tampering_is_detected` (uses `.update()`) |
| 15 | Someone edits or deletes a row through the model | `AuditLog.save()` raises on existing rows and `delete()` always raises. Django admin only registers `User` | VERIFIED: `test_audit_rows_cannot_be_modified` |
| 16 | Bulk update or raw SQL on the table | Bypasses the Python protection. The hash chain still detects changed rows | ACCEPTED: I did not add a database-level INSERT-only permission |
| 17 | Deleting the newest rows | The remaining chain is still consistent, so it is NOT detected | ACCEPTED. A fix would be to store the latest hash somewhere outside the database |
| 18 | Failed logins are not recorded | I did not hook login failures into the audit log | ACCEPTED, a real gap |
| 19 | Two requests writing at once break the chain | `log()` runs in `transaction.atomic` and locks the last row with `select_for_update` | DESIGNED. SQLite ignores row locks, so this protection is only real on a server database |
| 20 | Spoofed client IP | I take the last `X-Forwarded-For` entry (added by Render's proxy) | DESIGNED. The IP is only as trustworthy as the proxy |

## D. Uploads

| # | Threat | What I did | Status |
|---|---|---|---|
| 21 | A disguised file (an .exe renamed to .pdf) | Extension allowlist (pdf, png, jpg, docx, txt) plus a check that the first bytes match the type | VERIFIED: `test_fake_pdf_rejected` |
| 22 | Path traversal through the filename | Only the base name is kept for display; the file on disk is a random uuid name, never the user's name | DESIGNED. I have not tried a hostile filename |
| 23 | Oversized or empty upload | Rejected above 5 MB or at 0 bytes | DESIGNED. The check runs after the upload arrives, so the server still receives the file first. No test |
| 24 | A download that runs in the browser | Sent as an attachment with `X-Content-Type-Options: nosniff` | DESIGNED |
| 25 | Malware or macros inside a valid .docx | Not scanned | ACCEPTED |
| 26 | Viewers uploading | `@role_required("owner")` | VERIFIED: `test_viewer_cannot_upload` |

## E. Application and deployment

| # | Threat | What I did | Status |
|---|---|---|---|
| 27 | Debug page leaks code and settings | `DEBUG` comes from an environment variable and is `0` on the live site | VERIFIED: a plain Not Found page is shown for bad addresses |
| 28 | Cross-site request forgery | Django's CSRF middleware is on; every state-changing action is a POST with a token (delete, revoke, logout, share) | DESIGNED. Not attacked |
| 29 | Password theft | Passwords are stored as Argon2 hashes | DESIGNED |
| 30 | Cookie theft | HttpOnly and SameSite=Lax; Secure cookies when DEBUG is off | DESIGNED |
| 31 | Secrets in Git history | My first commit contained `db.sqlite3` and Django's original development `SECRET_KEY` (in settings.py). I removed the database from tracking (commit e3afc66) but did not rewrite history. The live site uses a new SECRET_KEY set on Render, and `seed` resets the demo passwords on each deploy | ACCEPTED: the old database is still in the first commit |

## F. Knowingly accepted or unfinished

- **Brute force on login:** there is no lockout or rate limit.
- **Public demo passwords:** they are in the README. The live data is demo data only.
- **Admin superuser:** `admin_demo` cannot open documents, but a superuser can reset another user's password in `/admin/` and then log in as them. This is a real hole in "admin cannot read content". A fix is to make the admin a staff user without password-reset rights.
- **Edit link shown to read-only viewers:** the page offers it and the server refuses it with 404. A usability fault, not an access hole.
- **Sessions after deactivation:** no forced logout.
- **No file recovery:** soft delete only; no restore screen, no versions, no external sharing, no retention policy.
- **Free hosting:** uploaded files and the SQLite database are wiped on every redeploy; `seed` recreates the demo accounts and sample files.
- **Test gaps:** no tests for the upload size limit, the `role_denied` log row, revoke by a non-owner, or deleted-document access.

## What I deliberately did not build
Self-registration, password reset, external (outside-company) sharing, groups or folder inheritance, versions, and recovery of deleted files. I kept one simple permission model (per-document grants to named users) so that it could be checked end to end.
