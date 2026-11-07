# PROMPTS.md



Tool used: Claude (chat). I am new to Django, so I used Claude as a step-by-step guide. I dictated my questions in Telugu, pasted the problem statement and the rules at the start, and sent photos of my screen and errors. Below is where it was wrong and what I did about it. Commit links: https://github.com/varalakshmivennapusa124-cell/Trustvault/commit/<hash>



## Entry 1: 2026-11-01: .gitignore did not ignore caches

- **Asked:** set up a private repo and a Django project, with a .gitignore for venv, database, .env and caches.

- **Produced:** `echo` commands that wrote .gitignore, followed by `git add .` and a push.

- **Wrong:** the pattern for `__pycache__` did not work. The first real commit pushed 31 files including `.pyc` files. I saw them in the `create mode ...pycache...` lines of the commit output.

- **Did:** rewrote .gitignore with a Python one-liner, ran `git rm -r --cached .`, added again, committed, and checked with `git ls-files` that no `.pyc`, `db.sqlite3` or `venv` was tracked. Commit: `<33c0632>` ("Stop tracking pycache and local database").



## Entry 2: 2026-11-04: the "admin" account was only a viewer (access control)

- **Asked:** a custom user model with three roles (admin, owner, viewer) and a way to create an admin for testing.

- **Produced:** a `role` field defaulting to "viewer", and `createsuperuser` as the way to make the admin.

- **Wrong:** the account made by `createsuperuser` got the default role "viewer". The page said "Hello admin, role: viewer". There were two different meanings of "admin" (Django's `is_superuser` and my `role`), and the role checks would have refused the real admin.

- **Did:** fixed the role in the database by hand, then wrote a `seed` management command that sets `role`, `is_staff` and `is_superuser` together, with passwords read from environment variables, so deployed accounts are consistent. Commit: `9b25d6b`.



## Entry 3: 2026-11-04: refused attempts were not recorded (audit trail)

- **Asked:** a download view that only serves a document if the user may read it, and then the audit trail required by the problem statement.

- **Produced:** a first download view that used `get_object_or_404` and then `if not can(...): raise Http404`, and an upload view that returned 403 for viewers. Neither wrote anything to a log.

- **Wrong:** the problem statement says the record must include refused attempts. The first version recorded nothing, and `get_object_or_404` also meant that a request for a non-existent id left no trace. When we reached the audit step Claude itself admitted its first version broke this rule.

- **Did:** replaced it with `Document.objects.filter(pk=...).first()`, so a missing document and a forbidden document are handled and logged the same way ("denied"), and added a hash-chained `AuditEntry`. I checked by listing the entries (`viewer1 download denied`, `admin download allowed`) and `verify_chain()` returned `(True, None)`. Test: `test_refused_attempts_are_recorded`. Commit: `c5dec2d`.



## Entry 4: 2026-11-05: a Windows shell command silently did not update urls.py

- **Asked:** add the share route to `config/urls.py`.

- **Produced:** a one-line `python -c "open('config/urls.py','w').write(...)"` containing `<int:doc_id>`.

- **Wrong:** Windows cmd treats `<` as input redirection. The command printed "The system cannot find the file specified" and **urls.py was not changed**. If I had not read the output, I would have believed the share page existed.

- **Did:** edited the file in Notepad, checked the first line with `repr(open(...).readline())` (an earlier paste had left a leading space, which gave an IndentationError), started the server and opened `/documents/1/share/`. Grant and revoke were then tested by hand with a second user. Commit: `7d875cb`.



## Entry 5: 2026-11-06: Django's /admin/ route was left in (access control)

- **Asked:** wire up all routes for the app.

- **Produced:** `urls.py` that kept the scaffold's `path("admin/", admin.site.urls)` in every version it gave me.

- **Wrong:** my design has its own admin Activity page, and nothing uses Django's admin. It was an extra login and management surface nobody had reviewed. Its bulk "delete selected" bypasses the model-level append-only guard of the audit table if that table were ever registered there.

- **Did:** removed the route in the commit that added search, the activity page, edit and delete, and recorded it in THREATS.md (A4). All 24 tests were re-run. Commit: `<8731f6d >`.



## Evidence that the tests test something: 2026-11-06

After writing the 24 tests, I removed the read check from the download view (`doc is None or not can(request.user, doc, "read")` became `doc is None`) and ran the suite: **FAILED (failures=5)**: `test_admin_has_no_special_read_access`, `test_other_owner_cannot_download`, `test_revoke_takes_effect_immediately`, `test_viewer_without_grant_cannot_download`, `test_refused_attempts_are_recorded`. I restored the line with `git checkout -- vault/views.py` and all 24 passed again.



## Instructions and context I reused across the week

- At the start I pasted the problem statement, the instruction page and the grounds for rejection, and asked Claude to keep all rules in mind and guide me from start to end.

- Standing rules we followed: one `can()` function decides access, default deny; a forbidden document answers 404; log refused attempts as well as allowed ones; commit after every small feature; explain each security-relevant line so I can answer in the interview; give exact Windows cmd commands and tell me what output to expect.

- I sent screenshots of every error instead of describing it, which is how most of the mistakes above were found.

- Everything is my own submission: Claude was my only helper, and I am able to explain the code.
