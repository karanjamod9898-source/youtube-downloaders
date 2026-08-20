import os
import subprocess
import logging
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TYER, TCON, error
from mutagen.mp4 import MP4, MP4Cover

logger = logging.getLogger("youtube_downloader")

def run_ffmpeg_command(cmd: list) -> bool:
    """
    Run an FFmpeg command using subprocess safely.
    """
    try:
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg command failed with exit code {e.returncode}")
        logger.error(f"FFmpeg Stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"FFmpeg execution failed: {e}")
        return False

def convert_to_mp3(input_path: str, output_path: str, bitrate: str = "320k") -> bool:
    """
    Converts any audio file to MP3 with the specified bitrate.
    """
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output files without asking
        "-i", input_path,   # Input file
        "-b:a", bitrate,    # Audio bitrate (e.g. 320k, 256k, 192k)
        "-vn",              # Disable video recording
        output_path
    ]
    return run_ffmpeg_command(cmd)

def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Merges separate video and audio files into a single MP4 file.
    Tries to copy streams first (lossless & fast). If it fails, transcodes audio to AAC.
    """
    # Try copying both streams first
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        output_path
    ]
    
    success = run_ffmpeg_command(cmd)
    if not success:
        logger.warning("Lossless merge copy failed. Retrying with audio transcoding to AAC...")
        # Fallback: copy video, encode audio to AAC
        cmd_fallback = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        success = run_ffmpeg_command(cmd_fallback)
        
    return success

def embed_mp3_metadata(
    file_path: str,
    thumbnail_path: str,
    title: str,
    artist: str,
    album: str = "YouTube Downloads",
    year: str = None,
    genre: str = "YouTube"
) -> bool:
    """
    Embeds metadata and cover artwork into an MP3 file using mutagen.
    """
    try:
        try:
            audio = MP3(file_path, ID3=ID3)
        except error:
            audio = MP3(file_path)
            audio.add_tags()
            
        tags = audio.tags
        if tags is None:
            audio.add_tags()
            tags = audio.tags

        # Set text frames (use encoding=1 UTF-16 for ID3v2.3 Windows Explorer compatibility)
        tags.add(TIT2(encoding=1, text=title))       # Title
        tags.add(TPE1(encoding=1, text=artist))      # Artist / Uploader
        tags.add(TALB(encoding=1, text=album))       # Album
        tags.add(TCON(encoding=1, text=genre))       # Genre
        if year:
            tags.add(TYER(encoding=1, text=str(year))) # Year

        # Embed cover artwork
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as img:
                img_data = img.read()
                
            mime = 'image/jpeg'
            if thumbnail_path.lower().endswith('.png'):
                mime = 'image/png'
                
            tags.add(APIC(
                encoding=1,
                mime=mime,
                type=3,  # Cover Front
                desc=u'Cover',
                data=img_data
            ))
            
        audio.save(v2_version=3)
        logger.info(f"Successfully embedded MP3 metadata and ID3v2.3 artwork for {os.path.basename(file_path)}")
        return True
    except Exception as e:
        logger.error(f"Failed to embed MP3 metadata: {e}")
        return False

def embed_mp4_metadata(
    file_path: str,
    thumbnail_path: str,
    title: str,
    artist: str,
    album: str = "YouTube Downloads",
    year: str = None
) -> bool:
    """
    Embeds metadata and cover artwork into an MP4 file using mutagen.
    """
    try:
        video = MP4(file_path)
        
        # Set iTunes standard metadata tags
        video["\xa9nam"] = [title]
        video["\xa9ART"] = [artist]
        video["\xa9alb"] = [album]
        if year:
            video["\xa9day"] = [str(year)]
            
        # Embed cover artwork
        if thumbnail_path and os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as img:
                img_data = img.read()
                
            cover_format = MP4Cover.FORMAT_JPEG
            if thumbnail_path.lower().endswith('.png'):
                cover_format = MP4Cover.FORMAT_PNG
                
            video["covr"] = [MP4Cover(img_data, cover_format)]
            
        video.save()
        logger.info(f"Successfully embedded MP4 metadata and artwork for {os.path.basename(file_path)}")
        return True
    except Exception as e:
        logger.error(f"Failed to embed MP4 metadata: {e}")
        return False

def verify_mp3_has_artwork(file_path: str) -> bool:
    """
    Verifies that the MP3 file contains valid embedded cover artwork.
    """
    try:
        audio = MP3(file_path, ID3=ID3)
        if audio.tags:
            # Look for APIC frame (Attached Picture)
            has_apic = any(key.startswith("APIC") for key in audio.tags.keys())
            return has_apic
        return False
    except Exception as e:
        logger.error(f"Failed to verify MP3 artwork: {e}")
        return False
