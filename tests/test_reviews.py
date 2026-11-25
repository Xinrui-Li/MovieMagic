import pytest

from conftest import flashes, login, register


def reviews(query):
    return query(
        "SELECT username, movie_id, media_type, rating, review_text "
        "FROM reviews ORDER BY media_type"
    )


def post_review(client, rating="5", text="Loved it.", path="/movie/27205"):
    return client.post(
        f"{path}/review", data={"rating": rating, "review_text": text}
    )


def test_save_review(logged_in, query):
    response = post_review(logged_in)

    assert response.headers["Location"].endswith("/movie/27205")
    row = reviews(query)[0]
    assert (row["username"], row["rating"], row["review_text"]) == (
        "alice", 5, "Loved it."
    )


def test_second_review_updates_instead_of_duplicating(logged_in, query):
    post_review(logged_in, rating="5", text="Loved it.")
    post_review(logged_in, rating="2", text="Changed my mind.")

    rows = reviews(query)
    assert len(rows) == 1
    assert (rows[0]["rating"], rows[0]["review_text"]) == (
        2, "Changed my mind."
    )


def test_movie_and_tv_reviews_with_same_id_are_separate(logged_in, query):
    post_review(logged_in, path="/movie/27205")
    post_review(logged_in, path="/tv/27205")

    assert [row["media_type"] for row in reviews(query)] == ["movie", "tv"]


@pytest.mark.parametrize("rating", ["0", "6", "abc", ""])
def test_rejects_invalid_rating(logged_in, query, rating):
    post_review(logged_in, rating=rating)
    assert reviews(query) == []


def test_rejects_empty_review(logged_in, query):
    post_review(logged_in, text="   ")

    assert reviews(query) == []
    assert "Please write a review before submitting." in flashes(logged_in)


def test_rejects_review_over_2000_characters(logged_in, query):
    post_review(logged_in, text="x" * 2001)
    assert reviews(query) == []

    post_review(logged_in, text="x" * 2000)
    assert len(reviews(query)) == 1


def test_delete_only_removes_own_review(client, query):
    register(client, "alice")
    register(client, "bobby")

    login(client, "alice")
    post_review(client, text="Alice review")
    client.post("/logout")

    login(client, "bobby")
    post_review(client, text="Bobby review")
    client.post("/movie/27205/review/delete")

    assert [row["username"] for row in reviews(query)] == ["alice"]


def test_reviews_show_on_detail_page(logged_in):
    post_review(logged_in, text="A mind-bending classic.")
    page = logged_in.get("/movie/27205").data

    assert b"A mind-bending classic." in page
    assert b"Community Reviews (1)" in page


def test_review_text_is_escaped(logged_in):
    post_review(logged_in, text="<script>alert(1)</script>")
    page = logged_in.get("/movie/27205").data

    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;" in page


def test_profile_shows_review_stats(logged_in):
    logged_in.post("/watchlist/add/27205")
    post_review(logged_in, rating="5", path="/movie/27205")
    post_review(logged_in, rating="2", path="/tv/27205")

    page = logged_in.get("/profile").data.decode()

    assert "3.5" in page                # average of 5 and 2
    assert "Based on 2 rating(s)" in page
    assert "Inception" in page          # title looked up from TMDb
    assert "Some Show" in page


def test_profile_still_loads_when_tmdb_is_down(logged_in, tmdb):
    post_review(logged_in)
    tmdb.fail = True

    response = logged_in.get("/profile")

    assert response.status_code == 200
    assert b"Movie #27205" in response.data
