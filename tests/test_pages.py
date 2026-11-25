"""Home page, search, detail pages, and the helper functions behind them."""

import app as app_module


# --- Home page and trending rows --------------------------------------------

def test_home_shows_all_rows(client):
    page = client.get("/").data

    for heading in (b"Trending This Week", b"Popular Movies",
                    b"Popular TV Shows", b"Coming Soon"):
        assert heading in page


def test_trending_skips_people(client):
    page = client.get("/").data

    assert b"Trending Show" in page
    assert b"An Actor" not in page


def test_home_rows_are_cached(client, tmdb):
    client.get("/")
    client.get("/")

    assert tmdb.endpoints().count("/trending/all/week") == 1


def test_home_rows_refresh_after_cache_expires(client, tmdb, monkeypatch):
    client.get("/")
    for endpoint, (fetched_at, movies) in list(app_module.row_cache.items()):
        app_module.row_cache[endpoint] = (
            fetched_at - app_module.ROW_CACHE_SECONDS - 1, movies
        )
    client.get("/")

    assert tmdb.endpoints().count("/trending/all/week") == 2


def test_one_failing_row_does_not_break_home(client, tmdb):
    del tmdb.responses["/tv/popular"]
    response = client.get("/")

    assert response.status_code == 200
    assert b"Popular Movies" in response.data
    assert b"Popular TV Shows" not in response.data


def test_rows_hidden_while_searching(client):
    page = client.get("/?query=inception").data
    assert b"Trending This Week" not in page


# --- Search and filters --------------------------------------------------------

def test_title_search_uses_search_endpoint(client, tmdb):
    page = client.get("/?query=inception&year=2010").data

    assert b"Inception" in page
    params = tmdb.params_for("/search/movie")
    assert params["query"] == "inception"
    assert params["primary_release_year"] == "2010"


def test_tv_search_uses_tv_year_param(client, tmdb):
    client.get("/?query=show&media=tv&year=2008")
    assert tmdb.params_for("/search/tv")["first_air_date_year"] == "2008"


def test_browse_uses_discover_with_filters(client, tmdb):
    client.get("/?genre=27&year=1980&sort_by=vote_average.desc")

    params = tmdb.params_for("/discover/movie")
    assert params["with_genres"] == "27"
    assert params["primary_release_year"] == "1980"
    assert params["sort_by"] == "vote_average.desc"


def test_tv_release_sort_is_translated(client, tmdb):
    client.get("/?media=tv&sort_by=primary_release_date.desc")
    assert tmdb.params_for("/discover/tv")["sort_by"] == "first_air_date.desc"


def test_invalid_filters_are_ignored(client, tmdb):
    response = client.get(
        "/?genre=99999&year=abcd&sort_by=DROP+TABLE&media=books&page=x"
    )

    assert response.status_code == 200
    params = tmdb.params_for("/discover/movie")
    assert "with_genres" not in params
    assert "primary_release_year" not in params
    assert params["sort_by"] == "popularity.desc"
    assert params["page"] == 1


def test_page_number_is_capped_at_500(client, tmdb):
    client.get("/?genre=18&page=9999")
    assert tmdb.params_for("/discover/movie")["page"] == 500


def test_search_shows_message_when_tmdb_is_down(client, tmdb):
    tmdb.fail = True
    response = client.get("/?query=inception")

    assert response.status_code == 200
    assert b"Unable to load movies right now." in response.data


# --- Detail pages -------------------------------------------------------------

def test_movie_detail(client, tmdb):
    page = client.get("/movie/27205").data

    assert b"Inception" in page
    assert b"Leonardo DiCaprio" in page
    assert b"Christopher Nolan" in page
    assert b"youtube.com/watch?v=official-key" in page
    # Details, videos, and credits come from one request.
    assert tmdb.endpoints() == ["/movie/27205"]
    assert tmdb.params_for("/movie/27205")["append_to_response"] == (
        "videos,credits"
    )


def test_tv_detail(client):
    page = client.get("/tv/27205").data
    assert b"Some Show" in page
    assert b"AMC" in page


def test_detail_pages_handle_tmdb_errors(client, tmdb):
    tmdb.fail = True

    movie = client.get("/movie/27205")
    show = client.get("/tv/27205")

    assert movie.status_code == 200
    assert b"Unable to load movie details right now." in movie.data
    assert show.status_code == 200
    assert b"Unable to load show details right now." in show.data


# --- Helper functions ---------------------------------------------------------

def test_pick_trailer_prefers_official_youtube_trailer():
    videos = [
        {"site": "Vimeo", "type": "Trailer", "key": "vimeo", "official": True},
        {"site": "YouTube", "type": "Teaser", "key": "teaser", "official": True},
        {"site": "YouTube", "type": "Trailer", "key": "unofficial"},
        {"site": "YouTube", "type": "Trailer", "key": "official", "official": True},
    ]
    assert app_module.pick_trailer(videos).endswith("v=official")


def test_pick_trailer_falls_back_and_handles_none():
    unofficial = [{"site": "YouTube", "type": "Trailer", "key": "abc"}]

    assert app_module.pick_trailer(unofficial).endswith("v=abc")
    assert app_module.pick_trailer([]) is None


def test_format_credits_orders_cast_and_merges_crew_jobs():
    credits = {
        "cast": [
            {"name": "Second", "order": 1},
            {"name": "First", "order": 0},
        ],
        "crew": [
            {"id": 1, "name": "Producer Person", "job": "Producer"},
            {"id": 2, "name": "Nolan", "job": "Producer"},
            {"id": 2, "name": "Nolan", "job": "Director"},
            {"id": 3, "name": "Caterer", "job": "Catering"},
        ],
    }

    cast, crew = app_module.format_credits(credits)

    assert [person["name"] for person in cast] == ["First", "Second"]
    assert crew == [
        {"name": "Nolan", "jobs": ["Director", "Producer"]},
        {"name": "Producer Person", "jobs": ["Producer"]},
    ]


def test_fetch_movies_formats_movie_and_tv_results(tmdb):
    movies, total_pages, total_results = app_module.fetch_movies(
        "/trending/all/week"
    )

    assert [movie["title"] for movie in movies] == [
        "Trending Movie", "Trending Show"
    ]
    assert movies[1]["media_type"] == "tv"
    assert movies[1]["year"] == "2010"
    assert movies[0]["rating"] == 7.8
    assert movies[0]["genre"] == "Drama"
    assert (total_pages, total_results) == (1, 3)
