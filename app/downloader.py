import os
import uuid
import logging
import threading
import urllib.request
import shutil
import yt_dlp
from app.utils import sanitize_filename, check_and_setup_ffmpeg
from app.media import (
    convert_to_mp3, 
    merge_audio_video, 
    embed_mp3_metadata, 
    embed_mp4_metadata, 
    verify_mp3_has_artwork,
    run_ffmpeg_command
)

logger = logging.getLogger("youtube_downloader")

# In-memory database of download tasks
# Schema: { task_id: { "status": str, "progress": float, "error": str, "file_name": str } }
download_tasks = {}
tasks_lock = threading.Lock()

def update_task(task_id: str, status: str, progress: float, error: str = None, file_name: str = None):
    with tasks_lock:
        download_tasks[task_id] = {
            "status": status,
            "progress": progress,
            "error": error,
            "file_name": file_name
        }
        logger.info(f"Task {task_id} updated: status={status}, progress={progress}%, error={error}")

def get_task_status(task_id: str) -> dict:
    with tasks_lock:
        return download_tasks.get(task_id, {"status": "error", "progress": 0.0, "error": "Task not found"})

def clean_old_tasks():
    # Helper to clean task records if they get too large
    pass

def parse_ytdl_error(error_msg: str) -> str:
    """
    Parses yt-dlp error output and returns a user-friendly message.
    """
    error_msg_lower = error_msg.lower()
    
    if "private video" in error_msg_lower:
        return "This video is private and cannot be downloaded."
    elif "deleted video" in error_msg_lower or "does not exist" in error_msg_lower:
        return "This video has been deleted or does not exist."
    elif "confirm your age" in error_msg_lower or "sign in to confirm your age" in error_msg_lower or "age-gated" in error_msg_lower:
        return "This video is age-restricted and requires sign-in, which is not supported."
    elif "unable to download webpage" in error_msg_lower or "connection refused" in error_msg_lower or "timed out" in error_msg_lower:
        return "Network error: Unable to reach YouTube. Please check your internet connection."
    elif "unsupported url" in error_msg_lower or "invalid url" in error_msg_lower:
        return "Invalid or unsupported YouTube URL. Please check the address."
    elif "video unavailable" in error_msg_lower:
        return "This video is unavailable in your region or country."
    
    # Generic fallback
    return f"YouTube Downloader error: {error_msg.split(':')[-1].strip()}"

def extract_video_metadata(url: str) -> dict:
    """
    Extracts metadata from a YouTube URL without downloading the video.
    """
    # Ensure FFmpeg is set up just in case yt-dlp needs it for format resolution
    check_and_setup_ffmpeg()
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # Sort thumbnails to find the highest resolution one
            thumbnails = info.get('thumbnails', [])
            highest_res_thumb = info.get('thumbnail') # fallback
            
            if thumbnails:
                # Filter out those without width/height or select the last ones which are usually highest quality
                valid_thumbs = [t for t in thumbnails if t.get('width') and t.get('height')]
                if valid_thumbs:
                    # Sort by width * height
                    valid_thumbs.sort(key=lambda t: t['width'] * t['height'], reverse=True)
                    highest_res_thumb = valid_thumbs[0]['url']
                else:
                    # Fallback to the last item in the list
                    highest_res_thumb = thumbnails[-1]['url']

            return {
                "success": True,
                "title": info.get("title", "Unknown Title"),
                "uploader": info.get("uploader", "Unknown Uploader"),
                "duration": info.get("duration", 0),  # in seconds
                "thumbnail": highest_res_thumb,
                "url": url,
                "upload_date": info.get("upload_date"),
                "genre": info.get("genre", "Music" if "music" in info.get("categories", []) else "YouTube")
            }
        except yt_dlp.utils.DownloadError as e:
            friendly_err = parse_ytdl_error(str(e))
            return {"success": False, "error": friendly_err}
        except Exception as e:
            return {"success": False, "error": f"Failed to extract video details: {str(e)}"}

def make_progress_hook(task_id: str, base_percent: float, multiplier: float):
    """
    Creates a yt-dlp progress hook that maps download progress to task status.
    """
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            downloaded_mb = downloaded / (1024 * 1024)
            status_text = f"downloading ({downloaded_mb:.1f} MB)"
            
            if total > 0:
                percent = (downloaded / total) * 100
                # Scale the percentage to fit the current stage
                scaled_percent = base_percent + (percent * multiplier)
                update_task(task_id, status_text, round(scaled_percent, 1))
            else:
                # Estimate progress using a 5MB threshold for unknown sizes
                simulated_total = 5 * 1024 * 1024  # 5 MB
                percent = min(95.0, (downloaded / simulated_total) * 100)
                scaled_percent = base_percent + (percent * multiplier)
                update_task(task_id, status_text, round(scaled_percent, 1))
        elif d['status'] == 'finished':
            update_task(task_id, "processing", base_percent + (100.0 * multiplier))
            
    return progress_hook

def run_download_thread(task_id: str, url: str, format_type: str, quality: str, temp_dir: str, output_dir: str):
    """
    Background worker thread function that downloads and processes YouTube media.
    """
    try:
        # Step 0: Ensure FFmpeg is available
        update_task(task_id, "preparing", 0.0)
        if not check_and_setup_ffmpeg():
            update_task(task_id, "error", 0.0, error="FFmpeg is required but not installed/configured.")
            return

        # Step 1: Extract full info (already validated, but we need details)
        update_task(task_id, "fetching video information", 5.0)
        
        ydl_opts_meta = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                update_task(task_id, "error", 0.0, error=parse_ytdl_error(str(e)))
                return

        title = info.get("title", "download")
        uploader = info.get("uploader", "Unknown")
        upload_date = info.get("upload_date") # YYYYMMDD
        genre = info.get("genre", "YouTube")
        
        year = upload_date[:4] if upload_date and len(upload_date) >= 4 else None
        
        sanitized_title = sanitize_filename(title)
        
        # Determine thumbnail URL
        thumbnails = info.get('thumbnails', [])
        thumbnail_url = info.get('thumbnail')
        if thumbnails:
            valid_thumbs = [t for t in thumbnails if t.get('width') and t.get('height')]
            if valid_thumbs:
                valid_thumbs.sort(key=lambda t: t['width'] * t['height'], reverse=True)
                thumbnail_url = valid_thumbs[0]['url']
            else:
                thumbnail_url = thumbnails[-1]['url']

        # Path configurations
        task_temp_dir = os.path.join(temp_dir, task_id)
        os.makedirs(task_temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        thumbnail_path = os.path.join(task_temp_dir, "thumb.jpg")
        
        # Download Thumbnail
        update_task(task_id, "fetching thumbnail", 8.0)
        if thumbnail_url:
            try:
                temp_thumb_download = os.path.join(task_temp_dir, "thumb_raw")
                headers = {'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request(thumbnail_url, headers=headers)
                with urllib.request.urlopen(req) as response, open(temp_thumb_download, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                # Convert WebP/PNG to standard JPEG using FFmpeg so Windows Explorer can render it
                cmd = ["ffmpeg", "-y", "-i", temp_thumb_download, thumbnail_path]
                if run_ffmpeg_command(cmd):
                    logger.info("Successfully standardized downloaded thumbnail to JPEG.")
                else:
                    logger.warning("FFmpeg thumbnail conversion failed, falling back to raw file.")
                    shutil.copy2(temp_thumb_download, thumbnail_path)
            except Exception as e:
                logger.warning(f"Failed to download/process thumbnail: {e}")
                thumbnail_path = None
        else:
            thumbnail_path = None

        if format_type == "mp3":
            # --- MP3 Download Workflow ---
            # Output path
            final_filename = f"{sanitized_title}.mp3"
            final_output_path = os.path.join(output_dir, final_filename)
            
            # Map quality (kbps) to ffmpeg options
            bitrate_map = {
                "320": "320k",
                "256": "256k",
                "192": "192k"
            }
            bitrate = bitrate_map.get(quality, "320k")
            
            # Download audio stream
            # We download the best audio format
            audio_temp_template = os.path.join(task_temp_dir, "audio.%(ext)s")
            
            ydl_opts_dl = {
                'format': 'bestaudio/best',
                'outtmpl': audio_temp_template,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [make_progress_hook(task_id, 10.0, 0.65)], # scaled from 10% to 75%
            }
            
            update_task(task_id, "downloading audio", 10.0)
            with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                try:
                    ydl.download([url])
                except Exception as e:
                    update_task(task_id, "error", 0.0, error=parse_ytdl_error(str(e)))
                    return

            # Find downloaded audio file
            downloaded_files = os.listdir(task_temp_dir)
            audio_file = None
            for f in downloaded_files:
                if f.startswith("audio."):
                    audio_file = os.path.join(task_temp_dir, f)
                    break
            
            if not audio_file:
                update_task(task_id, "error", 0.0, error="Audio download failed (no file found).")
                return

            # Convert to MP3
            update_task(task_id, "processing (converting to MP3)", 80.0)
            temp_mp3 = os.path.join(task_temp_dir, "output.mp3")
            if not convert_to_mp3(audio_file, temp_mp3, bitrate):
                update_task(task_id, "error", 0.0, error="Failed to convert audio to MP3 using FFmpeg.")
                return

            # Embed metadata
            update_task(task_id, "embedding thumbnail & tags", 90.0)
            embed_mp3_metadata(
                file_path=temp_mp3,
                thumbnail_path=thumbnail_path,
                title=title,
                artist=uploader,
                year=year,
                genre=genre
            )
            
            # Verify embedded artwork
            if not verify_mp3_has_artwork(temp_mp3):
                logger.warning("Cover artwork verification failed. Attempting re-embed...")
                # Try re-embedding once more
                embed_mp3_metadata(temp_mp3, thumbnail_path, title, uploader, year=year, genre=genre)

            # Finalize: Move to output folder
            update_task(task_id, "finalizing", 95.0)
            if os.path.exists(final_output_path):
                # Avoid collision by appending a uuid fragment
                final_filename = f"{sanitized_title}_{uuid.uuid4().hex[:6]}.mp3"
                final_output_path = os.path.join(output_dir, final_filename)
                
            shutil.move(temp_mp3, final_output_path)
            
        elif format_type == "mp4":
            # --- MP4 Download Workflow ---
            final_filename = f"{sanitized_title}.mp4"
            final_output_path = os.path.join(output_dir, final_filename)
            
            # Map quality (resolutions) to yt-dlp format filter
            # Prefer video with ext=mp4, and audio with ext=m4a to merge losslessly into mp4 container
            res_heights = {
                "1080": "1080",
                "720": "720",
                "480": "480"
            }
            height = res_heights.get(quality, "1080")
            
            # Select formats: video and audio
            # We download the best video stream up to requested height and the best audio stream
            # yt-dlp is extremely smart and merges them if we give merge_output_format: 'mp4'
            video_temp_template = os.path.join(task_temp_dir, "media.%(ext)s")
            
            ydl_opts_dl = {
                'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
                'outtmpl': video_temp_template,
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                # progress hook scaled from 10% to 80%
                'progress_hooks': [make_progress_hook(task_id, 10.0, 0.70)],
            }
            
            update_task(task_id, "downloading video and audio streams", 10.0)
            with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                try:
                    ydl.download([url])
                except Exception as e:
                    # Let's try downloading just 'best' if the complex format filter fails
                    logger.warning("Preferred format selection failed. Attempting fallback to general best...")
                    try:
                        ydl_opts_dl['format'] = 'best'
                        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl_fallback:
                            ydl_fallback.download([url])
                    except Exception as ex:
                        update_task(task_id, "error", 0.0, error=parse_ytdl_error(str(ex)))
                        return

            # Find the merged file or individual downloaded files
            downloaded_files = os.listdir(task_temp_dir)
            merged_file = None
            
            # Since we specified merge_output_format = mp4, yt-dlp usually produces media.mp4
            for f in downloaded_files:
                if f.endswith(".mp4") and f.startswith("media"):
                    merged_file = os.path.join(task_temp_dir, f)
                    break
                    
            # If it downloaded video and audio files separately but failed to merge
            if not merged_file:
                update_task(task_id, "processing (merging streams)", 80.0)
                video_file = None
                audio_file = None
                
                # Identify video and audio files (ignoring thumbnail/temp metadata)
                for f in downloaded_files:
                    path = os.path.join(task_temp_dir, f)
                    if f == "thumb.jpg" or f.endswith(".zip"):
                        continue
                    # Check file type using extension
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ['.mp4', '.webm', '.mkv']:
                        # Simple heuristic: video files are usually much larger than audio files
                        if not video_file or os.path.getsize(path) > os.path.getsize(video_file):
                            if video_file:
                                audio_file = video_file
                            video_file = path
                        else:
                            audio_file = path
                    elif ext in ['.m4a', '.mp3', '.ogg', '.opus', '.wav']:
                        audio_file = path
                
                if video_file and audio_file:
                    temp_mp4 = os.path.join(task_temp_dir, "output.mp4")
                    if merge_audio_video(video_file, audio_file, temp_mp4):
                        merged_file = temp_mp4
                    else:
                        update_task(task_id, "error", 0.0, error="Failed to merge audio and video streams using FFmpeg.")
                        return
                elif video_file:
                    # Video only (no audio track found)
                    merged_file = video_file
                else:
                    update_task(task_id, "error", 0.0, error="Media download failed (no playable files found).")
                    return

            # Embed MP4 metadata
            update_task(task_id, "embedding metadata & artwork", 90.0)
            temp_final_mp4 = os.path.join(task_temp_dir, "final.mp4")
            # Copy to final temp name
            shutil.copy2(merged_file, temp_final_mp4)
            embed_mp4_metadata(
                file_path=temp_final_mp4,
                thumbnail_path=thumbnail_path,
                title=title,
                artist=uploader,
                year=year
            )
            
            # Finalize: Move to output folder
            update_task(task_id, "finalizing", 95.0)
            if os.path.exists(final_output_path):
                # Avoid collision by appending a uuid fragment
                final_filename = f"{sanitized_title}_{uuid.uuid4().hex[:6]}.mp4"
                final_output_path = os.path.join(output_dir, final_filename)
                
            shutil.move(temp_final_mp4, final_output_path)
            
        else:
            update_task(task_id, "error", 0.0, error="Unsupported download format requested.")
            return

        # Verify final file exists
        if os.path.exists(final_output_path):
            update_task(task_id, "ready", 100.0, file_name=final_filename)
        else:
            update_task(task_id, "error", 0.0, error="Final processed file not found.")

    except Exception as e:
        logger.error(f"Download thread error: {e}", exc_info=True)
        update_task(task_id, "error", 0.0, error=f"An unexpected error occurred during processing: {str(e)}")
        
    finally:
        # Clean up task-specific temp files
        try:
            task_temp_dir = os.path.join(temp_dir, task_id)
            if os.path.exists(task_temp_dir):
                shutil.rmtree(task_temp_dir)
                logger.info(f"Cleaned up temporary workspace: {task_temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {task_id}: {e}")

def start_download_task(url: str, format_type: str, quality: str, temp_dir: str, output_dir: str) -> str:
    """
    Spawns a background thread to handle validation, downloading, and converting.
    Returns the task_id immediately.
    """
    task_id = str(uuid.uuid4())
    update_task(task_id, "preparing", 0.0)
    
    thread = threading.Thread(
        target=run_download_thread,
        args=(task_id, url, format_type, quality, temp_dir, output_dir),
        daemon=True
    )
    thread.start()
    return task_id
