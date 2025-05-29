# 📚 Static Media Library Viewer

Generate a browsable static HTML site from your Jellyfin and/or Plex library metadata.

---

## 🧾 Requirements

- Python 3.9+ (for manual use)
- Docker (optional, recommended for deployment)
- `.env` file in the root directory with:

```env
SERVER_NAME="My Media Library"

JELLYFIN_URL=http://your-jellyfin-host:8096
JELLYFIN_API_KEY=your_jellyfin_api_key
JELLYFIN_USER_ID=your_jellyfin_user_id

PLEX_URL=http://your-plex-host:32400
PLEX_TOKEN=your_plex_token
PLEX_MOVIE_LIBRARY=Films
PLEX_TV_LIBRARY=TV shows

JELLYFIN_ENABLED=true
PLEX_ENABLED=true
```

# ⚙️ Manual Usage (Python)

`pip install -r requirements.txt`
`python fetch_and_build.py`

This generates a static site in the output/ folder.
Open output/index.html in your browser to view it.
# 🐳 Docker Usage
## 🏗 Build the Image

`docker build -t static-library-viewer .`

⏱ This builds the base image. No media is fetched during this step.

## 🚀 Run the Container

```powershell
docker run -d \
  -v "C:\Docker\LibraryViewer":/config \
  -v "C:\Docker\LibraryViewer\output":/app/output \ # Optional: If you want to be able to examine the built files
  -p 1066:80 \
  --name media-library \
  ghcr.io/pekempy/libraryviewer:latest
  ```

- At startup, the container will:

- Fetch and merge metadata from Jellyfin/Plex

- Generate static HTML output

- Refresh the site every hour

- Your site will be available at: http://localhost:1066

# 🗂 Output Structure

`output/index.html`: Main page

`output/posters/`: Downloaded poster images

`output/static/`: CSS/JS assets

`output/media.json`: Combined media metadata

# 💡 Tips

Use npx serve output during development to live preview your site

Set `JELLYFIN_ENABLED=false` or `PLEX_ENABLED=false` to disable one backend

Add `PLEX_MOVIE_LIBRARY` or `PLEX_TV_LIBRARY` to restrict which libraries are scanned

# 🔐 Disclaimer

No personal data is stored in the output

Plex support may be limited depending on metadata access