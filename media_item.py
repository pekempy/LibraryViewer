import re
import os

class MediaItem:
    def __init__(self, source, **kwargs):
        self.source = source
        self.key = kwargs.get("key")
        self.title = kwargs.get("title")
        self.year = kwargs.get("year")
        self.genres = kwargs.get("genres", [])
        self.type = kwargs.get("type")
        self.id = kwargs.get("id")
        self.image_url = kwargs.get("image_url")
        self.poster_path = kwargs.get("poster_path", "")
        self.file_path = kwargs.get("file_path", "")
        self.file_size_bytes = kwargs.get("file_size_bytes", 0)
        self.media = kwargs.get("media", [])
        self.size = kwargs.get("size", 0)
        self.overview = kwargs.get("overview")
        self.directors = kwargs.get("directors", [])
        self.community_rating = kwargs.get("community_rating")
        self.official_rating = kwargs.get("official_rating")
        self.runtime_ticks = kwargs.get("runtime_ticks")
        self.season_count = kwargs.get("season_count")
        self.episode_count = kwargs.get("episode_count")
        self.collections = kwargs.get("collections", [])

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def find_relevant_path(full_path, title):
        if not full_path or not title:
            return ""

        def normalize(s):
            s = re.sub(r"[^\w\s]", "", s).lower()
            s = re.sub(r"\b(the|a|an)\b", "", s).strip()
            return re.sub(r"\s+", " ", s)  

        norm_title = normalize(title)
        parts = full_path.replace("\\", "/").split("/")

        for i, part in enumerate(parts):
            norm_part = normalize(part)
            if norm_title in norm_part:
                return "/".join(parts[i:])

        return os.path.basename(full_path) 

    @classmethod
    def from_jellyfin(cls, item, image_url, size, season_count, episode_count, directors, media):
        file_path = media[0].get("Path", "") if media else ""
        file_size_bytes = media[0].get("Size", 0) if media else 0
        relative_path = cls.find_relevant_path(file_path, item.get("Name", ""))

        return cls(
            source="jellyfin",
            key=item["Id"],
            title=item.get("Name"),
            year=item.get("ProductionYear"),
            genres=item.get("Genres", []),
            type=item.get("Type"),
            id=item["Id"],
            image_url=image_url,
            file_path=relative_path,
            file_size_bytes=file_size_bytes,
            media=media,
            size=size,
            overview=item.get("Overview"),
            directors=directors,
            community_rating=item.get("CommunityRating"),
            official_rating=item.get("OfficialRating"),
            runtime_ticks=item.get("RunTimeTicks"),
            season_count=season_count,
            episode_count=episode_count,
        )

    @classmethod
    def from_plex(cls, item, base_url, size, directors, media):
        file_path = media[0]["Part"][0].get("file") if media and "Part" in media[0] else ""
        file_size_bytes = size
        relative_path = cls.find_relevant_path(file_path, item.get("title", ""))

        rating_key = item.get("ratingKey")
        thumb = item.get("thumb", "")
        poster_filename = f"library_metadata_{rating_key}"
        image_url = f"{base_url}{thumb}" if thumb else ""
        poster_path = f"posters/{poster_filename}"

        return cls(
            source="plex",
            key=rating_key,
            title=item.get("title"),
            year=item.get("year"),
            genres=item.get("genres", []),
            type=item.get("type"),
            id=rating_key,
            image_url=image_url,
            poster_path=poster_path,
            file_path=relative_path,
            file_size_bytes=file_size_bytes,
            media=media,
            size=size,
            overview=item.get("summary"),
            directors=directors,
            community_rating=item.get("rating"),
            official_rating=item.get("contentRating"),
            runtime_ticks=item.get("duration"),
            season_count=item.get("childCount") if item.get("type") == "show" else None,
            episode_count=item.get("leafCount") if item.get("type") == "show" else None,
            collections=item.get("collections", []),
        )