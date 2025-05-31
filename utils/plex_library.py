import os
import requests
from utils.media_item import MediaItem
from utils.utils import extract_folder_and_filename, log


def get_plex_headers(token):
    return {
        "Accept": "application/json",
        "X-Plex-Token": token
    }

def get_plex_config():
    return {
        "url": os.getenv("PLEX_URL"),
        "token": os.getenv("PLEX_TOKEN"),
        "movie_library_name": os.getenv("PLEX_MOVIE_LIBRARY", "movies").lower(),
        "show_library_name": os.getenv("PLEX_TV_LIBRARY", "tv shows").lower()
    }

def get_section_keys(config):
    base_url = config["plex"]["url"].rstrip("/")
    token = config["plex"]["token"]
    headers = get_plex_headers(token)
    sections_url = f"{base_url}/library/sections"
    resp = requests.get(sections_url, headers=headers)
    sections = resp.json().get("MediaContainer", {}).get("Directory", [])

    movie_key = next((s["key"] for s in sections if s["title"].lower() == config["plex"]["movie_library_name"]), None)
    show_key = next((s["key"] for s in sections if s["title"].lower() == config["plex"]["show_library_name"]), None)

    return movie_key, show_key

def should_download_poster(key, updated_at):
    path = f"output/posters/library_metadata_{key}.jpg"
    return not os.path.exists(path) or os.path.getmtime(path) < updated_at

def download_poster(base_url, key, token):
    poster_url = f"{base_url}/library/metadata/{key}/thumb?X-Plex-Token={token}"
    poster_path = f"output/posters/library_metadata_{key}.jpg"
    os.makedirs("output/posters", exist_ok=True)
    try:
        response = requests.get(poster_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(poster_path, "wb") as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
    except Exception as e:
        print(f"❌ Failed to download poster for {key}: {e}")

def fetch_plex_items(config):
    base_url = config["plex"]["url"].rstrip("/")
    token = config["plex"]["token"]
    headers = get_plex_headers(token)

    movie_key, show_key = get_section_keys(config)
    result = []

    if movie_key:
        result.extend(fetch_plex_movies(base_url, token, headers, movie_key))
    if show_key:
        result.extend(fetch_plex_shows(base_url, token, headers, show_key))

    return result

def fetch_plex_movies(base_url, token, headers, movie_key):
    log("Fetching Movies from Plex...")
    movie_url = f"{base_url}/library/sections/{movie_key}/all"
    movie_params = {"type": "1", "includeGuids": "1"}
    movie_resp = requests.get(movie_url, headers=headers, params=movie_params)
    movie_items = movie_resp.json().get("MediaContainer", {}).get("Metadata", [])

    result = []
    for item in movie_items:
        media = item.get("Media", [])
        if not media or "Part" not in media[0]:
            continue

        part_file = media[0]["Part"][0].get("file")
        size = media[0]["Part"][0].get("size")
        directors = [d["tag"] for d in item.get("Director", [])]
        collections = [c["tag"] for c in item.get("Collection", [])]
        genres = [g["tag"] for g in item.get("Genre", [])]

        media_item = MediaItem.from_plex(item, base_url, size, directors, media, collections=collections, genres=genres, plex_token=token)
        if part_file:
            media_item.file_path = extract_folder_and_filename(part_file)
        media_item.plex_collections = collections
        result.append(media_item)

        updated_at = int(item.get("updatedAt", 0))
        if should_download_poster(item["ratingKey"], updated_at):
            download_poster(base_url, item["ratingKey"], token)

    return result

def fetch_plex_shows(base_url, token, headers, show_key):
    log("Fetching TV Shows from Plex...")
    show_url = f"{base_url}/library/sections/{show_key}/all"
    show_params = {"type": "2", "includeGuids": "1"}
    show_resp = requests.get(show_url, headers=headers, params=show_params)
    show_items = show_resp.json().get("MediaContainer", {}).get("Metadata", [])

    result = []
    for show in show_items:
        show_id = show.get("ratingKey")
        if not show_id:
            continue

        first_path, total_size, all_episodes = None, 0, []
        seasons_resp = requests.get(f"{base_url}/library/metadata/{show_id}/children", headers=headers)
        seasons = seasons_resp.json().get("MediaContainer", {}).get("Metadata", [])
        if not seasons:
            continue

        for season in seasons:
            season_id = season["ratingKey"]
            episodes_resp = requests.get(f"{base_url}/library/metadata/{season_id}/children", headers=headers)
            episodes = episodes_resp.json().get("MediaContainer", {}).get("Metadata", [])
            all_episodes.extend(episodes)

        all_episodes.sort(key=lambda ep: (ep.get("parentIndex", 0), ep.get("index", 0)))
        for episode in all_episodes:
            media = episode.get("Media", [])
            if media and "Part" in media[0]:
                part = media[0]["Part"][0]
                total_size += part.get("size", 0)
                if not first_path and part.get("file"):
                    first_path = part["file"]

        detail_resp = requests.get(f"{base_url}/library/metadata/{show_id}", headers=headers)
        metadata_list = detail_resp.json().get("MediaContainer", {}).get("Metadata", [])
        detailed_show = metadata_list[0] if len(metadata_list) == 1 else next(
            (item for item in metadata_list if str(item.get("ratingKey")) == str(show_id)), None
        )
        if not detailed_show:
            continue

        directors = [d["tag"] for d in show.get("Director", [])]
        collections = [c["tag"] for c in detailed_show.get("Collection", [])]
        genres = [g["tag"] for g in detailed_show.get("Genre", [])]

        media_item = MediaItem.from_plex(show, base_url, total_size, directors, [], collections=collections, genres=genres, plex_token=token)
        if first_path:
            media_item.file_path = extract_folder_and_filename(first_path, depth=2)

        media_item.season_count = show.get("childCount")
        media_item.episode_count = show.get("leafCount")
        result.append(media_item)

        updated_at = int(show.get("updatedAt", 0))
        if should_download_poster(show["ratingKey"], updated_at):
            download_poster(base_url, show["ratingKey"], token)

    return result
