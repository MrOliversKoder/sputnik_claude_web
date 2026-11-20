import os
import re
import time

import requests
from flask import Flask, render_template

app = Flask(__name__)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks API clients to send a descriptive User-Agent.
HEADERS = {"User-Agent": "SputnikTestSite/1.0 (test project; python-requests)"}
CACHE_SECONDS = 3600
_cache = {"time": 0, "images": []}


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_commons_images(query="Sputnik 1", limit=8):
    """Fetch free-licensed images from Wikimedia Commons, with license info."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6,  # File: namespace
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 800,
    }
    try:
        r = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:
        print("Commons fetch failed:", e)
        return []

    images = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        if not info.get("thumburl"):
            continue
        images.append({
            "title": page.get("title", "").replace("File:", ""),
            "url": info["thumburl"],
            "page": info.get("descriptionurl"),
            "artist": strip_tags(meta.get("Artist", {}).get("value")) or "Unknown",
            "license": meta.get("LicenseShortName", {}).get("value", "See source"),
        })
    return images


def get_images():
    now = time.time()
    if not _cache["images"] or now - _cache["time"] > CACHE_SECONDS:
        images = fetch_commons_images()
        if images:  # only cache successful fetches
            _cache.update(time=now, images=images)
        return images
    return _cache["images"]


@app.route("/")
def index():
    sample_images = [
        {"url": f"https://picsum.photos/seed/sputnik{i}/600/400", "alt": f"Sample image {i}"}
        for i in range(1, 5)
    ]
    return render_template("index.html", commons=get_images(), samples=sample_images)


if __name__ == "__main__":
    port = int(os.environ.get("SERVER_PORT") or os.environ.get("PORT") or 8080)
    app.run(host="0.0.0.0", port=port)
