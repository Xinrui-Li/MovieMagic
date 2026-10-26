# MovieMagic 🎬

MovieMagic is a movie discovery and tracking web application that helps users explore movies, manage their personal watchlists, and share their thoughts on films.

## Features

- **Movie Discovery:** Search for movies and browse movie information, posters, and trailers using TMDb data.
- **Filtering and Sorting:** Explore movies using available filters and sorting options.
- **Movie Details:** View movie descriptions, metadata, and available trailers.
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

## Acknowledgments

Movie data and related movie information are provided through TMDb.

This project was developed collaboratively as a web application project.
