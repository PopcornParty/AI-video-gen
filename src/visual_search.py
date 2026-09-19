"""Find royalty-free images. Works with zero API keys via Wikimedia."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
from .config_loader import env
from .utils import cache_path, download_file, extension_from_url, http_get, info, warn

def find_visuals_for_scenes(scenes, topic, cache_dir: Path, visuals_cfg):
    used = set()
    results = []
    for scene in scenes:
        query = scene.get("search_query") or topic
        info(f"Visual search: {query}")
        asset = _search_image(query, cache_dir, used) or _search_image(topic, cache_dir, used)
        if asset is None:
            warn(f"No media for '{query}', will use generated backdrop")
            asset = {"kind": "generated", "path": None, "query": query, "source": "generated", "attribution": ""}
        else:
            used.add(asset.get("url") or "")
        out = dict(scene)
        out["visual"] = asset
        results.append(out)
    return results

def _search_image(query, cache_dir, used):
    for fn in (_wikimedia_images, _pexels_photos, _pixabay_photos):
        try:
            hits = fn(query)
        except Exception as exc:
            warn(f"{fn.__name__} error: {exc}")
            hits = []
        asset = _download_first(hits, cache_dir, used)
        if asset:
            return asset
    return None

def _download_first(hits, cache_dir, used):
    for hit in hits:
        url = hit.get("url")
        if not url or url in used:
            continue
        dest = cache_path(cache_dir, "visuals", url, extension_from_url(url, ".jpg"))
        if download_file(url, dest, headers=hit.get("headers")):
            return {"kind": "image", "path": str(dest), "url": url, "query": hit.get("query", ""), "source": hit.get("source", ""), "attribution": hit.get("attribution", "")}
    return None

def _wikimedia_images(query):
    resp = http_get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "12", "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": "1280", "format": "json"})
    if resp is None:
        return []
    pages = resp.json().get("query", {}).get("pages", {})
    out = []
    for page in pages.values():
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
