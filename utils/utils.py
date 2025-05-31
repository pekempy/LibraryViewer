import os
import re
import time
import json
import shutil
from PIL import Image

CONFIG_DIR = "/config" if os.path.exists("/config/.env") else "."
OUTPUT_DIR = os.path.join(CONFIG_DIR, "output")
POSTER_DIR = os.path.join(OUTPUT_DIR, "posters")

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



def copy_static_files():
    static_src = "static"
    static_dst = os.path.join(OUTPUT_DIR, "static")
    for filename in os.listdir(static_src):
        src_path = os.path.join(static_src, filename)
        dest_path = os.path.join(static_dst, filename)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)

def clean_unused_posters(all_items):
    used_posters = {
        item.get("poster_path", "").replace("\\", "/")
        for item in all_items
        if item.get("poster_path")
    }
    if os.path.isdir(POSTER_DIR):
        for fname in os.listdir(POSTER_DIR):
            rel_path = f"posters/{fname}"
            if rel_path not in used_posters:
                try:
                    os.remove(os.path.join(POSTER_DIR, fname))
                except Exception:
                    continue