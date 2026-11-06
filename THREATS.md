# \# THREATS.md: TrustVault

# 

# Each entry: how I think it could be broken, what I did, status (Closed / Mitigated / Accepted / Open), and the test that covers it. Test names refer to `vault/tests.py` (24 tests).

# 

# \## Design facts the rest depends on

# \- One decision point: `can(user, document, action)` in `vault/permissions.py`. Default is deny.

# \- Not allowed = HTTP 404 (same answer as "does not exist"), so a stranger cannot learn that a document exists.

# \- Files live in the database, never on disk or a static folder, so there is no path to guess.

# \- No share links or tokens are issued. Access = a `Grant` row (or being the owner), checked in the database on every request.

# \- Audit log is hash-chained. Refused attempts are logged.

# 

# \## A. Authorisation

# | # | Threat | What I did | Status |

# |---|---|---|---|

# | A1 | Button hidden but route open | Every view (download, edit, delete, share) calls `can()` on the server. Tests: `test\_stranger\_cannot\_edit\_delete\_or\_share`, `test\_other\_owner\_cannot\_download` | Closed |

# | A2 | Guessing document IDs (IDOR) | Forbidden and missing both return 404. Tests: `test\_viewer\_without\_grant\_cannot\_download` | Closed |

# | A3 | Admin as all-seeing superuser | Admin has no read power over documents unless granted like anyone else. Test: `test\_admin\_has\_no\_special\_read\_access`. Cost: admin cannot recover someone else's file | Closed (design choice) |

# | A4 | Back doors | Django `/admin/` route removed. No media/static serving of files. Only the listed views exist | Closed |

# | A5 | List/search leaking other people's documents | Queries start from the set the user may see, then filter. Test: `test\_list\_and\_search\_do\_not\_leak` | Closed |

# | A6 | Privilege escalation through grants | Only the owner can share or delete. "edit" grant cannot share/delete, "read" cannot edit. Tests: `test\_read\_grant\_reads\_but\_cannot\_change`, `test\_edit\_grant\_cannot\_share\_or\_delete`, `test\_read\_grant\_only\_reads` | Closed |

# | A7 | Changing own role | Role is stored server side. No endpoint changes roles and there is no self-registration | Closed |

# | A8 | State change by GET / CSRF | Delete is POST only (GET gets 405). Django CSRF middleware on. Test: `test\_delete\_requires\_post` | Closed |

# | A9 | Deactivated or anonymous users | `can()` denies them. Tests: `test\_anonymous\_and\_inactive\_denied`, `test\_anonymous\_is\_sent\_to\_login` | Closed |

# | A10 | Viewer uploading | Role check, 403, logged. Test: `test\_viewer\_cannot\_upload` | Closed |

# | A11 | Activity page open to non-admins | 404 for others. Test: `test\_only\_admin\_sees\_activity` | Closed |

# 

# \## B. Taking access away

# | # | Threat | What I did | Status |

# |---|---|---|---|

# | B1 | Revoked user keeps access | Revoke deletes the `Grant` row. No cache, no tokens or links ever issued. Test: `test\_revoke\_takes\_effect\_immediately` (download 200 -> revoke -> 404, and list is empty) | Closed |

# | B2 | Old session still works | A session only proves identity. Access is decided from the database on each request | Closed |

# | B3 | Copy already downloaded | Cannot be recalled by any system. A request already in flight when revoke happens completes | Accepted (inherent) |

# | B4 | Browser cache keeps a downloaded file | Responses are not marked `Cache-Control: no-store` | Open (low) |

# 

# \## C. Audit trail

# | # | Threat | What I did | Status |

# |---|---|---|---|

# | C1 | Refused attempts not recorded | Denied download/edit/delete/share/upload are logged. Download and delete log before acting, so a logging failure blocks the action. Tests: `test\_refused\_attempts\_are\_recorded`, `test\_successful\_actions\_are\_recorded` | Closed |

# | C2 | Quietly editing an entry | Each entry stores the hash of the previous one. Model refuses save/delete after creation. The admin Activity page shows "chain intact / broken at #n". Tests: `test\_chain\_detects\_edit`, `test\_entries\_cannot\_be\_changed\_or\_deleted\_via\_model` | Mitigated |

# | C3 | Deleting an entry in the middle | Detected by `verify\_chain`. Test: `test\_chain\_detects\_removed\_entry` | Mitigated |

# | C4 | Deleting the newest entries (truncating the tail) | NOT detected. There is no external anchor for the latest hash. Idea: publish the head hash somewhere write-once | Open |

# | C5 | Someone with direct database write access recomputes the whole chain | NOT prevented. The chain is tamper-evidence against casual edits, not against the database owner. Real fix: append-only DB role or an external write-once log | Accepted |

# | C6 | Flooding the log with denied requests | No rate limit | Accepted |

# | C7 | Deleting a document erases its history | Audit rows keep document id and name with no foreign key, so history survives deletion | Closed |

# | C8 | Activity page verifies the whole chain on every view | Fine at this size, would not scale | Accepted |

# 

# \## D. Authentication and sessions

# | # | Threat | What I did | Status |

# |---|---|---|---|

# | D1 | Password guessing | No rate limiting or lockout. Django password validators and PBKDF2 hashing only. Idea: django-axes | Open |

# | D2 | Judge credentials are public | The README lists one account per role as required. The data is demo data only. I will change them after evaluation | Accepted |

# | D3 | Cookies and transport | On Render: HTTPS redirect, Secure cookies, HttpOnly (default), session rotated on login. HSTS only 1 hour on purpose | Mitigated |

# | D4 | Secrets in the repository | `SECRET\_KEY` and seed passwords come from environment variables. The Django-generated development key is still in the git history and is used only when running locally | Accepted (low) |

# 

# \## E. Uploads and downloads

# | # | Threat | What I did | Status |

# |---|---|---|---|

# | E1 | Oversized upload | 5 MB limit checked on the server, but after the body is received | Mitigated |

# | E2 | Wrong file type | Allow-list of 4 types, but the type is declared by the client and I do not check magic bytes. Files are always sent as attachments with `X-Content-Type-Options: nosniff`, never shown inline. Test: `test\_upload\_rules` | Mitigated, Open (low) |

# | E3 | Hostile filename | Rename input is stripped to safe characters. The upload filename is not escaped inside `Content-Disposition` | Open (low) |

# | E4 | Stored XSS | Templates auto-escape. Nothing is rendered inline | Closed |

# | E5 | Path traversal | Not applicable, files are not on the file system | Closed |

# | E6 | Malware in uploads | No scanning | Accepted |

# 

# \## F. Infrastructure

# \- Production has `DEBUG` off, `ALLOWED\_HOSTS` limited to the Render host. SQL goes through the ORM. No CSP header (no scripts in the pages): Accepted.

# \- Files are not encrypted at application level: Accepted.

# \- Free tier: cold start of about a minute, and the free database expires after 30 days. This affects availability only.

# 

# \## Check-removal drill (6 Nov 2026)

# I removed the read check from the download view and ran the suite: FAILED (failures=5): `test\_admin\_has\_no\_special\_read\_access`, `test\_other\_owner\_cannot\_download`, `test\_revoke\_takes\_effect\_immediately`, `test\_viewer\_without\_grant\_cannot\_download`, `test\_refused\_attempts\_are\_recorded`. I restored the check and all 24 tests passed.

# 

# \## Deliberately not built

# External sharing, versions, retention and recovery, groups and folders, AI suggestions, 2FA, login rate limiting. A smaller system with a permission model that holds seemed better than a larger one with a hole in it.

