import os
import requests
import shutil
from datetime import datetime
from media_item import MediaItem

POSTER_DIR = "output/posters"

def fetch_plex_items(config):
    print("📡 Fetching items from Plex...")
    base_url = config["plex"]["url"].rstrip("/")
    token = config["plex"]["token"]
    headers = {
        "Accept": "application/json",
        "X-Plex-Token": token
    }
    
    allowed_movie = os.getenv("PLEX_MOVIE_LIBRARY", "").lower()
    allowed_tv = os.getenv("PLEX_TV_LIBRARY", "").lower()
    allowed_names = {allowed_movie, allowed_tv}

    all_items = []

    sections_url = f"{base_url}/library/sections"
    sections_resp = requests.get(sections_url, headers=headers)
    sections = sections_resp.json()["MediaContainer"].get("Directory", [])

    for directory in sections:
        section_key = directory.get("key")
        section_type = directory.get("type")
        section_title = directory.get("title", "").lower()
        if section_title not in allowed_names:
            continue

        items_url = f"{base_url}/library/sections/{section_key}/all"
        items_resp = requests.get(items_url, headers=headers)
        items = items_resp.json()["MediaContainer"].get("Metadata", [])

        for item in items:
            item["type"] = section_type.capitalize()
            item["genres"] = [g["tag"] for g in item.get("Genre", [])]
            directors = [d["tag"] for d in item.get("Director", [])]
            media = item.get("Media", [])
            size = 0
            if media and "Part" in media[0]:
                size = media[0]["Part"][0].get("size", 0)

            media_item = MediaItem.from_plex(item, base_url, size, directors, media, plex_token=config["plex"]["token"])
            all_items.append(media_item.to_dict())

    return all_items


def enrich_media_with_collections(items, config):
    print("🗂️ Fetching collections from Plex...")
    base_url = config["plex"]["url"].rstrip("/")
    token = config["plex"]["token"]
    headers = {
        "Accept": "application/json",
        "X-Plex-Token": token
    }

    item_lookup = {item.get("ratingKey"): item for item in items}

    sections_url = f"{base_url}/library/sections"
    sections_resp = requests.get(sections_url, headers=headers)
    sections = sections_resp.json()["MediaContainer"].get("Directory", [])

    for directory in sections:
        section_key = directory.get("key")
        section_type = directory.get("type")
        if section_type != "movie":
            continue

        collection_url = f"{base_url}/library/sections/{section_key}/collection"
        coll_resp = requests.get(collection_url, headers=headers)
        if coll_resp.status_code != 200:
            continue
        collections = coll_resp.json()["MediaContainer"].get("Metadata", [])

        for coll in collections:
            coll_id = coll.get("ratingKey")
            coll_name = coll.get("title")
            if not coll_id or not coll_name:
                continue

            members_url = f"{base_url}/library/sections/{section_key}/all?collection={coll_id}"
            members_resp = requests.get(members_url, headers=headers)
            if members_resp.status_code != 200:
                continue

            members = members_resp.json()["MediaContainer"].get("Metadata", [])
            for member in members:
                member_id = member.get("ratingKey")
                if member_id in item_lookup:
                    item_lookup[member_id].setdefault("collections", []).append({
                        "id": coll_id,
                        "name": coll_name
                    })

    return list(item_lookup.values())


def download_posters(items, config):
    print("🖼️  Downloading Plex posters...")
    base_url = config["plex"]["url"].rstrip("/")
    token = config["plex"]["token"]
    headers = {
        "X-Plex-Token": token
    }

    os.makedirs(POSTER_DIR, exist_ok=True)

    total = len(items)
    for idx, item in enumerate(items, 1):
        if idx % max(1, total // 10) == 0 or idx == total:
            percent = int((idx / total) * 100)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⬇️  Posters: {idx}/{total} ({percent}%)")

        image_url = item.get("image_url")
        if not image_url:
            continue

        rating_key = item.get("key") or item.get("id")
        filename = f"library_metadata_{rating_key}.jpg"
        poster_path = os.path.join(POSTER_DIR, filename)
        full_url = base_url + image_url

        if not os.path.exists(poster_path):
            try:
                r = requests.get(full_url, headers=headers, stream=True)
                if r.status_code == 200:
                    with open(poster_path, "wb") as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)
            except Exception as e:
                print(f"⚠️ Failed to download poster for {item.get('title')}: {e}")
                continue

        item["poster_path"] = f"posters/{filename}"
