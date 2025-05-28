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

    @classmethod
    def from_jellyfin(cls, item, image_url, size, season_count, episode_count, directors):
        return cls(
            source="jellyfin",
            key=item["Id"],
            title=item.get("Name"),
            year=item.get("ProductionYear"),
            genres=item.get("Genres", []),
            type=item.get("Type"),
            id=item["Id"],
            image_url=image_url,
            media=item.get("MediaSources", []),
            size=size,
            overview=item.get("Overview"),
            directors=directors,
            community_rating=item.get("CommunityRating"),
            official_rating=item.get("OfficialRating"),
            runtime_ticks=item.get("RunTimeTicks"),
            season_count=season_count,
            episode_count=episode_count,
        )