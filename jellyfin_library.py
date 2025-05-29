import os
import requests
import shutil
from datetime import datetime
from media_item import MediaItem

JELLYFIN_HEADERS = lambda token: {
    "X-Emby-Token": token,
    "Content-Type": "application/json"
}

POSTER_DIR = "output/posters"

def fetch_jellyfin_items(config):
    print("📡 Fetching items from Jellyfin...")
    base_url = config["jellyfin"]["url"].rstrip("/")
    api_key = config["jellyfin"]["api_key"]
    user_id = config["jellyfin"]["user_id"]
    headers = JELLYFIN_HEADERS(api_key)
    all_items = {}

    url = f"{base_url}/Items"
    params = {
        "IncludeItemTypes": "Movie,Series",
        "Recursive": "true",
        "Fields": "MediaSources,Genres,ProductionYear,ImageTags,Overview,CommunityRating,OfficialRating,RunTimeTicks",
    }
    response = requests.get(url, headers=headers, params=params)
    try:
        items = response.json().get("Items", [])
        for item in items:
            all_items[item["Id"]] = item
    except Exception:
        return []

    coll_resp = requests.get(
        f"{base_url}/Users/{user_id}/Items?IncludeItemTypes=BoxSet", headers=headers
    )
    collections = coll_resp.json().get("Items", [])

    for collection in collections:
        collection_id = collection["Id"]
        collection_name = collection.get("Name")
        members_resp = requests.get(
            f"{base_url}/Items/{collection_id}/Items?Recursive=true", headers=headers
        )
        try:
            member_items = members_resp.json().get("Items", [])
        except Exception:
            continue
        for member in member_items:
            if member["Id"] in all_items:
                all_items[member["Id"]].setdefault("collections", []).append({
                    "id": collection_id,
                    "name": collection_name
                })
            else:
                member.setdefault("collections", []).append({
                    "id": collection_id,
                    "name": collection_name
                })
                all_items[member["Id"]] = member

    items_out = []
    items_list = list(all_items.values())
    total = len(items_list)

    for idx, item in enumerate(items_list, 1):
        if idx % max(1, total // 10) == 0 or idx == total:
            percent = int((idx / total) * 100)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📦 Processing Items: {idx}/{total} ({percent}%)")

        if not item.get("ImageTags"):
            continue
        image_tag = next(iter(item["ImageTags"].values()), None)
        image_url = f"{base_url}/Items/{item['Id']}/Images/Primary?tag={image_tag}&quality=90"

        size = 0
        season_count = None
        episode_count = None
        if item["Type"] == "Series":
            ep_resp = requests.get(
                f"{base_url}/Shows/{item['Id']}/Episodes?Fields=MediaSources,ParentIndexNumber",
                headers=headers,
            )
            try:
                episodes = ep_resp.json()
                season_numbers = set()
                for ep in episodes.get("Items", []):
                    size += ep.get("MediaSources", [{}])[0].get("Size", 0)
                    if "ParentIndexNumber" in ep:
                        season_numbers.add(ep["ParentIndexNumber"])
                season_count = len(season_numbers)
                episode_count = len(episodes.get("Items", []))
            except Exception:
                continue
        else:
            size = item.get("MediaSources", [{}])[0].get("Size", 0)

        cred_resp = requests.get(f"{base_url}/Items/{item['Id']}/Credits", headers=headers)
        try:
            credits = cred_resp.json()
        except Exception:
            credits = []

        directors = [person["Name"] for person in credits if person.get("Type") == "Director"]
        media = item.get("MediaSources", [])
        media_item = MediaItem.from_jellyfin(item, image_url, size, season_count, episode_count, directors, media)
        items_out.append(media_item.to_dict())

    return items_out

def enrich_media_with_collections(items, config):
    base_url = config["jellyfin"]["url"].rstrip("/")
    api_key = config["jellyfin"]["api_key"]
    user_id = config["jellyfin"]["user_id"]
    headers = JELLYFIN_HEADERS(api_key)

    item_map = {item["id"]: item for item in items}

    libs = requests.get(f"{base_url}/Users/{user_id}/Views", headers=headers)
    libraries = libs.json().get("Items", [])
    movie_libraries = [lib for lib in libraries if lib.get("CollectionType") == "movies"]

    for lib in movie_libraries:
        lib_id = lib["Id"]
        params = {
            "ParentId": lib_id,
            "IncludeItemTypes": "BoxSet",
            "Recursive": "true"
        }
        coll_resp = requests.get(f"{base_url}/Items", headers=headers, params=params)
        if coll_resp.status_code != 200:
            continue

        for collection in coll_resp.json().get("Items", []):
            collection_id = collection["Id"]
            collection_name = collection["Name"]
            members_resp = requests.get(
                f"{base_url}/Items", headers=headers,
                params={"ParentId": collection_id, "Recursive": "true"}
            )
            if members_resp.status_code != 200:
                continue

            for member in members_resp.json().get("Items", []):
                member_id = member.get("Id")
                if member_id in item_map:
                    item = item_map[member_id]
                    item.setdefault("collections", []).append({
                        "id": collection_id,
                        "name": collection_name
                    })

def download_posters(items):
    if os.path.exists(POSTER_DIR):
        shutil.rmtree(POSTER_DIR)
    os.makedirs(POSTER_DIR, exist_ok=True)

    for item in items:
        ext = ".jpg"
        poster_path = os.path.join(POSTER_DIR, f"{item['id']}{ext}")
        if not os.path.exists(poster_path):
            try:
                with requests.get(item["image_url"], stream=True) as r:
                    with open(poster_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)
            except:
                continue
        item["poster_path"] = f"posters/{item['id']}{ext}"
