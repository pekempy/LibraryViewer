import os

def extract_folder_and_filename(full_path, depth = 1):
    full_path = full_path.replace("\\", "/")
    parts = full_path.split("/")
    if len(parts) < depth + 1:
        return full_path
    return "/".join(parts[-(depth + 1):])
