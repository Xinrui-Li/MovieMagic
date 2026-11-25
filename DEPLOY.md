# Deploying MovieMagic to PythonAnywhere

We use PythonAnywhere's free tier because it keeps files on disk between
restarts, so `movies.db` (accounts, watchlists, reviews) survives.
Render's free tier wipes the disk on every deploy and restart.

The app needs no code changes to deploy:

- `init_db()` runs on import, so `movies.db` is created on first start.
- Debug mode is off unless `FLASK_DEBUG=1` is set. Do **not** set it on
  the server.
- PythonAnywhere runs the app through its own WSGI server, so gunicorn
  is not needed.

## 1. Create the account

Sign up at https://www.pythonanywhere.com (free "Beginner" account).
The site will be `https://<username>.pythonanywhere.com`.

## 2. Get the code (Bash console)

Open **Consoles → Bash** and run:

```bash
git clone https://github.com/Xinrui-Li/MovieMagic.git
cd MovieMagic
python3.13 -m venv .venv          # any Python 3.10+ listed on the site works
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Add the secrets

Still in `~/MovieMagic`, create `.env` (it is git-ignored, so it never
gets pushed):

```bash
cat > .env <<'EOF'
SECRET_KEY=paste-a-new-random-string
TMDB_API_KEY=paste-the-tmdb-read-access-token
EOF
```

Generate the secret key with
`python -c "import secrets; print(secrets.token_hex(32))"`.

Check that the server can reach TMDb (free accounts can only call
allow-listed sites):

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.themoviedb.org/3/configuration
```

`401` means TMDb answered (no token was sent), so it works. A proxy or
connection error means TMDb is blocked on the free tier.

## 4. Create the web app

1. **Web → Add a new web app → Manual configuration** (not "Flask").
   Pick the same Python version as the venv.
2. **Virtualenv:** `/home/<username>/MovieMagic/.venv`
3. **Source code / Working directory:** `/home/<username>/MovieMagic`
4. **Static files:** URL `/static/` → directory
   `/home/<username>/MovieMagic/static`
5. **Force HTTPS:** on.
6. Click the **WSGI configuration file** link and replace everything in
   it with:

```python
import os
import sys

from dotenv import load_dotenv

project_home = "/home/<username>/MovieMagic"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

load_dotenv(os.path.join(project_home, ".env"))

from app import app as application  # noqa: E402
```

7. Click **Reload** and open the site.

## 5. Updating after a push

```bash
cd ~/MovieMagic
git pull
source .venv/bin/activate
pip install -r requirements.txt   # only if requirements changed
```

Then click **Reload** on the Web tab. `git pull` does not touch
`movies.db` or `.env`.

## Troubleshooting

- **"Something went wrong" page:** read the **Error log** linked on the
  Web tab.
- **`SECRET_KEY is missing`:** `.env` is missing or not in
  `~/MovieMagic`.
- **Pages load but say "Unable to load movies":** wrong TMDb token, or
  TMDb is blocked (see the curl check in step 3).
- **No CSS:** check the `/static/` mapping in step 4.
- Free web apps must be renewed with one click every three months.
