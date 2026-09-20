"""Find royalty-free video clips, gifs, and photos. Videos first when they exist."""
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
    video_first = list(visuals_cfg.get("prefer_video", True) and extras or extras)
    for scene in scenes:
        queries = list(scene.get("search_queries") or [])
        main = scene.get("search_query") or topic
        if main not in queries:
            queries.insert(0, main)
        for extra in extras:
            if extra not in queries:
                queries.append(extra)
        tokens = [t.lower() for t in (scene.get("match_tokens") or []) if len(t) > 2]
        info(f"Visual search: {main}")
        asset = None
        for query in queries[:8]:
            asset = _search_video(query, cache_dir, used_urls, used_paths, tokens)
            if asset:
                break
        if asset is None:
            for query in queries[:8]:
                asset = _search_image(query, cache_dir, used_urls, used_paths, tokens)
                if asset:
                    break
        if asset is None:
            warn(f"No new media for '{main}', will use generated backdrop")
            asset = {"kind": "generated", "path": None, "query": main, "source": "generated", "attribution": ""}
        else:
            used_urls.add(asset.get("url") or "")
            if asset.get("path"):
                used_paths.add(asset["path"])
            info(f"Using {asset.get('kind')} from {asset.get('source')}")
        out = dict(scene)
        out["visual"] = asset
        results.append(out)
    return results

def _score(hit, tokens):
    blob = f"{hit.get('title', '')} {hit.get('query', '')}".lower()
    if not tokens:
        return int(hit.get("width") or 0)
    hits = sum(3 if t in (hit.get("title") or "").lower() else 1 for t in tokens if t in blob)
    return hits * 1000 + int(hit.get("width") or 0)

def _search_video(query, cache_dir, used_urls, used_paths, tokens):
    hits = []
    try:
        hits.extend(_wikimedia_videos(query))
        hits.extend(_wikimedia_videos(f"Minecraft {query}"))
    except Exception as exc:
        warn(f"video search error: {exc}")
    return _download_first(hits, cache_dir, used_urls, used_paths, tokens)

def _search_image(query, cache_dir, used_urls, used_paths, tokens):
    for fn in (_wikimedia_images, _wikipedia_search_images, _pexels_photos, _pixabay_photos):
        try:
            hits = fn(query)
        except Exception as exc:
            warn(f"{fn.__name__} error: {exc}")
            hits = []
        asset = _download_first(hits, cache_dir, used_urls, used_paths, tokens)
        if asset:
            return asset
    return None

def _download_first(hits, cache_dir, used_urls, used_paths, tokens):
    ranked = sorted(hits, key=lambda h: _score(h, tokens), reverse=True)
    if tokens:
        matched = [h for h in ranked if _score(h, tokens) >= 1000]
        if matched:
            ranked = matched + [h for h in ranked if h not in matched]
    for hit in ranked:
        url = hit.get("url")
        if not url or url in used_urls:
            continue
        ext = extension_from_url(url, ".mp4" if hit.get("kind") == "video" else ".jpg")
        dest = cache_path(cache_dir, "visuals", url, ext)
        if str(dest) in used_paths:
            continue
        if download_file(url, dest, headers=hit.get("headers")):
            return {
                "kind": hit.get("kind") or ("video" if ext in {".mp4", ".webm", ".mov", ".ogv", ".gif"} else "image"),
                "path": str(dest),
                "url": url,
                "query": hit.get("query", ""),
                "source": hit.get("source", ""),
                "attribution": hit.get("attribution", ""),
                "title": hit.get("title", ""),
            }
    return None

def _wikimedia_videos(query):
    resp = http_get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} (filetype:video OR filetype:gif)",
            "gsrnamespace": "6",
            "gsrlimit": "12",
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "format": "json",
        },
    )
    if resp is None:
        return []
    pages = (resp.json().get("query") or {}).get("pages", {})
    out = []
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info_ = infos[0]
        mime = (info_.get("mime") or "").lower()
        if mime not in {"video/mp4", "video/webm", "video/ogg", "image/gif"}:
            continue
        size = int(info_.get("size") or 0)
        if size and (size < 20_000 or size > 40_000_000):
            continue
        url = info_.get("url")
        if not url:
            continue
        out.append({
            "url": url,
            "title": page.get("title", ""),
            "width": int(info_.get("width") or 1280),
            "kind": "video",
            "source": "wikimedia",
            "query": query,
            "attribution": f"{page.get('title', 'Wikimedia')} — Wikimedia Commons",
        })
    return out

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
            "iiurlwidth": "1920",
            "format": "json",
        },
    )
    if resp is None:
        return []
    pages = (resp.json().get("query") or {}).get("pages", {})
    out = []
    skip = ("logo", "icon", "flag of", "coat of arms", "svg", "map of", "wordmark")
    for page in pages.values():
        title = page.get("title") or ""
        if any(s in title.lower() for s in skip):
            continue
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info_ = infos[0]
        mime = (info_.get("mime") or "").lower()
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            continue
        width = int(info_.get("thumbwidth") or info_.get("width") or 0)
        height = int(info_.get("thumbheight") or info_.get("height") or 0)
        if width < 800 and height < 800:
            continue
        url = info_.get("thumburl") or info_.get("url")
        orig_w = int(info_.get("width") or 0)
        if info_.get("url") and orig_w >= 1400:
            url = info_.get("url")
            width = orig_w
        if not url:
            continue
        out.append({
            "url": url,
            "title": title,
            "width": width,
            "kind": "video" if mime == "image/gif" else "image",
            "source": "wikimedia",
            "query": query,
            "attribution": f"{title} — Wikimedia Commons",
        })
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
            "pithumbsize": "1920",
            "format": "json",
        },
    )
    if resp is None:
        return []
    pages = (resp.json().get("query") or {}).get("pages", {})
    out = []
    for page in pages.values():
        thumb = page.get("thumbnail") or {}
        url = thumb.get("source")
        if not url:
            continue
        width = int(thumb.get("width") or 0)
        if width and width < 700:
            continue
        title = page.get("title", "")
        out.append({"url": url, "title": title, "width": width, "kind": "image", "source": "wikipedia", "query": query, "attribution": f"{title} — Wikipedia"})
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
        url = src.get("original") or src.get("large2x") or src.get("large")
        if url:
            out.append({"url": url, "title": photo.get("alt") or query, "width": 2000, "kind": "image", "source": "pexels", "query": query, "attribution": f"Photo by {photo.get('photographer', 'Pexels')} on Pexels"})
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
        url = photo.get("fullHDURL") or photo.get("largeImageURL") or photo.get("webformatURL")
        if url:
            out.append({"url": url, "title": photo.get("tags") or query, "width": int(photo.get("imageWidth") or 1280), "kind": "image", "source": "pixabay", "query": query, "attribution": "Photo from Pixabay"})
    return out
