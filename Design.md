# TrustVault design

## Roles (global)
- Admin: manages users, sees audit log and activity.
  Admin can NOT read document contents unless granted like anyone else.
- Owner: uploads documents, grants and revokes access to their own documents.
- Viewer: can only open documents shared with them.

## Document permissions
- Default is deny.
- Document owner: read, edit, delete, share.
- Grant "read": see details and download.
- Grant "edit": read + replace file and change details.
- Delete and sharing: document owner only.
- One function, can(user, document, action), in vault/permissions.py.
  Every view and every list calls it. Nothing else decides access.

## Files
- Stored in the database, not in a public folder.
- Only reachable through a view that checks can() first.

## Revoking access
- Permissions are checked in the database on every request.
- No cached permissions, no long-lived download links.
- Revoke takes effect on the very next request.

## Audit trail
- Append-only table: who, what, which document, result (allowed/denied), time.
- Refused attempts are logged too.
- Each row stores a hash of the previous row, so edits or deletions are detectable.
