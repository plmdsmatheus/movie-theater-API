def build_movies_list_cache_key(page: int, page_size: int) -> str:
    """
    I generate a unique cache key for the paginated movie list.
    """
    return f"movies:list:page:{page}:page_size:{page_size}"


def build_movie_sessions_cache_key(movie_id: int, page: int, page_size: int) -> str:
    """
    I generate a unique cache key for paginated sessions of a specific movie.
    """
    return f"movies:{movie_id}:sessions:page:{page}:page_size:{page_size}"