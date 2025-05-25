import os
import requests
import yaml
import shutil
from jinja2 import Environment, FileSystemLoader

JELLYFIN_HEADERS = lambda token: {
    "X-Emby-Token": token,
    "Content-Type": "application/json"
}

POSTER_DIR = "output/posters"


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def fetch_jellyfin_items(config):
    print("📡 Fetching Jellyfin library...")
    base_url = config["jellyfin"]["url"].rstrip("/")
    api_key = config["jellyfin"]["api_key"]
    user_id = config["jellyfin"]["user_id"]

    libraries = requests.get(
        f"{base_url}/Users/{user_id}/Items?IncludeItemTypes=Movie,Series&Recursive=true&Fields=MediaSources,Genres,ProductionYear,ImageTags",
        headers=JELLYFIN_HEADERS(api_key)
    ).json()

    items = []
    for item in libraries.get("Items", []):
        if not item.get("ImageTags"): continue
        image_tag = next(iter(item["ImageTags"].values()), None)
        image_url = f"{base_url}/Items/{item['Id']}/Images/Primary?tag={image_tag}&quality=90"

        size = 0
        if item["Type"] == "Series":
            episodes = requests.get(
                f"{base_url}/Shows/{item['Id']}/Episodes?Fields=MediaSources",
                headers=JELLYFIN_HEADERS(api_key)
            ).json()
            for episode in episodes.get("Items", []):
                size += episode.get("MediaSources", [{}])[0].get("Size", 0)
        else:
            size = item.get("MediaSources", [{}])[0].get("Size", 0)

        items.append({
            "title": item.get("Name"),
            "year": item.get("ProductionYear"),
            "genres": item.get("Genres", []),
            "type": item.get("Type"),
            "id": item["Id"],
            "image_url": image_url,
            "media": item.get("MediaSources", []),
            "size": size
        })
    return items


def download_posters(items):
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


def render_site(items):
    env = Environment(loader=FileSystemLoader("templates"))
    os.makedirs("output", exist_ok=True)

    movies = [i for i in items if i["type"] == "Movie"]
    shows = [i for i in items if i["type"] == "Series"]

    genres = sorted(set(g for item in items for g in item.get("genres", [])))
    years = sorted(set(i["year"] for i in items if i.get("year")), reverse=True)

    for page, data in [("movies.html", movies), ("shows.html", shows)]:
        tmpl = env.get_template(page)
        html = tmpl.render(items=data, genres=genres, years=years)
        with open(f"output/{page}", "w", encoding="utf-8") as f:
            f.write(html)

    tmpl = env.get_template("base.html")
    html = tmpl.render()
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    shutil.copytree("static", "output/static", dirs_exist_ok=True)


def main():
    config = load_config()
    items = fetch_jellyfin_items(config)
    download_posters(items)
    render_site(items)

if __name__ == "__main__":
    main()
