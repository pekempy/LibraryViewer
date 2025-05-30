import re
import os
import json
import shutil
import time
from PIL import Image
from dotenv import load_dotenv
from jellyfin_library import fetch_jellyfin_items
from plex_library import fetch_plex_items
from jinja2 import Environment, FileSystemLoader

CONFIG_DIR = "/config" if os.path.exists("/config/.env") else "."
OUTPUT_DIR = os.path.join(CONFIG_DIR, "output")

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

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

def normalize(s):
    s = re.sub(r"\s*\(\d{4}\)$", "", s)
    s = re.sub(r"[^\w\s]", "", s).lower()
    s = re.sub(r"\b(the|a|an)\b", "", s).strip()
    return re.sub(r"\s+", " ", s)

def get_dedupe_key(item):
    path = item.get("file_path", "").replace("\\", "/").lower()
    if item.get("type", "").lower() in ["series", "show"]:
        # Keep only the base show folder
        parts = path.split("/")
        for i in range(len(parts) - 1, 0, -1):
            if parts[i].lower().startswith("season"):
                return "/".join(parts[:i]).rstrip("/")
        return "/".join(parts[:-1]).rstrip("/")
    return path

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
    log("🛠️  Rendering site...")
    env = Environment(loader=FileSystemLoader("templates"))
    os.makedirs("output", exist_ok=True)
    movies = [i for i in all_items if i["type"].lower() == "movie"]
    shows = [i for i in all_items if i["type"].lower() in ["show", "series"]]
    genres = sorted(set(g for item in all_items for g in item.get("genres", [])))
    years = sorted(set(i["year"] for i in all_items if i.get("year")), reverse=True)

    log(f"🎬 Total movies passed to template: {len(movies)}")
    log(f"📺 Total shows passed to template: {len(shows)}")
    log("🧩 Rendering HTML...")
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

def optimise_posters():
    poster_dir = os.path.join("output", "posters")
    if not os.path.isdir(poster_dir):
        return

    for fname in os.listdir(poster_dir):
        path = os.path.join(poster_dir, fname)
        try:
            if os.path.isfile(path) and fname.lower().endswith((".jpg", ".jpeg", ".png")):
                img = Image.open(path).convert("RGB")
                img.save(path, "JPEG", optimize=True, quality=85)
        except Exception as e:
            log(f"❌ Failed to optimize {fname}: {e}")

def log_progress(index, total, label):
    percent = int((index / total) * 100)
    if percent % 10 == 0 and (index % max(1, total // 10)) == 0:
        log(f"{label}: {index}/{total} ({percent}%)")

def main():
    config = load_config()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    jellyfin_enabled = os.getenv("JELLYFIN_ENABLED", "false").lower() == "true"
    plex_enabled = os.getenv("PLEX_ENABLED", "false").lower() == "true"

    jellyfin_items = []
    plex_items = []

    if jellyfin_enabled:
        log(f"Fetching items from Jellyfin, this may take a while... ")
        jellyfin_items = fetch_jellyfin_items(config)
        log(f"Fetched {len(jellyfin_items)} Jellyfin items")

    if plex_enabled:
        log(f"Fetching items from Plex, this may take a while... ")
        plex_items = fetch_plex_items(config)
        log(f"Fetched {len(plex_items)} Plex items")

    plex_items = [i.to_dict() if hasattr(i, "to_dict") else i for i in plex_items]
    jellyfin_items = [i.to_dict() if hasattr(i, "to_dict") else i for i in jellyfin_items]
    log(f"Merging Jellyfin & Plex libraries (if necessary)")
    all_items = merge_items(jellyfin_items, plex_items)

    log(f"Removing unused posters")
    # # Remove unused posters
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
                except Exception:
                    continue
    
    log(f"Optimising posters, this WILL take a while... ")
    optimise_posters()
    render_site(all_items, config)

    with open(os.path.join(OUTPUT_DIR, "media.json"), "w", encoding="utf-8") as f:
        json.dump({"all": all_items}, f, indent=2)

if __name__ == "__main__":
    main()
