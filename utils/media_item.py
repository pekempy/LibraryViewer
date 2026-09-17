import re
import os

class MediaItem:
    def __init__(self, source, **kwargs):
        self.source = source
        self.library = kwargs.get("library")
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
        # Jellyfin reports RunTimeTicks (.NET ticks, 100ns units - 600M per
        # minute) while Plex reports duration in plain milliseconds (60K per
        # minute). Storing both under one ambiguous "runtime_ticks" name
        # made every Plex-only item's runtime silently round down to 0
        # minutes wherever it got divided by the Jellyfin-scale constant.
        # Normalising to minutes here removes the ambiguity at the source
        # instead of asking every consumer to know which unit a given item
        # came in as.
        self.runtime_minutes = kwargs.get("runtime_minutes")
        self.season_count = kwargs.get("season_count")
        self.episode_count = kwargs.get("episode_count")
        self.jellyfin_collections = kwargs.get("collections", [])
        self.plex_collections = kwargs.get("plex_collections", [])
        # {"tmdb": "...", "imdb": "...", "tvdb": "..."} where known - the
        # primary cross-server merge signal (see utils.get_dedupe_key).
        # File-path matching alone breaks the instant Plex and Jellyfin
        # disagree on folder naming for the same physical file.
        self.provider_ids = kwargs.get("provider_ids", {})

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def find_relevant_path(full_path, title):
        if not full_path or not title:
            return ""

        def normalise(s):
            s = re.sub(r"[^\w\s]", "", s).lower()
            s = re.sub(r"\b(the|a|an)\b", "", s).strip()
            return re.sub(r"\s+", " ", s)

        norm_title = normalise(title)
        parts = full_path.replace("\\", "/").split("/")

        for i, part in enumerate(parts):
            norm_part = normalise(part)
            if norm_title in norm_part:
                return "/".join(parts[i:])

        # Attempt TMDB tag match fallback
        tmdb_match = re.search(r"\{tmdb-(\d+)\}", full_path)
        if tmdb_match:
            tmdb_id = tmdb_match.group(1)
            for i, part in enumerate(parts):
                if f"tmdb-{tmdb_id}" in part:
                    return "/".join(parts[i:])

        return os.path.basename(full_path)

    @classmethod
    def from_jellyfin(cls, item, image_url, size, season_count, episode_count, directors, media, collections=None, genres=None, library=None):
        file_path = media[0].get("Path", "") if media else ""
        file_size_bytes = media[0].get("Size", 0) if media else 0
        relative_path = cls.find_relevant_path(file_path, item.get("Name", ""))

        provider_ids = {
            k.lower(): v for k, v in (item.get("ProviderIds") or {}).items()
            if k.lower() in ("tmdb", "imdb", "tvdb") and v
        }

        run_time_ticks = item.get("RunTimeTicks")
        runtime_minutes = round(run_time_ticks / 600_000_000) if run_time_ticks else None

        return cls(
            source="jellyfin",
            library=library,
            key=item["Id"],
            title=item.get("Name"),
            year=item.get("ProductionYear"),
            genres=genres or [],
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
            runtime_minutes=runtime_minutes,
            season_count=season_count,
            episode_count=episode_count,
            jellyfin_collections=collections or [],
            provider_ids=provider_ids,
        )


    @classmethod
    def from_plex(cls, item, base_url, size, directors, media, collections=None, genres=None, plex_token=None, library=None):
        file_path = media[0]["Part"][0].get("file") if media and "Part" in media[0] else ""
        file_size_bytes = size
        relative_path = cls.find_relevant_path(file_path, item.get("title", ""))

        rating_key = item.get("ratingKey")
        thumb = item.get("thumb", "")
        poster_filename = f"library_metadata_{rating_key}"
        token_param = f"?X-Plex-Token={plex_token}" if plex_token else ""
        image_url = f"{thumb}{token_param}" if thumb else ""
        poster_path = f"posters/{poster_filename}.jpg"

        # Plex's Guid entries look like {"id": "tmdb://1704"} - only present
        # when the request passed includeGuids=1.
        provider_ids = {}
        for guid in item.get("Guid", []):
            guid_id = guid.get("id", "")
            if "://" in guid_id:
                provider, value = guid_id.split("://", 1)
                if provider in ("tmdb", "imdb", "tvdb") and value:
                    provider_ids[provider] = value

        duration_ms = media[0].get("duration") if media else None
        runtime_minutes = round(duration_ms / 60_000) if duration_ms else None

        return cls(
            source="plex",
            library=library,
            key=rating_key,
            title=item.get("title"),
            year=item.get("year"),
            genres=genres,
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
            runtime_minutes=runtime_minutes,
            season_count=item.get("childCount") if item.get("type") == "show" else None,
            episode_count=item.get("leafCount") if item.get("type") == "show" else None,
            plex_collections=collections or [],
            provider_ids=provider_ids,
        )
