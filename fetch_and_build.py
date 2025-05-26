import os
import requests
import yaml
import shutil
import json
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from tqdm import tqdm 

JELLYFIN_HEADERS = lambda token: {
    "X-Emby-Token": token,
    "Content-Type": "application/json"
}

CONFIG_DIR = "/config" if os.path.exists("/config/.env") else "."
POSTER_DIR = "output/posters"


def load_config():
    load_dotenv(os.path.join(CONFIG_DIR, ".env"))
    with open(os.path.join(CONFIG_DIR, "config.yaml")) as f:
        config = yaml.safe_load(f)

    config["server_name"] = os.getenv("SERVER_NAME", "Media Library")
    config["jellyfin"]["url"] = os.getenv("JELLYFIN_URL", config["jellyfin"].get("url"))
    config["jellyfin"]["api_key"] = os.getenv("JELLYFIN_API_KEY", config["jellyfin"].get("api_key"))
    config["jellyfin"]["user_id"] = os.getenv("JELLYFIN_USER_ID", config["jellyfin"].get("user_id"))
    config["plex"]["url"] = os.getenv("PLEX_URL", config["plex"].get("url"))
    config["plex"]["token"] = os.getenv("PLEX_TOKEN", config["plex"].get("token"))
    return config


def fetch_jellyfin_items(config):
    print("📡 Fetching items from Jellyfin...")
    base_url = config["jellyfin"]["url"].rstrip("/")
    api_key = config["jellyfin"]["api_key"]
    user_id = config["jellyfin"]["user_id"]

    response = requests.get(
        f"{base_url}/Users/{user_id}/Items?IncludeItemTypes=Movie,Series&Recursive=true&Fields=MediaSources,Genres,ProductionYear,ImageTags,Overview,CommunityRating,OfficialRating,RunTimeTicks",
        headers=JELLYFIN_HEADERS(api_key)
    )

    try:
        libraries = response.json()
    except Exception:
        return []

    items = []
    for item in tqdm(libraries.get("Items", []), desc="📦 Processing Items", unit="item"):
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
                headers=JELLYFIN_HEADERS(api_key)
            )
            try:
                episodes = ep_resp.json()
                season_numbers = set()
                for episode in episodes.get("Items", []):
                    size += episode.get("MediaSources", [{}])[0].get("Size", 0)
                    if "ParentIndexNumber" in episode:
                        season_numbers.add(episode["ParentIndexNumber"])
                season_count = len(season_numbers)
                episode_count = len(episodes.get("Items", []))
            except Exception:
                continue
        else:
            size = item.get("MediaSources", [{}])[0].get("Size", 0)

        cred_resp = requests.get(
            f"{base_url}/Items/{item['Id']}/Credits",
            headers=JELLYFIN_HEADERS(api_key)
        )
        try:
            credits = cred_resp.json()
        except Exception:
            credits = []

        directors = [person["Name"] for person in credits if person.get("Type") == "Director"]

        items.append({
            "key": item["Id"],
            "title": item.get("Name"),
            "year": item.get("ProductionYear"),
            "genres": item.get("Genres", []),
            "type": item.get("Type"),
            "id": item["Id"],
            "image_url": image_url,
            "media": item.get("MediaSources", []),
            "size": size,
            "overview": item.get("Overview"),
            "directors": directors,
            "community_rating": item.get("CommunityRating"),
            "official_rating": item.get("OfficialRating"),
            "runtime_ticks": item.get("RunTimeTicks"),
            "season_count": season_count,
            "episode_count": episode_count
        })
    return items



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


def render_site(items, config):
    env = Environment(loader=FileSystemLoader("templates"))
    os.makedirs("output", exist_ok=True)

    movies = [i for i in items if i["type"] == "Movie"]
    shows = [i for i in items if i["type"] == "Series"]

    genres = sorted(set(g for item in items for g in item.get("genres", [])))
    years = sorted(set(i["year"] for i in items if i.get("year")), reverse=True)

    tmpl = env.get_template("library.html")
    html = tmpl.render(
        movies=movies,
        shows=shows,
        genres=genres,
        years=years,
        server_name=config["server_name"],
        movie_count=len(movies),
        show_count=len(shows),
        item_details=json.dumps({i["key"]: i for i in items})
    )
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    for filename in os.listdir("static"):
        src_path = os.path.join("static", filename)
        dest_path = os.path.join("output/static", filename)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)


def main():
    config = load_config()
    items = fetch_jellyfin_items(config)
    download_posters(items)
    render_site(items, config)

    output_dir = os.path.join(CONFIG_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "media.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

if __name__ == "__main__":
    main()
