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
