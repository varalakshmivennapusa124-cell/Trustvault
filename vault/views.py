from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .audit import log
from .models import Document
from .permissions import can

MAX_SIZE = 5 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "text/plain"}


@login_required
def document_list(request):
    docs = Document.objects.filter(
        Q(owner=request.user) | Q(grants__user=request.user)
    ).distinct().order_by("-created_at")
    return render(request, "vault/list.html", {"docs": docs})


@login_required
@require_http_methods(["GET", "POST"])
def upload(request):
    if request.user.role not in ("owner", "admin"):
        log(request.user, "upload", outcome="denied", detail="role not allowed")
        return HttpResponse("Only owners can upload.", status=403)
    error = ""
    if request.method == "POST":
        f = request.FILES.get("file")
        if f is None:
            error = "Choose a file."
        elif f.size > MAX_SIZE:
            error = "File too large (max 5 MB)."
        elif f.content_type not in ALLOWED_TYPES:
            error = "Only PDF, PNG, JPG or TXT allowed."
        if error:
            log(request.user, "upload", outcome="denied", detail=error)
        else:
            doc = Document.objects.create(
                owner=request.user,
                name=f.name,
                category=request.POST.get("category", "")[:100],
                content_type=f.content_type,
                size=f.size,
                data=f.read(),
            )
            log(request.user, "upload", doc)
            return redirect("document_list")
    return render(request, "vault/upload.html", {"error": error})


@login_required
def download(request, doc_id):
    doc = Document.objects.filter(pk=doc_id).first()
    if doc is None or not can(request.user, doc, "read"):
        log(request.user, "download", doc, "denied", f"doc_id={doc_id}")
        raise Http404
    log(request.user, "download", doc)
    response = HttpResponse(bytes(doc.data), content_type=doc.content_type)
    response["Content-Disposition"] = f'attachment; filename="{doc.name}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response