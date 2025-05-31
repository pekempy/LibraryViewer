# 📚 Static Media Library Viewer

Generate a browsable static HTML site from your Jellyfin and/or Plex library metadata.

![Preview](https://i.imgur.com/LoicSad.png)
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

JELLYFIN_ENABLED=true
PLEX_ENABLED=true
```

Also populate `libraries.json` with your library mappings
```json
 {
      "name":"Movies",
      "plex":{
         "name":"Films",
         "library_type":"Movies" 
      },
      "jellyfin":{
         "name":"Movies",
         "library_type":"Movies"
      }
   },
```
`name` in the parent object is the name of your tab within Library viewers web ui. You can customise this however you wish
A `plex` and `jellyfin` object will instruct the code to map these two libraries together when attempting to merge data. This should prevent cross-library merging, but allow for cross-server merging.
The `library_type` field in the json should be either `Movies` or `TV` as this tells the script how to handle fetching the data, if it's episodic it should hopefully work with TV. If it's structured like movies, then use Movies.


# ⚙️ Manual Usage (Python)

`pip install -r requirements.txt`
`python fetch_and_build.py`

This generates a static site in the output/ folder.
Open output/index.html in your browser to view it.
# 🐳 Docker Usage
## 🏗 Build the Image

`docker build -t static-library-viewer .`

This builds the base image. No media is fetched during this step.    

You can also fetch the latest release with    
`docker pull ghcr.io/pekempy/libraryviewer:latest`

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