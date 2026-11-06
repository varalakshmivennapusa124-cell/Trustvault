from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .audit import log
from .models import Document
from .permissions import can


def _clean(name):
    return "".join(c for c in name if c.isalnum() or c in " ._-()")[:255]


@login_required
@require_POST
def delete(request, doc_id):
    doc = Document.objects.filter(pk=doc_id).first()
    if doc is None or not can(request.user, doc, "delete"):
        log(request.user, "delete", doc, "denied", f"doc_id={doc_id}")
        raise Http404
    log(request.user, "delete", doc)
    doc.delete()
    return redirect("document_list")


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, doc_id):
    doc = Document.objects.filter(pk=doc_id).first()
    if doc is None or not can(request.user, doc, "edit"):
        log(request.user, "edit", doc, "denied", f"doc_id={doc_id}")
        raise Http404
    if request.method == "POST":
        old = f"{doc.name}|{doc.category}"
        doc.name = _clean(request.POST.get("name", "")) or doc.name
        doc.category = request.POST.get("category", "")[:100]
        doc.save()
        log(request.user, "edit", doc, detail=f"was {old}")
        return redirect("document_list")
    return render(request, "vault/edit.html", {"doc": doc})