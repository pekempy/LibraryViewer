import re
import os
import json
import shutil
from dotenv import load_dotenv
from jellyfin_library import fetch_jellyfin_items, enrich_media_with_collections as enrich_jf_collections, download_posters as download_jf_posters
from plex_library import fetch_plex_items, enrich_media_with_collections as enrich_plex_collections, download_posters as download_plex_posters
from jinja2 import Environment, FileSystemLoader

CONFIG_DIR = "/config" if os.path.exists("/config/.env") else "."

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
        }
    }


def normalize(s):
    s = re.sub(r"\s*\(\d{4}\)$", "", s)
    s = re.sub(r"[^\w\s]", "", s).lower()
    s = re.sub(r"\b(the|a|an)\b", "", s).strip()
    return re.sub(r"\s+", " ", s)

def get_dedupe_key(item):
    file_path = item.get("file_path", "").replace("\\", "/").lower()
    title = item.get("title", "")
    year = item.get("year", "")
    file_size = item.get("file_size_bytes", 0)
    item_type = item.get("type", "").lower()

    tmdb_match = re.search(r"\{tmdb-(\d+)\}", file_path)
    if tmdb_match:
        return f"tmdb-{tmdb_match.group(1)}"

    norm_title = normalize(title)

    if item_type in ["show", "series"]:
        return f"show:{norm_title}|{year}"

    if file_path:
        parts = file_path.split("/")
        for i in range(len(parts) - 1):
            if norm_title in normalize(parts[i]):
                return f"title:{'/'.join(parts[:i+1])}"

    return f"size:{file_size}"

def merge_items(jellyfin_items, plex_items):
    def merge_dict(a, b):
        merged = dict(a)
        for key, value in b.items():
            if key == "source":
                a_sources = a["source"] if isinstance(a["source"], list) else [a["source"]]
                b_sources = b["source"] if isinstance(b["source"], list) else [b["source"]]
                merged["source"] = sorted(set(a_sources + b_sources))
            elif key not in merged or merged[key] in [None, "", [], {}]:
                merged[key] = value
            elif isinstance(value, list):
                existing = merged.get(key, [])
                if all(isinstance(i, dict) for i in value):
                    merged[key] = list({json.dumps(i, sort_keys=True): i for i in existing + value}.values())
                else:
                    merged[key] = list(set(existing + value))
            elif isinstance(value, dict):
                merged[key] = merge_dict(merged.get(key, {}), value)
        return merged

    combined = {}
    for item in jellyfin_items + plex_items:
        item["source"] = [item["source"]] if isinstance(item["source"], str) else item["source"]
        dedupe_key = get_dedupe_key(item)
        if dedupe_key not in combined:
            combined[dedupe_key] = item
        else:
            combined[dedupe_key] = merge_dict(combined[dedupe_key], item)

    return list(combined.values())


def render_site(all_items, config):
    print("🛠️  Rendering site...")
    env = Environment(loader=FileSystemLoader("templates"))
    os.makedirs("output", exist_ok=True)

    movies = [i for i in all_items if i["type"] == "Movie"]
    shows = [i for i in all_items if i["type"] in ["Show", "Series", "show"]]
    genres = sorted(set(g for item in all_items for g in item.get("genres", [])))
    years = sorted(set(i["year"] for i in all_items if i.get("year")), reverse=True)

    print(f"🎬 Total movies passed to template: {len(movies)}")
    print(f"📺 Total shows passed to template: {len(shows)}")
    print("🧩 Rendering HTML...")
    tmpl = env.get_template("library.html")
    html = tmpl.render(
        movies=movies,
        shows=shows,
        genres=genres,
        years=years,
        server_name=config["server_name"],
        movie_count=len(movies),
        show_count=len(shows),
        item_details=json.dumps({i["key"]: i for i in all_items})
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

    output_dir = os.path.join(CONFIG_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    if jellyfin_enabled:
        jellyfin_items = fetch_jellyfin_items(config)
        enrich_jf_collections(jellyfin_items, config)
        for item in jellyfin_items:
            item["source"] = "jellyfin"
        download_jf_posters(jellyfin_items)
        with open(os.path.join(output_dir, "media-jf.json"), "w", encoding="utf-8") as f:
            json.dump({"jellyfin": jellyfin_items}, f, indent=2)

    if plex_enabled:
        plex_items = fetch_plex_items(config)
        enrich_plex_collections(plex_items, config)
        for item in plex_items:
            item["source"] = "plex"
        download_plex_posters(plex_items, config)

        with open(os.path.join(output_dir, "media-plex.json"), "w", encoding="utf-8") as f:
            json.dump({"plex": plex_items}, f, indent=2)

    all_items = merge_items(jellyfin_items, plex_items)

    # Remove unused posters
    used_posters = {
        item.get("poster_path", "").replace("\\", "/")
        for item in all_items
        if item.get("poster_path")
    }
    poster_dir = os.path.join("output", "posters")
    if os.path.isdir(poster_dir):
        for fname in os.listdir(poster_dir):
            rel_path = f"posters/{fname}"
            if rel_path not in used_posters:
                try:
                    os.remove(os.path.join(poster_dir, fname))
                except Exception as e:
                    continue

    render_site(all_items, config)

    output_dir = os.path.join(CONFIG_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "media.json"), "w", encoding="utf-8") as f:
        json.dump({"all": all_items}, f, indent=2)

if __name__ == "__main__":
    main()
