# MovieMagic 🎬

MovieMagic is a movie discovery and tracking web application that helps users explore movies, manage their personal watchlists, and share their thoughts on films.

## Features

- **Movie Discovery:** Search for movies and browse movie information, posters, and trailers using TMDb data.
- **Filtering and Sorting:** Explore movies using available filters and sorting options.
- **Movie Details:** View movie descriptions, metadata, and available trailers.
- **Cast & Crew:** See the top-billed cast and key crew on every movie and TV show page.
- **Year Filter:** Narrow searches and browsing to a release year (movies) or first air year (TV shows).
- **User Accounts:** Register, log in, and manage a personal account.
- **Personal Watchlist:** Add and remove movies from a watchlist and update their viewing status.
- **Ratings and Reviews:** Share opinions about movies and explore community reviews.
- **User Profiles:** View profile information and activity statistics.
- **Responsive Interface:** Browse the application through a user-friendly web interface.

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript, Jinja2 templates
- **Database:** SQLite
- **Movie Data:** TMDb API
- **Version Control:** Git and GitHub

## Project Structure

```text
MovieMagic/
├── app.py              # Flask application and routes
├── templates/          # HTML templates
├── static/             # CSS, JavaScript, and static assets
├── .env                # Local environment configuration
├── .gitignore          # Files excluded from Git
└── movies.db           # Local SQLite database, if generated
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Xinrui-Li/MovieMagic.git
cd MovieMagic
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the Python packages required by the application. If a `requirements.txt` file is available, run:

```powershell
pip install -r requirements.txt
```

Otherwise, install the packages imported by `app.py`.

### 4. Run the application

```powershell
python app.py
```

Open the local URL displayed in the terminal, commonly `http://127.0.0.1:5000`, in your browser.

## Usage

1. Open MovieMagic in your browser.
2. Search for movies or browse the available movie listings.
3. Select a movie to view its details and available trailer.
4. Register or log in to access account-dependent features.
5. Add movies to your watchlist.
6. Update a movie's status to **Want to Watch**, **Watching**, or **Watched**.
7. Remove movies from your watchlist when needed.
8. Explore ratings, reviews, and user profiles where available.

## Cast & Crew and Year Filter (by Alina)

### Cast & Crew

Movie pages (`/movie/<id>`) and TV show pages (`/tv/<id>`) now have two
new sections below the overview:

- **Top Cast:** up to 12 top-billed actors with their photo, name, and
  character, in a horizontally scrolling row. Actors without a photo
  show their first initial instead.
- **Key Crew:** up to 10 key crew members. A person with several jobs is
  shown once with all of them, e.g. "Christopher Nolan — Director,
  Writer, Producer".

Crew order:

| Page | Order |
|---|---|
| Movie | Director, Screenplay, Writer, Story, Novel, Original Music Composer, Director of Photography, Editor, Producer |
| TV show | Executive Producer, Novel, Original Music Composer, Director of Photography, Editor, Producer |

Producers come last because big titles list many of them. TV shows have
a different director for each episode, so TMDb's show-level crew is led
by the executive producers (usually the showrunners). TV cast comes from
TMDb's default credits, which list the most recent season's cast.

**How it works:** `movie_detail()` and `tv_detail()` fetch the details,
videos, and credits in one request with
`append_to_response=videos,credits`. The new `format_credits()` function
picks the cast and crew. The movie page used to make a second request
for videos and had its own copy of the trailer code; it now uses the
shared `pick_trailer()`.

### Year Filter

The search bar has a new **Any year** box between the genre and sort
options. It works for both movies and TV shows, and with or without a
title search:

| Example | Result |
|---|---|
| Year `2010` | Popular movies released in 2010 |
| TV Shows + year `2016` | Shows that first aired in 2016 |
| Title `batman` + year `2022` | Only the 2022 match |
| Genre Horror + year `1980` | Horror movies from 1980 |

- Movies use TMDb's `primary_release_year` and TV shows use
  `first_air_date_year`. TMDb applies the filter, so result counts and
  pages are accurate. (The genre filter on a title search only filters
  the current page.)
- The heading shows the year, e.g. "Horror Movies from 1980", and the
  year is kept when changing pages.
- Valid years are 1874 to five years after the current year, so listed
  upcoming releases are included. Anything else is ignored.
- The trending/popular/upcoming rows are hidden while a year is set,
  the same as for search and genre filters.

### Files changed

| File | Change |
|---|---|
| `app.py` | `format_credits()`, crew job lists, credits in `movie_detail()` and `tv_detail()`, year filter in `home()` |
| `templates/movie_detail.html` | Top Cast and Key Crew sections |
| `templates/tv_detail.html` | Top Cast and Key Crew sections |
| `templates/index.html` | Year box, year in headings and page links |
| `static/style.css` | Cast & crew styles and year box styles (end of file) |

No database changes are needed.

### How to test

1. Run `flask --app app run --port 5001` and open http://127.0.0.1:5001
2. Open a movie, e.g. http://127.0.0.1:5001/movie/27205 (Inception), and
   a TV show, e.g. http://127.0.0.1:5001/tv/1396 (Breaking Bad). Both
   should show Top Cast and Key Crew below the overview.
3. Try the year examples in the table above, including a TV search, and
   check the results and next page all match the year.

## Acknowledgments

Movie data and related movie information are provided through TMDb.

This project was developed collaboratively as a web application project.
