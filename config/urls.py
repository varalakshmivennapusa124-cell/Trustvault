from django.urls import include, path

from vault import adminview, editing, listing, sharing, views

urlpatterns = [
    path("", listing.document_list, name="document_list"),
    path("upload/", views.upload, name="upload"),
    path("activity/", adminview.activity, name="activity"),
    path("documents/<int:doc_id>/download/", views.download, name="download"),
    path("documents/<int:doc_id>/share/", sharing.share, name="share"),
    path("documents/<int:doc_id>/edit/", editing.edit, name="edit"),
    path("documents/<int:doc_id>/delete/", editing.delete, name="delete"),
    path("accounts/", include("django.contrib.auth.urls")),
]