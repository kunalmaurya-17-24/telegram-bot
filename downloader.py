import yt_dlp
import os

def download_video(url, download_dir):
    ydl_opts = {
        "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s"),
        "format": "bv*+ba/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]
        final_path = os.path.join(download_dir, f"{video_id}.mp4")

    return final_path
