import hashlib

from django.db import transaction

from .models import AuditEntry


def _digest(prev_hash, e):
    parts = [
        prev_hash,
        e.created_at.isoformat(),
        str(e.actor_id or ""),
        e.actor_name,
        e.action,
        str(e.document_id or ""),
        e.document_name,
        e.outcome,
        e.detail,
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


@transaction.atomic
def log(user, action, document=None, outcome="allowed", detail=""):
    last = AuditEntry.objects.select_for_update().order_by("-id").first()
    prev_hash = last.entry_hash if last else "0" * 64
    entry = AuditEntry(
        actor=user if getattr(user, "is_authenticated", False) else None,
        actor_name=getattr(user, "username", "anonymous"),
        action=action,
        document_id=document.id if document else None,
        document_name=document.name if document else "",
        outcome=outcome,
        detail=detail[:500],
        prev_hash=prev_hash,
    )
    entry.entry_hash = _digest(prev_hash, entry)
    entry.save()
    return entry


def verify_chain():
    prev = "0" * 64
    for e in AuditEntry.objects.order_by("id"):
        if e.prev_hash != prev or e.entry_hash != _digest(prev, e):
            return False, e.id
        prev = e.entry_hash
    return True, None