import os
import requests
import shutil
from utils.media_item import MediaItem
from utils.utils import extract_folder_and_filename, log

JELLYFIN_HEADERS = lambda token: {
    "X-Emby-Token": token,
    "Content-Type": "application/json"
}

POSTER_DIR = "output/posters"

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        log(f"[JF] ⚠️ Failed to decode JSON from {resp.url}")
        log(f"[JF] Status: {resp.status_code}")
        log(f"[JF] Response text: {resp.text[:300]!r}")
        return {}

def should_download_poster(key):
    path = os.path.join(POSTER_DIR, f"{key}.jpg")
    return not os.path.exists(path)

def download_poster(base_url, key, tag, token):
    url = f"{base_url}/Items/{key}/Images/Primary?tag={tag}&quality=90"
    os.makedirs(POSTER_DIR, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=10) as r:
            with open(os.path.join(POSTER_DIR, f"{key}.jpg"), "wb") as f:
                shutil.copyfileobj(r.raw, f)
    except Exception as e:
        log(f"[JF] ❌ Failed to download poster for {key}: {e}")

def fetch_movies(base_url, token, user_id, headers, library_id):
    params = {
        "Recursive": "true",
        "IncludeItemTypes": "Movie",
        "Fields": "MediaSources,Genres,Overview,CommunityRating,OfficialRating,RunTimeTicks,ImageTags,CollectionItems",
        "ParentId": library_id
    }
    resp = requests.get(f"{base_url}/Users/{user_id}/Items", headers=headers, params=params)
    return safe_json(resp).get("Items", [])

def fetch_boxset_movies(base_url, token, user_id, headers):
    items = []
    boxsets = safe_json(
        requests.get(f"{base_url}/Users/{user_id}/Items", headers=headers, params={
            "IncludeItemTypes": "BoxSet",
            "Recursive": "true"
        })
    ).get("Items", [])

    for box in boxsets:
        box_id = box["Id"]
        name = box["Name"]
        resp = requests.get(f"{base_url}/Users/{user_id}/Items", headers=headers, params={
            "ParentId": box_id,
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "Fields": "MediaSources,Genres,Overview,CommunityRating,OfficialRating,RunTimeTicks,ImageTags,CollectionItems"
        })
        for item in safe_json(resp).get("Items", []):
            item["_boxset_collection"] = name
            items.append(item)
    return items

def fetch_shows(base_url, token, user_id, headers, library_id):
    params = {
        "Recursive": "true",
        "IncludeItemTypes": "Series",
        "Fields": "MediaSources,Genres,Overview,CommunityRating,OfficialRating,RunTimeTicks,ImageTags,CollectionItems",
        "ParentId": library_id
    }
    resp = requests.get(f"{base_url}/Users/{user_id}/Items", headers=headers, params=params)
    return safe_json(resp).get("Items", [])

def parse_item(item, library_type, base_url, token, headers, display_name):
    item_id = item["Id"]
    if not item.get("ImageTags"):
        return None

    image_tag = next(iter(item["ImageTags"].values()), None)
    used_media = item.get("MediaSources", [])
    size = used_media[0].get("Size", 0) if used_media else 0
    path = used_media[0].get("Path") if used_media else None

    # TV specific episode logic
    season_count = episode_count = None
    if library_type.lower() in ["tv", "shows", "series"]:
        episodes = safe_json(
            requests.get(
                f"{base_url}/Shows/{item_id}/Episodes",
                headers=headers,
                params={"Fields": "MediaSources,ParentIndexNumber", "Recursive": "true", "Limit": 9999}
            )
        ).get("Items", [])

        season_numbers = set()
        size = 0
        used_media = []
        for ep in episodes:
            src = ep.get("MediaSources", [{}])[0]
            size += src.get("Size", 0)
            if not used_media and src.get("Path"):
                used_media = [src]
            if "ParentIndexNumber" in ep:
                season_numbers.add(ep["ParentIndexNumber"])

        season_count = len(season_numbers)
        episode_count = len(episodes)
        path = used_media[0].get("Path") if used_media else path

    directors = []
    cred_resp = requests.get(f"{base_url}/Items/{item_id}/Credits", headers=headers)
    if cred_resp.status_code == 200:
        credits = safe_json(cred_resp)
        if isinstance(credits, list):
            directors = [c["Name"] for c in credits if isinstance(c, dict) and c.get("Type") == "Director"]

    genres = item.get("Genres")
    collections = [c["Name"] for c in item.get("CollectionItems", [])]
    if "_boxset_collection" in item:
        collections.append(item["_boxset_collection"])

    image_url = f"{base_url}/Items/{item_id}/Images/Primary?tag={image_tag}&quality=90"
    media_item = MediaItem.from_jellyfin(item, image_url, size, season_count, episode_count, directors, used_media, collections, genres)
    media_item.library = display_name

    if path:
        media_item.file_path = extract_folder_and_filename(
            path, depth=2 if library_type.lower() in ["tv", "shows", "series"] else 1
        )

    if should_download_poster(item_id):
        download_poster(base_url, item_id, image_tag, token)
    media_item.poster_path = f"posters/{item_id}.jpg"
    media_item.jellyfin_collections = collections
    return media_item.to_dict()

def fetch_jellyfin_items(config, library_name, library_type, display_name):
    base_url = config["jellyfin"]["url"].rstrip("/")
    token = config["jellyfin"]["api_key"]
    user_id = config["jellyfin"]["user_id"]
    headers = JELLYFIN_HEADERS(token)

    log(f"[JF] Fetching {library_type} from {display_name}...")

    libs = safe_json(requests.get(f"{base_url}/Users/{user_id}/Views", headers=headers)).get("Items", [])
    lib_id = next((lib["Id"] for lib in libs if lib["Name"].lower() == library_name.lower()), None)

    if not lib_id:
        log(f"[JF] ❌ Library not found: {library_name}")
        return []

    result = []
    if library_type.lower() == "movies":
        items = fetch_movies(base_url, token, user_id, headers, lib_id)
        items += fetch_boxset_movies(base_url, token, user_id, headers)
    elif library_type.lower() in ["tv", "shows", "series"]:
        items = fetch_shows(base_url, token, user_id, headers, lib_id)
    else:
        log(f"[JF] ❌ Unsupported library_type: {library_type}")
        return []

    for item in items:
        parsed = parse_item(item, library_type, base_url, token, headers, display_name)
        if parsed:
            result.append(parsed)

    return result
