
import os
import requests

from dotenv import load_dotenv

import sqlite3
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing from .env")

# SQLite database for the movie watchlist
DATABASE = Path(__file__).resolve().parent / "movies.db"


def get_db_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection




def init_db():
    """Create user accounts, per-user watchlists, and reviews."""
    with get_db_connection() as connection:
        # 1. Create the users table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """)

        # 2. Create the watchlist table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                poster TEXT,
                rating REAL,
                release_date TEXT,
                watch_status TEXT NOT NULL DEFAULT 'Want to Watch'
                    CHECK (
                        watch_status IN (
                            'Want to Watch',
                            'Watching',
                            'Watched'
                        )
                    ),
                PRIMARY KEY (user_id, movie_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        # 3. Update existing databases if watch_status is missing
        columns = connection.execute(
            "PRAGMA table_info(user_watchlist)"
        ).fetchall()

        column_names = {column["name"] for column in columns}

        if "watch_status" not in column_names:
            connection.execute("""
                ALTER TABLE user_watchlist
                ADD COLUMN watch_status TEXT NOT NULL
                DEFAULT 'Want to Watch'
            """)

        # 4. Create the reviews table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                review_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, movie_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)




def login_required(view):
    """Require a logged-in user before accessing a view."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view



init_db()


TMDB_TOKEN = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

GENRES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Sci-Fi",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

ALLOWED_SORTS = {
    "popularity.desc",
    "vote_average.desc",
    "primary_release_date.desc",
}


def fetch_data(endpoint, params=None):
    """Request JSON data from TMDb."""

    if not TMDB_TOKEN:
        raise RuntimeError(
            "TMDB_API_KEY is missing. Check your .env file."
        )

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json",
    }

    response = requests.get(
        f"{TMDB_BASE_URL}{endpoint}",
        headers=headers,
        params=params or {},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def fetch_movies(endpoint, params=None):
    """Fetch movies and format them for the HTML template."""

    data = fetch_data(endpoint, params)
    movies = []

    for item in data.get("results", []):
        genre_ids = item.get("genre_ids", [])

        genre_names = [
            GENRES[genre_id]
            for genre_id in genre_ids
            if genre_id in GENRES
        ]

        poster_path = item.get("poster_path")
        release_date = item.get("release_date", "")

        movies.append({
            "id": item.get("id"),
            "title": item.get("title", "Untitled"),
            "year": release_date[:4] if release_date else "N/A",
            "rating": round(item.get("vote_average") or 0, 1),
            "genre": ", ".join(genre_names) or "Movie",
            "genre_ids": genre_ids,
            "poster": (
                f"{IMAGE_BASE_URL}{poster_path}"
                if poster_path
                else None
            ),
            "overview": (
                item.get("overview")
                or "No overview is available for this movie."
            ),
        })

    return (
        movies,
        data.get("total_pages", 1),
        data.get("total_results", 0),
    )


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        sort_by = request.form.get(
            "sort_by", "popularity.desc"
        )
        genre = request.form.get("genre", "")
        page = 1
    else:
        query = request.args.get("query", "").strip()
        sort_by = request.args.get(
            "sort_by", "popularity.desc"
        )
        genre = request.args.get("genre", "")
        try:
            page = int(request.args.get("page", 1))
        except ValueError:
            page = 1

    page = max(1, page)

    if sort_by not in ALLOWED_SORTS:
        sort_by = "popularity.desc"

    # Only allow genre IDs that exist in our genre dictionary.
    if genre not in ("",) and (
        not genre.isdigit() or int(genre) not in GENRES
    ):
        genre = ""

    error = None
    movies = []
    total_pages = 1
    total_results = 0

    try:
        if query:
            # Search by title. TMDb search does not support
            # the same global genre/sort options as Discover.
            movies, total_pages, total_results = fetch_movies(
                "/search/movie",
                {
                    "query": query,
                    "include_adult": "false",
                    "language": "en-US",
                    "page": page,
                },
            )

            # Genre filtering and sorting apply to this search page.
            if genre:
                genre_id = int(genre)
                movies = [
                    movie for movie in movies
                    if genre_id in movie["genre_ids"]
                ]

            if sort_by == "vote_average.desc":
                movies.sort(
                    key=lambda movie: movie["rating"],
                    reverse=True,
                )
            elif sort_by == "primary_release_date.desc":
                movies.sort(
                    key=lambda movie: movie["year"],
                    reverse=True,
                )

        else:
            # Discover supports server-side genre filtering
            # and sorting across the result set.
            params = {
                "language": "en-US",
                "sort_by": sort_by,
                "page": page,
                "vote_count.gte": 100,
            }

            if genre:
                params["with_genres"] = genre

            movies, total_pages, total_results = fetch_movies(
                "/discover/movie",
                params,
            )

        total_pages = max(1, total_pages)
        page = min(page, total_pages)

    except requests.RequestException:
        app.logger.exception("TMDb API request failed")
        movies = []
        total_pages = 1
        total_results = 0
        page = 1
        error = (
            "Unable to load movies right now. "
            "Please check your connection and try again."
        )

    except RuntimeError:
        app.logger.exception("TMDb API configuration error")
        movies = []
        total_pages = 1
        total_results = 0
        page = 1
        error = (
            "TMDb API credentials are not configured correctly. "
            "Please check your .env file."
        )

    return render_template(
        "index.html",
        movies=movies,
        query=query,
        sort_by=sort_by,
        genre=genre,
        genres=GENRES,
        error=error,
        page=page,
        total_pages=total_pages,
        total_results=total_results,
    )




@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    """Display movie details and an available YouTube trailer."""
    error = None
    movie = None
    trailer_url = None
    is_in_watchlist = False

    try:
        data = fetch_data(
            f"/movie/{movie_id}",
            {"language": "en-US"},
        )

        # Fetch videos associated with this movie.
        video_data = fetch_data(
            f"/movie/{movie_id}/videos",
            {"language": "en-US"},
        )

        videos = video_data.get("results", [])

        # Prefer an official YouTube trailer.
        trailers = [
            video for video in videos
            if video.get("site") == "YouTube"
            and video.get("type") == "Trailer"
            and video.get("key")
        ]

        official_trailers = [
            video for video in trailers
            if video.get("official") is True
        ]

        selected_trailer = (
            official_trailers[0]
            if official_trailers
            else trailers[0] if trailers
            else None
        )

        if selected_trailer:
            trailer_url = (
                "https://www.youtube.com/watch?v="
                + selected_trailer["key"]
            )

        poster_path = data.get("poster_path")
        backdrop_path = data.get("backdrop_path")

        movie = {
            "id": data.get("id"),
            "title": data.get("title", "Untitled"),
            "tagline": data.get("tagline", ""),
            "overview": (
                data.get("overview")
                or "No overview is available for this movie."
            ),
            "release_date": data.get("release_date") or "Unknown",
            "runtime": data.get("runtime"),
            "rating": round(data.get("vote_average") or 0, 1),
            "vote_count": data.get("vote_count", 0),
            "genres": [
                genre["name"]
                for genre in data.get("genres", [])
            ],
            "poster": (
                f"{IMAGE_BASE_URL}{poster_path}"
                if poster_path else None
            ),
            "backdrop": (
                f"https://image.tmdb.org/t/p/w1280{backdrop_path}"
                if backdrop_path else None
            ),
            "status": data.get("status", "Unknown"),
            "original_language": data.get(
                "original_language", "Unknown"
            ),
        }

        # Check whether the current user has saved this movie.
        if session.get("user_id"):
            with get_db_connection() as connection:
                saved_movie = connection.execute(
                    """
                    SELECT 1
                    FROM user_watchlist
                    WHERE user_id = ? AND movie_id = ?
                    """,
                    (session["user_id"], movie_id),
                ).fetchone()

            is_in_watchlist = saved_movie is not None

    except requests.RequestException:
        app.logger.exception(
            "Failed to fetch movie details or videos"
        )
        error = (
            "Unable to load movie details right now. Please try again."
        )

    except RuntimeError:
        app.logger.exception("TMDb API configuration error")
        error = "TMDb API is not configured correctly."


    with get_db_connection() as connection:
        review_rows = connection.execute(
            """
            SELECT id, user_id, username, rating, review_text,
                   created_at, updated_at
            FROM reviews
            WHERE movie_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (movie_id,),
        ).fetchall()

    reviews = [dict(row) for row in review_rows]

    user_review = None
    if session.get("user_id"):
        user_review = next(
            (
                review for review in reviews
                if review["user_id"] == session["user_id"]
            ),
            None,
        )

    return render_template(
        "movie_detail.html",
        movie=movie,
        error=error,
        trailer_url=trailer_url,
        is_in_watchlist=is_in_watchlist,
        reviews=reviews,
        user_review=user_review,
    )







@app.route("/watchlist")
@login_required
def watchlist():
    """Show the current user's saved movies."""
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT movie_id, title, poster, rating, release_date,
                   watch_status
            FROM user_watchlist
            WHERE user_id = ?
            ORDER BY rowid DESC
            """,
            (session["user_id"],),
        ).fetchall()

    movies = [dict(row) for row in rows]

    return render_template(
        "watchlist.html",
        movies=movies,
    )

@app.route("/watchlist/<int:movie_id>/status", methods=["POST"])
@login_required
def update_watch_status(movie_id):
    """Update the watch status of a saved movie."""
    watch_status = request.form.get("watch_status", "")

    allowed_statuses = {
        "Want to Watch",
        "Watching",
        "Watched",
    }

    if watch_status not in allowed_statuses:
        flash("Invalid watch status.", "error")
        return redirect(url_for("watchlist"))

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE user_watchlist
            SET watch_status = ?
            WHERE user_id = ? AND movie_id = ?
            """,
            (watch_status, session["user_id"], movie_id),
        )

        if cursor.rowcount == 0:
            flash("Movie not found in your watchlist.", "error")
        else:
            flash("Watch status updated!", "success")

    return redirect(url_for("watchlist"))



@app.route("/watchlist/add/<int:movie_id>", methods=["POST"])
@login_required
def add_to_watchlist(movie_id):
    """Fetch a movie and save it for the current user."""
    try:
        data = fetch_data(
            f"/movie/{movie_id}",
            {"language": "en-US"},
        )

        poster_path = data.get("poster_path")

        movie = {
            "id": data["id"],
            "title": data.get("title", "Untitled"),
            "poster": (
                f"{IMAGE_BASE_URL}{poster_path}"
                if poster_path else None
            ),
            "rating": round(data.get("vote_average") or 0, 1),
            "release_date": data.get("release_date") or "Unknown",
        }

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO user_watchlist
                    (user_id, movie_id, title, poster, rating, release_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    movie["id"],
                    movie["title"],
                    movie["poster"],
                    movie["rating"],
                    movie["release_date"],
                ),
            )

    except (requests.RequestException, RuntimeError):
        app.logger.exception("Could not add movie to watchlist")
        flash("Could not add this movie. Please try again.")
        return redirect(
            url_for("movie_detail", movie_id=movie_id)
        )

    flash("Movie added to your watchlist.")
    return redirect(
        url_for("movie_detail", movie_id=movie_id)
    )


@app.route("/watchlist/remove/<int:movie_id>", methods=["POST"])
@login_required
def remove_from_watchlist(movie_id):
    """Remove a movie from the current user's watchlist."""
    with get_db_connection() as connection:
        connection.execute(
            """
            DELETE FROM user_watchlist
            WHERE user_id = ? AND movie_id = ?
            """,
            (session["user_id"], movie_id),
        )

    flash("Movie removed from your watchlist.")
    return redirect(url_for("watchlist"))


@app.route("/profile")
@login_required
def profile():
    """Show the current user's movie activity."""
    user_id = session["user_id"]

    with get_db_connection() as connection:
        # Count this user's saved movies.
        watchlist_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM user_watchlist
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()[0]

        # Get review count and average personal rating.
        rating_stats = connection.execute(
            """
            SELECT
                COUNT(*) AS review_count,
                AVG(rating) AS average_rating
            FROM reviews
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        # Get the user's five most recently updated reviews.
        review_rows = connection.execute(
            """
            SELECT movie_id, rating, review_text,
                   created_at, updated_at
            FROM reviews
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 5
            """,
            (user_id,),
        ).fetchall()

    recent_reviews = [dict(row) for row in review_rows]

    # Look up movie titles for the recent reviews.
    for review in recent_reviews:
        review["movie_title"] = f"Movie #{review['movie_id']}"

        try:
            movie_data = fetch_data(
                f"/movie/{review['movie_id']}",
                {"language": "en-US"},
            )
            review["movie_title"] = movie_data.get(
                "title",
                review["movie_title"],
            )
        except (requests.RequestException, RuntimeError):
            # Keep the fallback title if TMDb is unavailable.
            pass

    average_rating = rating_stats["average_rating"]

    return render_template(
        "profile.html",
        username=session.get("username", "User"),
        watchlist_count=watchlist_count,
        review_count=rating_stats["review_count"],
        average_rating=(
            round(average_rating, 1)
            if average_rating is not None
            else None
        ),
        recent_reviews=recent_reviews,
    )


@app.route("/movie/<int:movie_id>/review", methods=["POST"])
@login_required
def save_review(movie_id):
    """Create or update the current user's review."""
    rating_value = request.form.get("rating", "").strip()
    review_text = request.form.get("review_text", "").strip()

    # Validate the rating.
    try:
        rating = int(rating_value)
    except (ValueError, TypeError):
        flash("Please select a rating from 1 to 5.")
        return redirect(url_for("movie_detail", movie_id=movie_id))

    if rating < 1 or rating > 5:
        flash("Rating must be between 1 and 5.")
        return redirect(url_for("movie_detail", movie_id=movie_id))

    # Validate the review text.
    if not review_text:
        flash("Please write a review before submitting.")
        return redirect(url_for("movie_detail", movie_id=movie_id))

    if len(review_text) > 2000:
        flash("Your review must be 2000 characters or fewer.")
        return redirect(url_for("movie_detail", movie_id=movie_id))

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO reviews
                (user_id, movie_id, username, rating, review_text)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET
                username = excluded.username,
                rating = excluded.rating,
                review_text = excluded.review_text,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                session["user_id"],
                movie_id,
                session["username"],
                rating,
                review_text,
            ),
        )

    flash("Your review has been saved.")
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route(
    "/movie/<int:movie_id>/review/delete",
    methods=["POST"],
)
@login_required
def delete_review(movie_id):
    """Delete only the current user's review for this movie."""
    with get_db_connection() as connection:
        connection.execute(
            """
            DELETE FROM reviews
            WHERE user_id = ? AND movie_id = ?
            """,
            (session["user_id"], movie_id),
        )

    flash("Your review has been deleted.")
    return redirect(url_for("movie_detail", movie_id=movie_id))




@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(username) > 30:
            flash("Username must be between 3 and 30 characters.")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        try:
            with get_db_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO users (username, password_hash)
                    VALUES (?, ?)
                    """,
                    (username, password_hash),
                )
        except sqlite3.IntegrityError:
            flash("That username is already taken.")
            return render_template("register.html")

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db_connection() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            flash("Invalid username or password.")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))



if __name__ == "__main__":
    app.run(debug=True)
