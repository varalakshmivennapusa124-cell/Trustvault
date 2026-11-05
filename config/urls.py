from django.contrib import admin
from django.urls import include, path

from vault import sharing, views

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("upload/", views.upload, name="upload"),
    path("documents/<int:doc_id>/download/", views.download, name="download"),
    path("documents/<int:doc_id>/share/", sharing.share, name="share"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
]