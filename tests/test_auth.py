from werkzeug.security import check_password_hash

from conftest import flashes, login, register


def test_register_stores_hashed_password(client, query):
    response = register(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    user = query("SELECT * FROM users WHERE username = 'alice'")[0]
    assert user["password_hash"] != "password123"
    assert check_password_hash(user["password_hash"], "password123")


def test_register_rejects_short_username(client, query):
    register(client, username="ab")
    assert query("SELECT * FROM users") == []


def test_register_rejects_short_password(client, query):
    register(client, password="short")
    assert query("SELECT * FROM users") == []


def test_register_rejects_duplicate_username(client, query):
    register(client)
    response = register(client, password="different123")

    assert b"already taken" in response.data
    assert len(query("SELECT * FROM users")) == 1


def test_login_sets_session(client):
    register(client)
    response = login(client)

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["username"] == "alice"
        assert "user_id" in session


def test_login_rejects_wrong_password(client):
    register(client)
    response = login(client, password="wrong-password")

    assert b"Invalid username or password" in response.data
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_login_rejects_unknown_user(client):
    response = login(client, username="nobody")
    assert b"Invalid username or password" in response.data


def test_logout_clears_session(logged_in):
    logged_in.post("/logout")

    with logged_in.session_transaction() as session:
        assert "user_id" not in session


def test_logout_requires_post(client):
    assert client.get("/logout").status_code == 405


def test_protected_pages_redirect_to_login(client):
    for path in ("/watchlist", "/profile"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    assert "Please log in to continue." in flashes(client)


def test_protected_actions_redirect_to_login(client, query):
    response = client.post("/watchlist/add/27205")

    assert response.headers["Location"].endswith("/login")
    assert query("SELECT * FROM user_watchlist") == []
