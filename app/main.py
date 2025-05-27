from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from app.utils.youtube_search import clean_query, get_best_video
from app.utils.video_download import setup_folders, download_video
from app.utils.frame_extraction import extract_relevant_frames
from app.utils.ui_crop import extract_ui_screenshots
from app.utils.osatlas import run_osatlas
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-query")
async def process_query(query: str = Form(...)):
    query_folder = clean_query(query)
    
    best_video = get_best_video(query)
    if not best_video:
        return {"error": "No suitable video found."}

    setup_folders(query_folder)
    video_path = download_video(best_video["url"], output_folder="videos")
    if not video_path:
        return {"error": "Video download failed."}

    extract_relevant_frames(video_path)
    extract_ui_screenshots()
    result = run_osatlas(query, query_folder)
    return result
