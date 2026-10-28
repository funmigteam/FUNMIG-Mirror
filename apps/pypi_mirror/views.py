from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from .models import RemoteFile
from .services import UpstreamUnavailable, cache_remote_file, normalize_name, refresh_metadata, touch

@require_GET
def landing(request):
    packages = RemoteFile.objects.values_list("package_version__package__display_name", flat=True).distinct().order_by("package_version__package__display_name")
    return render(request, "pypi_mirror/landing.html", {"packages": packages, "count": packages.count(), "domain": settings.MIRROR_DOMAIN})

@require_GET
def simple_root(request):
    return HttpResponse("<html><body><h1>Funmig PyPI mirror</h1></body></html>", content_type="text/html")

@require_GET
def simple_package(request, name):
    normalized = normalize_name(name)
    files = RemoteFile.objects.filter(package_version__package__registry="pypi", package_version__package__normalized_name=normalized).select_related("package_version")
    if not files.exists():
        try: refresh_metadata(name)
        except UpstreamUnavailable:
            return JsonResponse({"detail": "Package is not available in the local mirror and PyPI is unavailable."}, status=503)
        files = RemoteFile.objects.filter(package_version__package__registry="pypi", package_version__package__normalized_name=normalized)
    anchors = []
    for item in files:
        url = reverse("pypi-artifact", args=[item.id])
        anchors.append(f'<a href="{url}#sha256={item.sha256}"' + (f' data-requires-python="{item.requires_python}"' if item.requires_python else "") + f'>{item.filename}</a>')
    return HttpResponse("<!doctype html><html><body>" + "\n".join(anchors) + "</body></html>", content_type="text/html")

@require_GET
def artifact(request, file_id):
    try: remote = RemoteFile.objects.select_related("artifact__blob").get(pk=file_id)
    except RemoteFile.DoesNotExist: raise Http404
    try: cached = cache_remote_file(remote)
    except UpstreamUnavailable:
        return JsonResponse({"detail": "Artifact is not cached and PyPI is unavailable."}, status=503)
    touch(cached)
    response = HttpResponse()
    response["X-Accel-Redirect"] = "/_mirror_blobs/" + cached.blob.relative_path
    response["Content-Disposition"] = f'attachment; filename="{cached.filename}"'
    response["Content-Type"] = "application/octet-stream"
    return response
