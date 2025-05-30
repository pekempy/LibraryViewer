import os

def extract_folder_and_filename(full_path):
    full_path = full_path.replace("\\", "/")
    file_name = os.path.basename(full_path)
    stem = os.path.splitext(file_name)[0].lower()
    parts = full_path.split("/")
    match_index = next(
        (i for i in reversed(range(len(parts))) if stem in parts[i].lower()),
        len(parts) - 2
    )
    return "/".join(parts[match_index:])
