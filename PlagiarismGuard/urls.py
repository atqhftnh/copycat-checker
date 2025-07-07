from django.contrib import admin
from django.urls import include, path, re_path
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^', include('plag.urls')),
]