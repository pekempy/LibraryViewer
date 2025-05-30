import json
import os
import re
import time
from PIL import Image

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def get_dedupe_key(item):
    return item.get("file_path", "").replace("\\", "/").lower()

def extract_folder_and_filename(full_path, depth = 1):
    full_path = full_path.replace("\\", "/")
    parts = full_path.split("/")
    if len(parts) < depth + 1:
        return full_path
    return "/".join(parts[-(depth + 1):])

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
            log(f"❌ Failed to optimise {fname}: {e}")