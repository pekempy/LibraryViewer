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

def should_download_poster(key):
    path = os.path.join(POSTER_DIR, f"{key}.jpg")
    return not os.path.exists(path)

def download_poster(base_url, key, tag, token):
    poster_url = f"{base_url}/Items/{key}/Images/Primary?tag={tag}&quality=90"
    poster_path = os.path.join(POSTER_DIR, f"{key}.jpg")
    os.makedirs(POSTER_DIR, exist_ok=True)
    try:
        with requests.get(poster_url, stream=True, timeout=10) as r:
            with open(poster_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)
    except Exception as e:
        print(f"❌ Failed to download poster for {key}: {e}")

def fetch_jellyfin_movies(base_url, token, user_id, headers):
    log("Fetching Movies from Jellyfin...")
    movies = []
    lib_resp = requests.get(f"{base_url}/Users/{user_id}/Views", headers=headers)
    libraries = lib_resp.json().get("Items", [])

    for lib in libraries:
        if lib.get("CollectionType") != "movies":
            continue

        lib_id = lib["Id"]
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Movie",
            "Fields": "MediaSources,Genres,Overview,CommunityRating,OfficialRating,RunTimeTicks,ImageTags,CollectionItems",
            "ParentId": lib_id
        }
        response = requests.get(f"{base_url}/Users/{user_id}/Items", headers=headers, params=params)

        for item in response.json().get("Items", []):
            item_id = item["Id"]
            if not item.get("ImageTags"):
                continue

            image_tag = next(iter(item["ImageTags"].values()), None)
            image_url = f"{base_url}/Items/{item_id}/Images/Primary?tag={image_tag}&quality=90"

            used_media = item.get("MediaSources", [])
            size = used_media[0].get("Size", 0) if used_media else 0

            cred_url = f"{base_url}/Items/{item_id}/Credits"
            cred_resp = requests.get(cred_url, headers=headers)
            credits = cred_resp.json() if cred_resp.status_code == 200 else []
            directors = [c["Name"] for c in credits if c.get("Type") == "Director"]

            genres = item.get("Genres")
            collections = [c["Name"] for c in item.get("CollectionItems", [])]

            media_item = MediaItem.from_jellyfin(item, image_url, size, None, None, directors, used_media, collections, genres)

            if used_media:
                path = used_media[0].get("Path")
                if path:
                    media_item.file_path = extract_folder_and_filename(path)

            poster_filename = f"{item_id}.jpg"
            if should_download_poster(item_id):
                download_poster(base_url, item_id, image_tag, token)
            media_item.poster_path = f"posters/{poster_filename}"
            media_item.jellyfin_collections = collections

            movies.append(media_item.to_dict())

    return movies

def fetch_jellyfin_shows(base_url, token, user_id, headers):
    log("Fetching TV Shows from Jellyfin...")
    shows = []
    lib_resp = requests.get(f"{base_url}/Users/{user_id}/Views", headers=headers)
    libraries = lib_resp.json().get("Items", [])

    for lib in libraries:
        if lib.get("CollectionType") != "tvshows":
            continue

        lib_id = lib["Id"]
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Series",
            "Fields": "MediaSources,Genres,Overview,CommunityRating,OfficialRating,RunTimeTicks,ImageTags,CollectionItems",
            "ParentId": lib_id
        }
        response = requests.get(f"{base_url}/Users/{user_id}/Items", headers=headers, params=params)

        for item in response.json().get("Items", []):
            item_id = item["Id"]
            if not item.get("ImageTags"):
                continue

            image_tag = next(iter(item["ImageTags"].values()), None)
            image_url = f"{base_url}/Items/{item_id}/Images/Primary?tag={image_tag}&quality=90"

            ep_url = f"{base_url}/Shows/{item_id}/Episodes"
            ep_params = {"Fields": "MediaSources,ParentIndexNumber", "Recursive": "true", "Limit": 9999}
            ep_resp = requests.get(ep_url, headers=headers, params=ep_params)
            episodes = ep_resp.json().get("Items", [])

            size = 0
            used_media = []
            season_numbers = set()

            for ep in episodes:
                media_source = ep.get("MediaSources", [{}])[0]
                size += media_source.get("Size", 0)
                if not used_media and media_source.get("Path"):
                    used_media = [media_source]
                if "ParentIndexNumber" in ep:
                    season_numbers.add(ep["ParentIndexNumber"])

            season_count = len(season_numbers)
            episode_count = len(episodes)

            path = used_media[0].get("Path") if used_media else None

            cred_url = f"{base_url}/Items/{item_id}/Credits"
            cred_resp = requests.get(cred_url, headers=headers)
            credits = cred_resp.json() if cred_resp.status_code == 200 else []
            directors = [c["Name"] for c in credits if c.get("Type") == "Director"]

            genres = item.get("Genres")
            collections = [c["Name"] for c in item.get("CollectionItems", [])]

            media_item = MediaItem.from_jellyfin(item, image_url, size, season_count, episode_count, directors, used_media, collections, genres)
            if path:
                media_item.file_path = extract_folder_and_filename(path, depth=2)

            poster_filename = f"{item_id}.jpg"
            if should_download_poster(item_id):
                download_poster(base_url, item_id, image_tag, token)
            media_item.poster_path = f"posters/{poster_filename}"
            media_item.jellyfin_collections = collections

            shows.append(media_item.to_dict())

    return shows

def fetch_jellyfin_boxset_movies(base_url, token, user_id, headers):
    log("Fetching Movies from Collections in Jellyfin...")
    boxset_movies = []

    boxsets_url = f"{base_url}/Users/{user_id}/Items"
    boxset_resp = requests.get(boxsets_url, headers=headers, params={
        "IncludeItemTypes": "BoxSet",
        "Recursive": "true"
    })

    for boxset in boxset_resp.json().get("Items", []):
        box_id = boxset["Id"]
        box_name = boxset["Name"]

        items_url = f"{base_url}/Users/{user_id}/Items"
        params = {
            "ParentId": box_id,
            "Recursive": "true",
            "IncludeItemTypes": "Movie",
            "Fields": "MediaSources,Genres,Overview,CommunityRating,OfficialRating,RunTimeTicks,ImageTags,CollectionItems"
        }
        resp = requests.get(items_url, headers=headers, params=params)

        for item in resp.json().get("Items", []):
            item_id = item["Id"]
            if not item.get("ImageTags"):
                continue

            image_tag = next(iter(item["ImageTags"].values()), None)
            image_url = f"{base_url}/Items/{item_id}/Images/Primary?tag={image_tag}&quality=90"
            used_media = item.get("MediaSources", [])
            size = used_media[0].get("Size", 0) if used_media else 0

            cred_url = f"{base_url}/Items/{item_id}/Credits"
            cred_resp = requests.get(cred_url, headers=headers)
            credits = cred_resp.json() if cred_resp.status_code == 200 else []
            directors = [c["Name"] for c in credits if c.get("Type") == "Director"]

            genres = item.get("Genres")
            collections = [box_name]

            media_item = MediaItem.from_jellyfin(item, image_url, size, None, None, directors, used_media, collections, genres)

            if used_media:
                path = used_media[0].get("Path")
                if path:
                    media_item.file_path = extract_folder_and_filename(path)

            poster_filename = f"{item_id}.jpg"
            if should_download_poster(item_id):
                download_poster(base_url, item_id, image_tag, token)
            media_item.poster_path = f"posters/{poster_filename}"
            media_item.jellyfin_collections = collections

            boxset_movies.append(media_item.to_dict())

    return boxset_movies

def fetch_jellyfin_items(config):
    base_url = config["jellyfin"]["url"].rstrip("/")
    token = config["jellyfin"]["api_key"]
    user_id = config["jellyfin"]["user_id"]
    headers = JELLYFIN_HEADERS(token)

    return (
        fetch_jellyfin_movies(base_url, token, user_id, headers) + 
        fetch_jellyfin_shows(base_url, token, user_id, headers) + 
        fetch_jellyfin_boxset_movies(base_url, token, user_id, headers))
