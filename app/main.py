import os
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl, field_validator
import urllib.parse

from app.downloader import (
    extract_video_metadata,
    start_download_task,
    get_task_status
)
from app.utils import check_and_setup_ffmpeg

from fastapi.middleware.cors import CORSMiddleware

# Configure logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file = os.path.join(BASE_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger("youtube_downloader")

app = FastAPI(title="YouTube Downloader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths setup
TEMP_DIR = os.path.join(BASE_DIR, "temp")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ensure required directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Auto-setup FFmpeg at startup
@app.on_event("startup")
def startup_event():
    logger.info("Initializing application and checking dependencies...")
    ffmpeg_ready = check_and_setup_ffmpeg()
    if ffmpeg_ready:
        logger.info("FFmpeg verification passed.")
    else:
        logger.warning("FFmpeg setup was not completed. Audio conversions and stream merging might fail!")
    
    print("\n" + "="*55)
    print("                YTFLOW SERVER RUNNING")
    print(f"  PC Local Link:  http://127.0.0.1:8000/")
    print("="*55 + "\n")

# Request validation schemas
class AnalyzeRequest(BaseModel):
    url: str

    @field_validator('url')
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        parsed = urllib.parse.urlparse(v)
        domain = parsed.netloc.lower()
        # Allow www.youtube.com, youtube.com, youtu.be, m.youtube.com
        if not any(d in domain for d in ["youtube.com", "youtu.be"]):
            raise ValueError("URL must be a valid YouTube link (youtube.com or youtu.be).")
        return v

class DownloadRequest(BaseModel):
    url: str
    format: str # "mp3" or "mp4"
    quality: str # bitrate for mp3 (320, 256, 192) or height for mp4 (1080, 720, 480)

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ("mp3", "mp4"):
            raise ValueError("Format must be either 'mp3' or 'mp4'.")
        return v

def remove_temp_download(file_path: str):
    """
    Background task to safely delete files from the downloads directory.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up served download file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting served file {file_path}: {e}")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.api_route("/api/analyze", methods=["GET", "POST"])
async def analyze(request: Request):
    url = None
    if request.method == "POST":
        try:
            payload = await request.json()
            url = payload.get("url")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body.")
    else: # GET
        url = request.query_params.get("url")
        
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter.")
        
    # Validate URL
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    if not any(d in domain for d in ["youtube.com", "youtu.be"]):
        raise HTTPException(status_code=400, detail="URL must be a valid YouTube link (youtube.com or youtu.be).")

    logger.info(f"Analyzing URL ({request.method}): {url}")
    result = extract_video_metadata(url)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to extract metadata."))
    return result

@app.post("/api/download")
def download(payload: DownloadRequest):
    logger.info(f"Scheduling download for: {payload.url} | format={payload.format} | quality={payload.quality}")
    
    # Simple local syntax check on URL before starting thread to bypass double metadata extraction
    parsed = urllib.parse.urlparse(payload.url)
    domain = parsed.netloc.lower()
    if not any(d in domain for d in ["youtube.com", "youtu.be"]):
        raise HTTPException(status_code=400, detail="URL must be a valid YouTube link.")
        
    task_id = start_download_task(
        url=payload.url,
        format_type=payload.format,
        quality=payload.quality,
        temp_dir=TEMP_DIR,
        output_dir=DOWNLOAD_DIR
    )
    return {"task_id": task_id}

@app.get("/api/progress/{task_id}")
def progress(task_id: str):
    status_data = get_task_status(task_id)
    return status_data

@app.get("/api/retrieve/{task_id}")
def retrieve(task_id: str, background_tasks: BackgroundTasks):
    status_data = get_task_status(task_id)
    if status_data["status"] != "ready":
        raise HTTPException(
            status_code=400, 
            detail=f"File is not ready. Status: {status_data['status']}. Error: {status_data.get('error')}"
        )
    
    file_name = status_data["file_name"]
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="The requested file was not found on the server.")

    # Schedule background file removal after sending
    background_tasks.add_task(remove_temp_download, file_path)
    
    # Return standard attachment response to trigger browser download
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream"
    )
