from .models import SiteAsset, SiteText


class TemplateMap(dict):
    def __getattr__(self, key):
        return self.get(key, "")


def site_content(request):
    copy = TemplateMap(SiteText.objects.values_list("key", "value"))
    assets = TemplateMap({item.key: item.url for item in SiteAsset.objects.all()})
    origin = request.build_absolute_uri("/").rstrip("/")
    return {
        "copy": copy,
        "assets": assets,
        "canonical_url": request.build_absolute_uri(request.path),
        "og_image_url": origin + "/static/studio/img/og-cover.png",
    }
