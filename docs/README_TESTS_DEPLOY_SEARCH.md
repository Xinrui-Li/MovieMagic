# Tests, Deployment Prep, and New Search Bar

Branch: `chore/tests-deploy-prep`

This branch does **not** change `app.py`, so it will not conflict with the
GroupWatch work.

## Summary

| What | Why it matters |
|---|---|
| Test suite (`tests/`, 56 tests) | Lets us check the whole app in about 4 seconds before merging or demoing |
| Deployment guide (`DEPLOY.md`) | Step-by-step guide for putting the app online on PythonAnywhere |
| `.gitignore` fix | `.env` (our secret keys) was **not** being ignored before |
| `.env.example` | Shows new teammates which settings `.env` needs |
| New search bar | You can see right away where to type; filters are smaller and apply instantly |
| Bug check | Clicked through every page against the real TMDb; found 2 small bugs (listed below) |

---

## 1. Test suite

**Run it:**

```bash
pip install pytest
pytest tests -q
```

Expected result: `56 passed`.

The tests use a **fake TMDb** and a **temporary database**:

- No API key or internet is needed.
- They never touch your real `movies.db`.

| File | What it checks |
|---|---|
| `tests/test_auth.py` | Register, login, logout, password rules, duplicate usernames, logged-out users being sent to the login page |
| `tests/test_watchlist.py` | Add, remove, and change status; a movie and a TV show with the same ID stay separate; users cannot see or change each other's lists; TMDb being down |
| `tests/test_reviews.py` | Write, edit, and delete reviews; rating must be 1–5; review length limit; you can only delete your own review; review text cannot inject HTML; profile stats |
| `tests/test_pages.py` | Home page rows and their 10-minute cache; search and filters; bad URL values are ignored; detail pages; error messages when TMDb is down; trailer and cast/crew helpers |
| `tests/conftest.py` | Shared setup: the fake TMDb data, a temporary database, and login helpers |

**Adding tests (e.g. for GroupWatch):** use the `client` or `logged_in`
fixture. To fake a new TMDb endpoint, add it to
`FakeTMDb.responses` in `conftest.py`.

---

## 2. Deployment prep

The full guide is in [`DEPLOY.md`](../DEPLOY.md). Key points:

- **Host: PythonAnywhere (free).** It keeps `movies.db` between restarts.
  Render's free tier wipes the database every time it restarts.
- **No code changes are needed.** The database is created automatically,
  and debug mode stays off unless someone sets `FLASK_DEBUG=1`.
- `DEPLOY.md` has a one-line check that the server can reach TMDb.
  Free accounts can only call approved websites, so run it first.

### ⚠️ Change the secret keys before deploying

The `.gitignore` file had an invisible character at the start of line 1,
so the `.env` rule was ignored. `.env` was committed at one point
(commit `55278bb`). It was deleted later, but **it is still visible in
the git history**.

Before deploying:

1. Create a **new TMDb Read Access Token** on themoviedb.org and delete
   the old one.
2. Generate a **new `SECRET_KEY`**:
   `python -c "import secrets; print(secrets.token_hex(32))"`
3. Put only the new values in `.env` on your computer and on the server.

`.gitignore` is fixed now, so `.env` will not be committed again.

---

## 3. New search bar (home page)

**Before:** the title box was the same size as the four dropdowns, so it
was hard to tell where to type.

**After:**

- **Search box:** a large box on its own row, with a magnifying-glass
  icon. It glows when you click into it. The button now says
  **Search** instead of "Apply".
- **Filters** (Movies/TV, genre, year, sort): small pills on a row
  underneath.
- **Filters apply instantly:**
  - Picking a genre or sort updates the results straight away.
  - A year applies when you press Enter or click away.

It works with all four color themes and on phones.

Files: `templates/index.html` and `static/style.css`. The old search-bar
CSS was spread across 5 places in `style.css`; it is now one block at
the end of the file.

---

## 4. Bugs found (to fix after GroupWatch is merged)

Both are in `app.py`. We are waiting to fix them so they do not
conflict with GroupWatch.

1. **The "Newest Year" sort on a title search puts undated titles first.**
   Titles with no release date get the year `"N/A"`. When sorted
   newest-first, `"N/A"` lands above `"2026"`.
   **Fix:** in `home()`, sort by `movie["release_date"]` instead of
   `movie["year"]`.
2. **An invalid movie or show ID shows the wrong message.** For example,
   `/movie/999999999` says "Unable to load… try again" instead of saying
   the title was not found. It is only cosmetic; nothing crashes.

Everything else worked: every page, search, filter, watchlist action, and
review, with no crashes.

---

## Not in this branch (on purpose)

- **Demo seed data:** the GroupWatch owner will write it, since she knows
  which users and tastes her feature needs.
- **"Upcoming releases from your watchlist":** dropped, since it isn't
  needed for the final.

## All files changed

| File | Change |
|---|---|
| `tests/` (new) | 56 tests and shared setup |
| `DEPLOY.md` (new) | PythonAnywhere deployment guide |
| `.env.example` (new) | Template for `.env` |
| `.gitignore` | Removed the invisible character so `.env` is ignored |
| `README.md` | Added "Run the tests" and "Deployment" sections and updated the project structure |
| `templates/index.html` | New search bar layout |
| `static/style.css` | New search bar styles (old ones removed) |
| `docs/README_TESTS_DEPLOY_SEARCH.md` (new) | This write-up |
