from django.urls import path
from . import views
urlpatterns = [path("", views.landing, name="pypi-home"), path("simple/", views.simple_root), path("simple/<str:name>/", views.simple_package), path("packages/<int:file_id>/", views.artifact, name="pypi-artifact")]
