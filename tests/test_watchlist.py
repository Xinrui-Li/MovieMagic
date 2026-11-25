from conftest import flashes, login, register


def saved(query):
    return query(
        "SELECT movie_id, media_type, title, watch_status "
        "FROM user_watchlist ORDER BY media_type"
    )


def test_add_movie(logged_in, query):
    response = logged_in.post("/watchlist/add/27205")

    assert response.headers["Location"].endswith("/movie/27205")
    rows = saved(query)
    assert len(rows) == 1
    assert rows[0]["title"] == "Inception"
    assert rows[0]["media_type"] == "movie"
    assert rows[0]["watch_status"] == "Want to Watch"


def test_movie_and_tv_with_same_id_are_separate(logged_in, query):
    """TMDb movie and TV IDs overlap, so media_type is part of the key."""
    logged_in.post("/watchlist/add/27205")
    logged_in.post("/watchlist/add/tv/27205")

    rows = saved(query)
    assert [(row["media_type"], row["title"]) for row in rows] == [
        ("movie", "Inception"),
        ("tv", "Some Show"),
    ]


def test_adding_twice_keeps_one_row(logged_in, query):
    logged_in.post("/watchlist/add/27205")
    logged_in.post("/watchlist/add/27205")
    assert len(saved(query)) == 1


def test_add_fails_cleanly_when_tmdb_is_down(logged_in, query, tmdb):
    tmdb.fail = True
    response = logged_in.post("/watchlist/add/27205")

    assert response.status_code == 302
    assert saved(query) == []
    assert "Could not add this movie. Please try again." in flashes(logged_in)


def test_update_status(logged_in, query):
    logged_in.post("/watchlist/add/27205")
    logged_in.post(
        "/watchlist/27205/status", data={"watch_status": "Watched"}
    )
    assert saved(query)[0]["watch_status"] == "Watched"


def test_update_status_only_changes_matching_media_type(logged_in, query):
    logged_in.post("/watchlist/add/27205")
    logged_in.post("/watchlist/add/tv/27205")
    logged_in.post(
        "/watchlist/tv/27205/status", data={"watch_status": "Watching"}
    )

    statuses = {row["media_type"]: row["watch_status"] for row in saved(query)}
    assert statuses == {"movie": "Want to Watch", "tv": "Watching"}


def test_update_status_rejects_invalid_value(logged_in, query):
    logged_in.post("/watchlist/add/27205")
    logged_in.post(
        "/watchlist/27205/status", data={"watch_status": "Abandoned"}
    )

    assert saved(query)[0]["watch_status"] == "Want to Watch"
    assert "Invalid watch status." in flashes(logged_in)


def test_remove(logged_in, query):
    logged_in.post("/watchlist/add/27205")
    logged_in.post("/watchlist/add/tv/27205")
    logged_in.post("/watchlist/remove/27205")

    assert [row["media_type"] for row in saved(query)] == ["tv"]


def test_watchlist_page_shows_only_own_titles(client):
    register(client, "alice")
    register(client, "bobby")

    login(client, "alice")
    client.post("/watchlist/add/27205")
    assert b"Inception" in client.get("/watchlist").data

    client.post("/logout")
    login(client, "bobby")
    assert b"Inception" not in client.get("/watchlist").data


def test_user_cannot_change_another_users_watchlist(client, query):
    register(client, "alice")
    register(client, "bobby")

    login(client, "alice")
    client.post("/watchlist/add/27205")
    client.post("/logout")

    login(client, "bobby")
    client.post("/watchlist/27205/status", data={"watch_status": "Watched"})
    client.post("/watchlist/remove/27205")

    rows = saved(query)
    assert len(rows) == 1
    assert rows[0]["watch_status"] == "Want to Watch"


def test_detail_page_shows_saved_state(logged_in):
    assert b"Remove from Watchlist" not in logged_in.get("/movie/27205").data
    logged_in.post("/watchlist/add/27205")
    assert b"Remove from Watchlist" in logged_in.get("/movie/27205").data
