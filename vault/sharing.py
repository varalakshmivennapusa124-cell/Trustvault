from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .audit import log
from .models import Document, Grant
from .permissions import can


@login_required
@require_http_methods(["GET", "POST"])
def share(request, doc_id):
    doc = Document.objects.filter(pk=doc_id).first()
    if doc is None or not can(request.user, doc, "share"):
        log(request.user, "share", doc, "denied", f"doc_id={doc_id}")
        raise Http404
    User = get_user_model()
    message = ""
    if request.method == "POST":
        action = request.POST.get("action")
        target = User.objects.filter(username=request.POST.get("username", "")).first()
        level = request.POST.get("level", "read")
        if target is None or target.id == doc.owner_id:
            message = "Choose a different, existing user."
        elif action == "grant" and level in ("read", "edit"):
            Grant.objects.update_or_create(
                document=doc,
                user=target,
                defaults={"level": level, "granted_by": request.user},
            )
            log(request.user, "grant", doc, detail=f"{target.username}:{level}")
            message = f"Granted {level} to {target.username}."
        elif action == "revoke":
            deleted, _ = Grant.objects.filter(document=doc, user=target).delete()
            log(request.user, "revoke", doc, detail=target.username)
            message = f"Revoked access for {target.username}." if deleted else "No grant existed."
    grants = doc.grants.select_related("user")
    return render(
        request, "vault/share.html", {"doc": doc, "grants": grants, "message": message}
    )