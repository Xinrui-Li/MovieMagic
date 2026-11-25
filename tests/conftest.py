"""Shared pytest fixtures.

Every test gets its own temporary SQLite database, and TMDb is replaced
with a fake, so the tests never use the network or the real movies.db.
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Set these before importing app.py. load_dotenv() does not override
# variables that are already set, so a real .env is never used here.
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["TMDB_API_KEY"] = "test-token"

import app as app_module  # noqa: E402


# ---------------------------------------------------------------------------
# Fake TMDb data
# ---------------------------------------------------------------------------

def list_item(item_id, title, media_type=None, **extra):
    """A search/discover/trending result in TMDb's format.

    Pass media_type only for trending results; TMDb leaves it out of
    search and discover results.
    """
    item = {
        "id": item_id,
        "poster_path": f"/poster{item_id}.jpg",
        "vote_average": 7.84,
        "genre_ids": [18],
        "overview": f"Overview of {title}.",
    }
    if media_type == "tv":
        item.update(name=title, first_air_date="2010-01-01")
    else:
        item.update(title=title, release_date="2010-07-16")
    if media_type:
        item["media_type"] = media_type
    item.update(extra)
    return item


def page_of(*items, total_pages=1):
    return {
        "results": list(items),
        "total_pages": total_pages,
        "total_results": len(items),
    }


MOVIE_DETAIL = {
    "id": 27205,
    "title": "Inception",
    "tagline": "Your mind is the scene of the crime.",
    "overview": "A thief who steals corporate secrets.",
    "release_date": "2010-07-16",
    "runtime": 148,
    "vote_average": 8.37,
    "vote_count": 30000,
    "genres": [{"id": 28, "name": "Action"}],
    "poster_path": "/inception.jpg",
    "backdrop_path": "/inception_bg.jpg",
    "status": "Released",
    "original_language": "en",
    "videos": {"results": [
        {"site": "YouTube", "type": "Trailer", "key": "fan-made",
         "official": False},
        {"site": "YouTube", "type": "Trailer", "key": "official-key",
         "official": True},
    ]},
    "credits": {
        "cast": [{"name": "Leonardo DiCaprio", "character": "Cobb",
                  "order": 0, "profile_path": None}],
        "crew": [{"id": 525, "name": "Christopher Nolan",
                  "job": "Director"}],
    },
}

TV_DETAIL = {
    "id": 27205,  # Same number as the movie on purpose.
    "name": "Some Show",
    "overview": "A TV show.",
    "first_air_date": "2008-01-20",
    "last_air_date": "2013-09-29",
    "number_of_seasons": 5,
    "number_of_episodes": 62,
    "episode_run_time": [47],
    "vote_average": 8.9,
    "vote_count": 15000,
    "genres": [{"id": 18, "name": "Drama"}],
    "networks": [{"name": "AMC"}],
    "created_by": [{"name": "Someone"}],
    "poster_path": "/show.jpg",
    "backdrop_path": None,
    "status": "Ended",
    "original_language": "en",
    "videos": {"results": []},
    "credits": {"cast": [], "crew": []},
}


class FakeTMDb:
    """Stands in for app.fetch_data and records every call."""

    def __init__(self):
        self.calls = []
        self.fail = False
        self.responses = {
            "/movie/27205": MOVIE_DETAIL,
            "/tv/27205": TV_DETAIL,
            "/trending/all/week": page_of(
                # Trending mixes types, so each result names its own.
                list_item(1, "Trending Movie", media_type="movie"),
                list_item(2, "Trending Show", media_type="tv"),
                {"id": 3, "media_type": "person", "name": "An Actor"},
            ),
            "/movie/popular": page_of(list_item(4, "Popular Movie")),
            "/tv/popular": page_of(
                list_item(5, "Popular Show", media_type="tv")
            ),
            "/movie/upcoming": page_of(list_item(6, "Upcoming Movie")),
            "/search/movie": page_of(list_item(27205, "Inception")),
            "/search/tv": page_of(
                list_item(27205, "Some Show", media_type="tv")
            ),
            "/discover/movie": page_of(list_item(7, "Discovered Movie")),
            "/discover/tv": page_of(
                list_item(8, "Discovered Show", media_type="tv")
            ),
        }

    def __call__(self, endpoint, params=None):
        self.calls.append((endpoint, dict(params or {})))
        if self.fail:
            raise requests.ConnectionError("TMDb is down")
        if endpoint not in self.responses:
            raise requests.HTTPError(f"404 for {endpoint}")
        return self.responses[endpoint]

    def endpoints(self):
        return [endpoint for endpoint, _ in self.calls]

    def params_for(self, endpoint):
        """Params of the most recent call to endpoint."""
        for called, params in reversed(self.calls):
            if called == endpoint:
                return params
        raise AssertionError(f"{endpoint} was never called")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def tmdb(monkeypatch):
    fake = FakeTMDb()
    monkeypatch.setattr(app_module, "fetch_data", fake)
    app_module.row_cache.clear()
    return fake


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setattr(app_module, "DATABASE", path)
    app_module.init_db()
    return path


@pytest.fixture
def client(db_path):
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


@pytest.fixture
def query(db_path):
    """Run a SELECT on the test database and return a list of rows."""
    def run(sql, params=()):
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(sql, params).fetchall()
    return run


def register(client, username="alice", password="password123"):
    return client.post(
        "/register", data={"username": username, "password": password}
    )


def login(client, username="alice", password="password123"):
    return client.post(
        "/login", data={"username": username, "password": password}
    )


@pytest.fixture
def logged_in(client):
    """A client logged in as alice."""
    register(client)
    login(client)
    return client


def flashes(client):
    """Flash messages waiting in the session."""
    with client.session_transaction() as session:
        return [message for _, message in session.get("_flashes", [])]
