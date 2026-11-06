from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import Document


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@login_required
def document_list(request):
    # Start ONLY from documents this user may see, then narrow down.
    docs = Document.objects.filter(
        Q(owner=request.user) | Q(grants__user=request.user)
    ).distinct()
    q = request.GET.get("q", "").strip()
    owner = request.GET.get("owner", "").strip()
    category = request.GET.get("category", "").strip()
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if q:
        docs = docs.filter(name__icontains=q)
    if owner:
        docs = docs.filter(owner__username__icontains=owner)
    if category:
        docs = docs.filter(category__icontains=category)
    if date_from:
        docs = docs.filter(created_at__date__gte=date_from)
    if date_to:
        docs = docs.filter(created_at__date__lte=date_to)
    return render(request, "vault/list.html", {
        "docs": docs.order_by("-created_at"),
        "q": q, "owner": owner, "category": category,
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
    })