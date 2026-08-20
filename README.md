# YTFlow - Premium YouTube Media Downloader

YTFlow is a fully functional, self-hosted local YouTube downloader web application. It allows you to paste any YouTube URL (standard, mobile, shorts), fetch and preview its details, and download it as high-quality MP3 (with embedded metadata and high-resolution thumbnail artwork) or MP4 (with audio/video merged).

---

## Key Features
- **Auto-Configuring Environment**: The system sets up its own Python virtual environment and downloads required packages automatically.
- **Embedded Cover Art & ID3 Tags**: Downloaded MP3s contain the video thumbnail embedded as ID3 cover art (`APIC` frame) alongside Title, Artist (Uploader), Year, and Genre metadata.
- **Lossless Stream Merging**: Downloads high-resolution MP4 video and audio streams separately and merges them lossless using FFmpeg.
- **Automatic FFmpeg Setup**: Detects if FFmpeg is installed globally. If not, automatically downloads a static build from Gyan.dev, extracts the executable files into a local `bin/` directory, and runs it on the fly.
- **Background Tasks & Progress Tracking**: Avoids request timeouts by queueing downloads, with step-by-step progress tracking shown on the frontend.
- **Clean Workspace**: Automatically purges temporary file storage and serves downloaded files securely, clearing disk usage once files are sent.

---

## Tech Stack
- **Backend**: Python 3.11+ / FastAPI
- **Frontend**: HTML5 / Tailwind CSS / Vanilla JavaScript
- **Download Core**: `yt-dlp`
- **Audio/Video Assembly**: `FFmpeg`
- **Metadata Editing**: `mutagen`

---

## Setup & Running on Windows

### Prerequisites
- Make sure you have **Python 3.11** or newer installed.
- Ensure "Add Python to PATH" was selected during Python installation.

### One-Click Launch
1. Double-click on **`run.bat`** in the project folder.
2. The script will:
   - Check for Python presence.
   - Create a Python virtual environment (`.venv`) if missing.
   - Install all package dependencies from `requirements.txt`.
   - Start the FastAPI backend server on `http://127.0.0.1:8000`.
   - Automatically open the application in your default web browser.

---

## Manual FFmpeg Setup (Offline Fallback)
If the backend fails to download FFmpeg automatically due to internet filters, you can install it manually:

1. Create a folder named `bin` in the root of the project directory (`youtube-downloader/bin/`).
2. Download the FFmpeg essentials build zip from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip).
3. Open the downloaded zip, find `ffmpeg.exe` and `ffprobe.exe` (usually inside the `bin/` subdirectory in the zip), and extract both files directly into the project's `bin/` folder.
4. Restart the application using `run.bat`.

---

## Directory Structure
```
youtube-downloader/
│
├── app/
│   ├── main.py          # App routes, validation, and task endpoint wrappers
│   ├── downloader.py    # yt-dlp metadata extraction & download workers
│   ├── media.py         # FFmpeg merging, conversions, and mutagen tagging
│   └── utils.py         # Path checks, filename sanitizing, FFmpeg auto-downloader
│
├── static/
│   ├── css/style.css    # Layout animations and custom focus effects
│   └── js/app.js       # Clipboard interface, polling mechanism, and UI updates
│
├── templates/
│   └── index.html       # Responsive web dashboard
│
├── bin/                 # Local FFmpeg executables
├── downloads/           # Ready-to-serve files (cleared after serving)
├── temp/                # Temp download processing directories
├── requirements.txt     # Python libraries
├── README.md            # System documentation
└── run.bat              # Setup and execution script
```

---

## Troubleshooting
- **Age-Restricted Content**: Age-restricted videos require YouTube account authentication which is not supported by default to protect credentials.
- **Private or Deleted Videos**: Private or deleted videos cannot be downloaded.
- **Port 8000 in Use**: If you have another local application running on port 8000, you can edit `run.bat` and change `--port 8000` to a different port (e.g. `--port 8080`).
