from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import include, path


@login_required
def home(request):
    return HttpResponse(f"Hello {request.user.username}, role: {request.user.role}")


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
]