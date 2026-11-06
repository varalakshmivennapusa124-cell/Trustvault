from django.contrib.auth import views as auth_views
from django.urls import path

from vault import adminview, editing, listing, sharing, views

urlpatterns = [
    path("", listing.document_list, name="document_list"),
    path("upload/", views.upload, name="upload"),
    path("activity/", adminview.activity, name="activity"),
    path("documents/<int:doc_id>/download/", views.download, name="download"),
    path("documents/<int:doc_id>/share/", sharing.share, name="share"),
    path("documents/<int:doc_id>/edit/", editing.edit, name="edit"),
    path("documents/<int:doc_id>/delete/", editing.delete, name="delete"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
]