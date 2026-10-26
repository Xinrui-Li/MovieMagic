# Trending Rows & TV Shows

This feature adds trending/popular/upcoming rows to the home page and
full TV show support (search, detail pages, watchlist, and reviews).

## Features

### Home page rows
Four horizontally scrolling rows appear on the plain home page
(hidden while searching or filtering):

| Row | TMDb endpoint |
|---|---|
| Trending This Week (movies + TV) | `/trending/all/week` |
| Popular Movies | `/movie/popular` |
| Popular TV Shows | `/tv/popular` |
| Coming Soon | `/movie/upcoming` |

- TV shows are marked with a **TV** badge.
- Rows are cached in memory for 10 minutes (`ROW_CACHE_SECONDS`) so the
  home page does not call TMDb on every visit.
- If one row fails to load, it is skipped and the rest of the page still works.

### TV show search
- The search bar has a **Movies / TV Shows** dropdown. Changing it
  reloads the page with the matching genre list.
- TV uses its own genres (`TV_GENRES`) and sort options (`TV_SORTS`
  maps "Newest Year" to `first_air_date.desc`).
- The navbar has a **TV Shows** link (`/?media=tv`).

### TV show detail page
`/tv/<id>` shows the poster, backdrop, rating, first/last air date,
seasons, episodes, episode runtime, genres, networks, creators, and a
YouTube trailer. Videos are fetched in the same request using
`append_to_response=videos`.

### Watchlist and reviews for TV
Logged-in users can add TV shows to their watchlist, change the watch
status, and write/edit/delete reviews, the same as for movies. The
profile page links each review to the correct movie or TV page.

## Routes

Movie routes are unchanged. Each TV route uses the same view function
as its movie version.

| Action | Movie | TV |
|---|---|---|
| Detail page | `/movie/<id>` | `/tv/<id>` |
| Save review | `POST /movie/<id>/review` | `POST /tv/<id>/review` |
| Delete review | `POST /movie/<id>/review/delete` | `POST /tv/<id>/review/delete` |
| Add to watchlist | `POST /watchlist/add/<id>` | `POST /watchlist/add/tv/<id>` |
| Remove from watchlist | `POST /watchlist/remove/<id>` | `POST /watchlist/remove/tv/<id>` |
| Update watch status | `POST /watchlist/<id>/status` | `POST /watchlist/tv/<id>/status` |

In templates, build TV links by passing `media_type='tv'`, e.g.
`url_for('save_review', movie_id=show.id, media_type='tv')`.
Use `detail_url(media_type, id)` to link to the right detail page.

## Database changes

TMDb movie IDs and TV IDs can overlap, so `user_watchlist` and
`reviews` now have a `media_type` column (`'movie'` or `'tv'`) that is
part of the key:

- `user_watchlist`: primary key `(user_id, media_type, movie_id)`
- `reviews`: unique `(user_id, media_type, movie_id)`

`movie_id` stores the TMDb ID for either kind of title.

**Existing databases are upgraded automatically** when the app starts
(`add_media_type_column()` in `app.py`). Old rows are kept and marked
as `'movie'`. No manual steps are needed.

## Files changed

| File | Change |
|---|---|
| `app.py` | TV genres/sorts, home rows + cache, `fetch_movies()` handles TV, `tv_detail` route, `media_type` in watchlist/review routes, database upgrade |
| `templates/index.html` | Movies/TV toggle, home rows, TV badge, TV links |
| `templates/tv_detail.html` | New TV detail page |
| `templates/watchlist.html` | Links and forms work for movies and TV |
| `templates/profile.html` | Review links go to the movie or TV page |
| `static/style.css` | Row, badge, and search toggle styles |

## How to test

1. Create a `.env` file with `SECRET_KEY` and `TMDB_API_KEY`
   (TMDb "API Read Access Token").
2. Run `flask --app app run --port 5001` and open http://127.0.0.1:5001
3. Check:
   - The home page shows the four rows.
   - Switching the search dropdown to **TV Shows** lists TV shows.
   - Clicking a TV show opens its detail page with seasons and a trailer.
   - After logging in, a TV show can be added to the watchlist, its
     status changed, and reviewed. It appears on **My Profile**.

## Notes for other features

- **Year filter:** use `primary_release_year` for movies and
  `first_air_date_year` for TV.
- **Cast & crew on TV pages:** change `append_to_response` in
  `tv_detail()` from `"videos"` to `"videos,credits"`.
