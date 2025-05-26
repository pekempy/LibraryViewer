# Static Media Library Viewer

Generate a browsable static HTML site from your Jellyfin and/or Plex library metadata.

## 🧾 Requirements

- Python 3.9+ (for manual use)
- Docker (optional, for containerized use)
- `.env` file with:

```
SERVER_NAME="My Media Library"

JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=your_jellyfin_api_key
JELLYFIN_USER_ID=your_jellyfin_user_id

PLEX_URL=http://localhost:32400
PLEX_TOKEN=your_plex_token
```

## Testing / Development

Using `npx` to run `npx serve` allows the json to load and populate the cards.

## 🛠 Manual Usage (Python)

```bash
pip install -r requirements.txt
python fetch_and_build.py
```

Output will be in the output/ folder. Open `output/index.html` in your browser.

## 🐳 Docker Usage

### Build the image

```bash
docker build -t static-library-viewer .
```

### Run the container

```bash
docker run -d \
  --env-file .env \
  -v $(pwd)/output:/app/output \
  -p 1066:80 \
  --name library-site \
  static-library-viewer
```

The generated site will be accessible at http://localhost:1066.

## 📁 Output

`output/index.html`: Main page

`output/posters/`: Downloaded media images

`output/static/`: Copied JS/CSS

## 📝 Notes

Jellyfin is required for full functionality.

Plex is optional; support may be limited.

Re-run the script to refresh the data.
