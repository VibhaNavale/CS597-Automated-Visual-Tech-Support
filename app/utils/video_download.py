import yt_dlp
import os
import shutil
import json

yt_dlp.YoutubeDL().cache.remove()

def setup_folders(query_folder):
    base_dirs = ["videos", "screenshots", "metadata"]
    for base in base_dirs:
        folder_path = os.path.join(base, query_folder)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path, exist_ok=True)

def get_available_formats(video_url, query_folder):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "force-ipv4": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        os.makedirs("metadata", exist_ok=True)
        metadata_path = os.path.join("metadata", query_folder)
        os.makedirs(metadata_path, exist_ok=True)

        with open(os.path.join(metadata_path, "formats.json"), "w") as f:
            json.dump(info["formats"], f, indent=2)

        return info["formats"]

def download_video(video_url, output_folder="videos", min_height=1080):
    query_folder = os.path.basename(video_url).split("=")[-1]
    query_video_folder = os.path.join(output_folder, query_folder)
    os.makedirs(query_video_folder, exist_ok=True)

    formats = get_available_formats(video_url, query_folder)
    hd_formats = [f for f in formats if f.get("height") and f["height"] >= min_height and f.get("acodec") != "none"]

    if hd_formats:
        format_option = "bestvideo[height>=1080]+bestaudio/best[height>=1080]/bestvideo+bestaudio/best"
    else:
        format_option = "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": format_option,
        "outtmpl": f"{query_video_folder}/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "force-ipv4": True,
        "quiet": False,
        "no_warnings": False,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "writeinfojson": True,
        "writethumbnail": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.cache.remove()
            info = ydl.extract_info(video_url, download=True)
            for f in os.listdir(query_video_folder):
                if f.endswith(".mp4") and info["id"] in f:
                    return os.path.join(query_video_folder, f)
            mp4_files = [f for f in os.listdir(query_video_folder) if f.endswith(".mp4")]
            if mp4_files:
                return os.path.join(query_video_folder, mp4_files[0])
    except Exception as e:
        print(f"Error downloading video: {e}")
        fallback_opts = {
            "format": "best",
            "outtmpl": f"{query_video_folder}/%(id)s.%(ext)s",
            "force-ipv4": True
        }
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            ydl.download([video_url])
            mp4_files = [f for f in os.listdir(query_video_folder) if f.endswith(".mp4")]
            if mp4_files:
                return os.path.join(query_video_folder, mp4_files[0])

    return None
