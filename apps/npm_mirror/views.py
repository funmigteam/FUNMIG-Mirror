import json
from pathlib import Path
from urllib.parse import quote, unquote

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET


def _encoded(name):
    return quote(unquote(name), safe="")


@require_GET
def npm_root(request):
    return JsonResponse({"name": "Funmig npm mirror", "mode": "prefetched-only"})


@require_GET
def npm_metadata(request, name):
    encoded = _encoded(name)
    metadata_path = settings.MIRROR_REPOSITORY_ROOT / "npm" / "metadata" / f"{encoded}.json"
    if not metadata_path.is_file():
        raise Http404
    document = json.loads(metadata_path.read_text(encoding="utf-8"))
    public_name = document["name"]
    for version, item in document.get("versions", {}).items():
        if "dist" in item:
            item["dist"]["tarball"] = f"https://{settings.MIRROR_DOMAIN}/npm-artifacts/{quote(public_name, safe='')}/{version}/package.tgz"
    return JsonResponse(document)


@require_GET
def npm_artifact(request, encoded_name, version):
    root = (settings.MIRROR_REPOSITORY_ROOT / "npm" / "packages").resolve()
    target = (root / encoded_name / version / "package.tgz").resolve()
    if root not in target.parents or not target.is_file():
        raise Http404
    return FileResponse(target.open("rb"), content_type="application/octet-stream")
