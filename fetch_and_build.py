import os
import json
import shutil
import yaml
from dotenv import load_dotenv
from jellyfin_library import fetch_jellyfin_items, enrich_media_with_collections as enrich_jf_collections, download_posters as download_jf_posters
from plex_library import fetch_plex_items, enrich_media_with_collections as enrich_plex_collections, download_posters as download_plex_posters
from jinja2 import Environment, FileSystemLoader

CONFIG_DIR = "/config" if os.path.exists("/config/.env") else "."

def load_config():
    load_dotenv(os.path.join(CONFIG_DIR, ".env"))
    with open(os.path.join(CONFIG_DIR, "config.yaml")) as f:
        config = yaml.safe_load(f)
    jellyfin_enabled = os.getenv("JELLYFIN_ENABLED", "false").lower() == "true"
    plex_enabled = os.getenv("PLEX_ENABLED", "false").lower() == "true"

    config["server_name"] = os.getenv("SERVER_NAME", "Media Library")
    config["jellyfin"]["url"] = os.getenv("JELLYFIN_URL", config["jellyfin"].get("url"))
    config["jellyfin"]["api_key"] = os.getenv("JELLYFIN_API_KEY", config["jellyfin"].get("api_key"))
    config["jellyfin"]["user_id"] = os.getenv("JELLYFIN_USER_ID", config["jellyfin"].get("user_id"))
    config["plex"]["url"] = os.getenv("PLEX_URL", config["plex"].get("url"))
    config["plex"]["token"] = os.getenv("PLEX_TOKEN", config["plex"].get("token"))
    return config

def render_site(jellyfin_items, plex_items, config):
    print("🛠️  Rendering site...")
    env = Environment(loader=FileSystemLoader("templates"))
    os.makedirs("output", exist_ok=True)

    combined = jellyfin_items + plex_items
    movies = [i for i in combined if i["type"] == "Movie"]
    shows = [i for i in combined if i["type"] in ["Show", "Series", "show"]]
    genres = sorted(set(g for item in combined for g in item.get("genres", [])))
    years = sorted(set(i["year"] for i in combined if i.get("year")), reverse=True)

    print(f"🎬 Total movies passed to template: {len(movies)}")
    print(f"📺 Total shows passed to template: {len(shows)}")
    print("🧩 Rendering HTML...")
    tmpl = env.get_template("library.html")
    html = tmpl.render(
        movies=movies,
        shows=shows,
        media_jellyfin=jellyfin_items,
        media_plex=plex_items,
        genres=genres,
        years=years,
        server_name=config["server_name"],
        movie_count=len(movies),
        show_count=len(shows),
        item_details=json.dumps({i["key"]: i for i in combined})
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

    jellyfin_enabled = os.getenv("JELLYFIN_ENABLED", "false").lower() == "true"
    plex_enabled = os.getenv("PLEX_ENABLED", "false").lower() == "true"

    jellyfin_items = []
    plex_items = []

    if jellyfin_enabled:
        jellyfin_items = fetch_jellyfin_items(config)
        enrich_jf_collections(jellyfin_items, config)
        for item in jellyfin_items:
            item["source"] = "jellyfin"
        download_jf_posters(jellyfin_items)

    if plex_enabled:
        plex_items = fetch_plex_items(config)
        enrich_plex_collections(plex_items, config)
        for item in plex_items[:3]:
            item["source"] = "plex"
        download_plex_posters(plex_items, config)

    render_site(jellyfin_items, plex_items, config)

    output_dir = os.path.join(CONFIG_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "media.json"), "w", encoding="utf-8") as f:
        json.dump({
            "jellyfin": jellyfin_items,
            "plex": plex_items
        }, f, indent=2)


if __name__ == "__main__":
    main()
