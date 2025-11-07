import yt_dlp
import os
import shutil
import json
import sys
from contextlib import contextmanager

@contextmanager
def suppress_stdout_stderr():
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    try:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        yield
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = original_stdout
        sys.stderr = original_stderr

def setup_folders(video_id, base_output_dir="output"):
    video_dir = os.path.join(base_output_dir, "videos", video_id)
    subdirs = ["frames", "ui-screens", "os_atlas_steps"]
    
    os.makedirs(video_dir, exist_ok=True)
    
    for subdir in subdirs:
        subdir_path = os.path.join(video_dir, subdir)
        if os.path.exists(subdir_path):
            shutil.rmtree(subdir_path)
        os.makedirs(subdir_path, exist_ok=True)

def download_video(video_url, output_folder="output/videos", video_id=None):
    if video_id is None:
        from urllib.parse import urlparse, parse_qs
        import hashlib
        try:
            parsed_url = urlparse(video_url)
            if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get('v', [None])[0]
            elif parsed_url.hostname == 'youtu.be':
                video_id = parsed_url.path[1:]
        except Exception:
            pass
        
        if not video_id:
            video_id = hashlib.md5(video_url.encode()).hexdigest()[:12]
    
    video_folder = os.path.join(output_folder, video_id)
    os.makedirs(video_folder, exist_ok=True)

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": f"{video_folder}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "writeinfojson": True,
        "writethumbnail": True,
        "ignoreerrors": True,
        "extract_flat": False,
        "noplaylist": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "referer": "https://www.youtube.com/",
        "sleep_interval": 1,
        "max_sleep_interval": 5,
    }
    
    ydl_opts["cookiesfrombrowser"] = ("chrome",)

    try:
        with suppress_stdout_stderr():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
        
        video_path = None
        for f in os.listdir(video_folder):
            if f.endswith(".mp4") and info["id"] in f:
                video_path = os.path.join(video_folder, f)
                break
        
        if not video_path:
            mp4_files = [f for f in os.listdir(video_folder) if f.endswith(".mp4")]
            if mp4_files:
                video_path = os.path.join(video_folder, mp4_files[0])
        
        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            if file_size > 0:
                print(f"Video downloaded: {os.path.basename(video_path)} ({file_size / (1024*1024):.1f} MB)")
                return video_path
            else:
                os.remove(video_path)
                return None
        
    except Exception as e:
        try:
            fallback_opts = {
                "format": "best",
                "outtmpl": f"{video_folder}/%(id)s.%(ext)s",
                "force-ipv4": True,
                "quiet": True,
                "no_warnings": True
            }
            with suppress_stdout_stderr():
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    ydl.download([video_url])
            
            mp4_files = [f for f in os.listdir(video_folder) if f.endswith(".mp4")]
            if mp4_files:
                video_path = os.path.join(video_folder, mp4_files[0])
                file_size = os.path.getsize(video_path)
                if file_size > 0:
                    print(f"Video downloaded (fallback): {os.path.basename(video_path)} ({file_size / (1024*1024):.1f} MB)")
                    return video_path
                else:
                    os.remove(video_path)
                    return None
        except:
            pass

    return None