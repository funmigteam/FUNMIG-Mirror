from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from apps.core.views import git_repositories, git_repository_download, guide, guides, home, mirror_detail, mirrors
from apps.npm_mirror.views import npm_artifact, npm_metadata, npm_root

urlpatterns = [path("", home, name="home"), path("guides/", guides, name="guides"), path("guides/<str:category>/<slug:slug>/", guide, name="guide"), path("mirrors/", mirrors, name="mirrors"), path("mirrors/<slug:slug>/", mirror_detail, name="mirror-detail"), path("repositories/", git_repositories, name="git-repositories"), path("repositories/download/<str:filename>/", git_repository_download, name="git-repository-download"), path("admin/", admin.site.urls), path("pypi", lambda request: redirect("/pypi/")), path("pypi/", include("apps.pypi_mirror.urls")), path("npm/", npm_root, name="npm-root"), path("npm/<path:name>", npm_metadata, name="npm-metadata"), path("npm-artifacts/<str:encoded_name>/<str:version>/package.tgz", npm_artifact, name="npm-artifact")]
