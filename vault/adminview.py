from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from .audit import log, verify_chain
from .models import AuditEntry


@login_required
def activity(request):
    if request.user.role != "admin":
        log(request.user, "admin_view", outcome="denied", detail="not admin")
        raise Http404
    entries = AuditEntry.objects.order_by("-id")
    outcome = request.GET.get("outcome", "")
    if outcome in ("allowed", "denied"):
        entries = entries.filter(outcome=outcome)
    page = Paginator(entries, 50).get_page(request.GET.get("page"))
    ok, bad_id = verify_chain()
    return render(request, "vault/activity.html", {
        "page": page, "chain_ok": ok, "bad_id": bad_id, "outcome": outcome,
    })