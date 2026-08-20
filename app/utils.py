import os
import re
import urllib.request
import zipfile
import shutil
import logging

logger = logging.getLogger("youtube_downloader")

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and invalid characters.
    """
    # Remove any directory path characters
    filename = os.path.basename(filename)
    # Remove characters that are invalid on Windows/Linux filesystems
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Clean multiple spaces/dots/dashes
    filename = re.sub(r'\s+', " ", filename).strip()
    # Fallback for empty names
    if not filename or filename in (".", ".."):
        filename = "downloaded_media"
    return filename

def check_and_setup_ffmpeg() -> bool:
    """
    Checks if ffmpeg and ffprobe are available. If not, attempts to download
    and extract them locally to the 'bin' folder.
    Returns True if FFmpeg is ready, False otherwise.
    """
    # 1. Check system PATH
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        logger.info("FFmpeg is available in system PATH.")
        return True

    # 2. Check local bin folder
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_dir = os.path.join(app_dir, "bin")
    ffmpeg_exe = os.path.join(bin_dir, "ffmpeg.exe")
    ffprobe_exe = os.path.join(bin_dir, "ffprobe.exe")

    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        logger.info(f"FFmpeg is available in local bin folder: {bin_dir}")
        # Add local bin to PATH for the current process
        if bin_dir not in os.environ["PATH"]:
            os.environ["PATH"] = bin_dir + os.path.pathsep + os.environ["PATH"]
        return True

    # 3. Download and extract
    logger.info("FFmpeg not found. Attempting to download local Windows build from Gyan.dev...")
    os.makedirs(bin_dir, exist_ok=True)
    zip_path = os.path.join(bin_dir, "ffmpeg.zip")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(FFMPEG_URL, headers=headers)
        
        logger.info("Downloading FFmpeg zip archive (this might take a minute)...")
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        logger.info("Download completed. Extracting ffmpeg.exe and ffprobe.exe...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            extracted_ffmpeg = False
            extracted_ffprobe = False
            for member in zip_ref.namelist():
                if member.endswith("ffmpeg.exe"):
                    with zip_ref.open(member) as source, open(ffmpeg_exe, "wb") as target:
                        shutil.copyfileobj(source, target)
                    extracted_ffmpeg = True
                elif member.endswith("ffprobe.exe"):
                    with zip_ref.open(member) as source, open(ffprobe_exe, "wb") as target:
                        shutil.copyfileobj(source, target)
                    extracted_ffprobe = True

        # Clean up zip archive
        if os.path.exists(zip_path):
            os.remove(zip_path)

        if extracted_ffmpeg and extracted_ffprobe:
            logger.info("FFmpeg and FFprobe extracted successfully.")
            if bin_dir not in os.environ["PATH"]:
                os.environ["PATH"] = bin_dir + os.path.pathsep + os.environ["PATH"]
            return True
        else:
            logger.error("Failed to extract executables from the downloaded zip.")
            return False

    except Exception as e:
        logger.error(f"Error downloading/extracting FFmpeg: {e}")
        # Clean up zip in case of failure
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except:
                pass
        return False
