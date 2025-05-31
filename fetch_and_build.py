import os
import json
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from utils.jellyfin_library import fetch_jellyfin_items
from utils.plex_library import fetch_plex_items
from utils.utils import log, merge_items, optimise_posters, clean_unused_posters, copy_static_files

CONFIG_DIR = "/config" if os.path.exists("/config/.env") else "."
OUTPUT_DIR = os.path.join(CONFIG_DIR, "output")

def load_config():
    load_dotenv(os.path.join(CONFIG_DIR, ".env"))
    return {
        "server_name": os.getenv("SERVER_NAME", "Media Library"),
        "jellyfin": {
            "url": os.getenv("JELLYFIN_URL"),
            "api_key": os.getenv("JELLYFIN_API_KEY"),
            "user_id": os.getenv("JELLYFIN_USER_ID"),
        },
        "plex": {
            "url": os.getenv("PLEX_URL"),
            "token": os.getenv("PLEX_TOKEN"),
            "movie_library_name": os.getenv("PLEX_MOVIE_LIBRARY", "movies").lower(),
            "show_library_name": os.getenv("PLEX_TV_LIBRARY", "tv shows").lower(),
        }
    }

def render_site(all_items, config):
    log("Rendering site...")
    env = Environment(loader=FileSystemLoader("templates"))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    movies = [i for i in all_items if i["type"].lower() == "movie"]
    shows = [i for i in all_items if i["type"].lower() in ["show", "series"]]
    genres = sorted(set(g for item in all_items for g in item.get("genres", [])))
    years = sorted(set(i["year"] for i in all_items if i.get("year")), reverse=True)

    log(f"🎬 Total movies passed to template: {len(movies)}")
    log(f"📺 Total shows passed to template: {len(shows)}")
    log("Rendering HTML...")

    template = env.get_template("library.html")
    html = template.render(
        movies=movies,
        shows=shows,
        genres=genres,
        years=years,
        server_name=config["server_name"],
        movie_count=len(movies),
        show_count=len(shows),
        item_details=json.dumps({i["key"]: i for i in all_items})
    )

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    copy_static_files()

def main():
    config = load_config()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    jellyfin_enabled = os.getenv("JELLYFIN_ENABLED", "false").lower() == "true"
    plex_enabled = os.getenv("PLEX_ENABLED", "false").lower() == "true"

    jellyfin_items = fetch_jellyfin_items(config) if jellyfin_enabled else []
    plex_items = fetch_plex_items(config) if plex_enabled else []

    log(f"[JF] Fetched {len(jellyfin_items)} items")
    log(f"[Plex] Fetched {len(plex_items)} items")
    log("Merging Jellyfin & Plex libraries...")

    # Ensure all items are dicts
    all_items = merge_items(
        [i.to_dict() if hasattr(i, "to_dict") else i for i in jellyfin_items],
        [i.to_dict() if hasattr(i, "to_dict") else i for i in plex_items]
    )

    log("Removing unused posters...")
    clean_unused_posters(all_items)

    log("Optimising posters (this will take a while)...")
    optimise_posters()

    render_site(all_items, config)

    with open(os.path.join(OUTPUT_DIR, "media.json"), "w", encoding="utf-8") as f:
        json.dump({"all": all_items}, f, indent=2)

if __name__ == "__main__":
    main()
