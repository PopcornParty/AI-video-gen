"""Find royalty-free images. Works with zero API keys via Wikimedia and Wikipedia."""
from __future__ import annotations
from pathlib import Path
from .config_loader import env
from .research import visual_lookups
from .utils import cache_path, download_file, extension_from_url, http_get, info, warn

def find_visuals_for_scenes(scenes, topic, cache_dir: Path, visuals_cfg):
    used_urls = set()
    used_paths = set()
    results = []
    extras = visual_lookups(topic)
    for scene in scenes:
        queries = list(scene.get("search_queries") or [])
        main = scene.get("search_query") or topic
        if main not in queries:
            queries.insert(0, main)
        for extra in extras:
            if extra not in queries:
                queries.append(extra)
        info(f"Visual search: {main}")
        asset = None
        for query in queries:
            asset = _search_image(query, cache_dir, used_urls, used_paths)
            if asset:
                break
        if asset is None:
            asset = _wikipedia_thumb(queries[0] if queries else topic, cache_dir, used_urls, used_paths)
        if asset is None:
            warn(f"No new media for '{main}', will use generated backdrop")
            asset = {"kind": "generated", "path": None, "query": main, "source": "generated", "attribution": ""}
        else:
            used_urls.add(asset.get("url") or "")
            if asset.get("path"):
                used_paths.add(asset["path"])
        out = dict(scene)
        out["visual"] = asset
        results.append(out)
    return results

def _search_image(query, cache_dir, used_urls, used_paths):
    for fn in (_wikimedia_images, _wikipedia_search_images, _pexels_photos, _pixabay_photos):
        try:
            hits = fn(query)
        except Exception as exc:
            warn(f"{fn.__name__} error: {exc}")
            hits = []
        asset = _download_first(hits, cache_dir, used_urls, used_paths)
        if asset:
            return asset
    return None

def _wikipedia_thumb(title, cache_dir, used_urls, used_paths):
    hits = _wikipedia_search_images(title)
    return _download_first(hits, cache_dir, used_urls, used_paths)

def _download_first(hits, cache_dir, used_urls, used_paths):
    for hit in hits:
        url = hit.get("url")
        if not url or url in used_urls:
            continue
        dest = cache_path(cache_dir, "visuals", url, extension_from_url(url, ".jpg"))
        if str(dest) in used_paths:
            continue
        if download_file(url, dest, headers=hit.get("headers")):
            return {
                "kind": "image",
                "path": str(dest),
                "url": url,
                "query": hit.get("query", ""),
                "source": hit.get("source", ""),
                "attribution": hit.get("attribution", ""),
            }
    return None

def _wikimedia_images(query):
    resp = http_get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": "16",
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "iiurlwidth": "1280",
            "format": "json",
        },
    )
    if resp is None:
        return []
    pages = resp.json().get("query", {}).get("pages", {})
    out = []
    skip = ("logo", "icon", "flag of", "coat of arms", "svg", "map of", "wordmark")
    for page in pages.values():
        title = (page.get("title") or "").lower()
        if any(s in title for s in skip):
            continue
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info_ = infos[0]
        mime = (info_.get("mime") or "").lower()
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        url = info_.get("thumburl") or info_.get("url")
        if not url:
            continue
        out.append({"url": url, "source": "wikimedia", "query": query, "attribution": f"{page.get('title', 'Wikimedia')} — Wikimedia Commons"})
    return out

def _wikipedia_search_images(query):
    resp = http_get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": "8",
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": "1280",
            "format": "json",
        },
    )
    if resp is None:
        return []
    pages = resp.json().get("query", {}).get("pages", {})
    out = []
    for page in pages.values():
        thumb = page.get("thumbnail") or {}
        url = thumb.get("source")
        if not url:
            continue
        out.append({"url": url, "source": "wikipedia", "query": query, "attribution": f"{page.get('title', 'Wikipedia')} — Wikipedia"})
    return out

def _pexels_photos(query):
    key = env("PEXELS_API_KEY")
    if not key:
        return []
    resp = http_get("https://api.pexels.com/v1/search", headers={"Authorization": key}, params={"query": query, "per_page": 12, "orientation": "portrait"})
    if resp is None:
        return []
    out = []
    for photo in resp.json().get("photos", []):
        src = photo.get("src") or {}
        url = src.get("large2x") or src.get("large")
        if url:
            out.append({"url": url, "source": "pexels", "query": query, "attribution": f"Photo by {photo.get('photographer', 'Pexels')} on Pexels"})
    return out

def _pixabay_photos(query):
    key = env("PIXABAY_API_KEY")
    if not key:
        return []
    resp = http_get("https://pixabay.com/api/", params={"key": key, "q": query, "image_type": "photo", "orientation": "vertical", "per_page": 12, "safesearch": "true"})
    if resp is None:
        return []
    out = []
    for photo in resp.json().get("hits", []):
        url = photo.get("largeImageURL") or photo.get("webformatURL")
        if url:
            out.append({"url": url, "source": "pixabay", "query": query, "attribution": "Photo from Pixabay"})
    return out
