from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.utils.youtube_search import clean_query, get_best_video
from app.utils.video_download import setup_folders, download_video
from app.utils.frame_extraction import extract_relevant_frames
from app.utils.ui_crop import extract_ui_screenshots
from app.utils.osatlas import run_osatlas, run_osatlas_with_progress
from app.utils.cache import extract_video_id, get_cached_video_result, cache_video_result, is_video_cached
import os
import json
import asyncio
import time

app = FastAPI(root_path="/api-vnava22")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def save_performance_metrics(video_id: str, query: str, step: str, duration: float, additional_data: Dict[str, Any] = None):
    test_dir = f"test/{video_id}"
    os.makedirs(test_dir, exist_ok=True)
    
    metrics_file = os.path.join(test_dir, "performance_metrics.json")
    
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
    else:
        metrics = {
            "video_id": video_id,
            "query": query,
            "created_at": datetime.now().isoformat(),
            "timing": {},
            "video_metadata": {},
            "frame_extraction": {},
            "osatlas_processing": {},
            "system_efficiency": {},
            "step_count": 0,
            "frame_count": 0,
            "total_steps_generated": 0
        }
    
    metrics["timing"][step] = {"duration": duration}
    metrics["last_updated"] = datetime.now().isoformat()
    
    if additional_data:
        if "video_metadata" in additional_data:
            metrics["video_metadata"].update(additional_data["video_metadata"])
        if "frame_extraction" in additional_data:
            metrics["frame_extraction"].update(additional_data["frame_extraction"])
        if "osatlas_processing" in additional_data:
            metrics["osatlas_processing"].update(additional_data["osatlas_processing"])
        if "system_efficiency" in additional_data:
            metrics["system_efficiency"].update(additional_data["system_efficiency"])
        if "frame_count" in additional_data:
            metrics["frame_count"] = additional_data["frame_count"]
        if "step_count" in additional_data:
            metrics["total_steps_generated"] = additional_data["step_count"]
    
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

@app.options("/process-query-stream")
async def options_handler():
    return {"message": "OK"}

async def process_query_with_progress(query: str):
    print(f"\n{'='*80}\nPROCESSING QUERY: {query}\n{'='*80}")
    
    timing_metrics = {}
    overall_start = time.time()
    
    def send_progress(step: str, status: str, message: str = "", data: dict = None):
        progress_data = {
            "step": step,
            "status": status,
            "message": message,
            "data": data or {}
        }
        return f"data: {json.dumps(progress_data)}\n\n"
    
    yield send_progress("connection", "connected", "Connected to analysis stream")
    
    time.sleep(0.1)
    
    search_start = time.time()
    yield send_progress("video-search", "active", "Searching for relevant video...")
    best_video = get_best_video(query)
    search_end = time.time()
    search_duration = round(search_end - search_start, 2)
    
    if not best_video:
        yield send_progress("video-search", "error", "No suitable video found.")
        return
    
    video_id = extract_video_id(best_video['url'])
    timing_metrics["video-search"] = {"duration": search_duration}
    
    yield send_progress("video-search", "completed", f"Found video: {best_video['title']}", {
        "video_id": video_id,
        "title": best_video.get('title', ''),
        "url": best_video.get('url', ''),
        "duration_seconds": best_video.get('duration_seconds', 0),
        "views": best_video.get('views', 0)
    })
    
    video_metadata = {
        "duration_seconds": best_video.get("duration_seconds", 0),
        "views": best_video.get("views", 0),
        "resolution": best_video.get("definition", "unknown"),
        "relevance_score": best_video.get("relevance_score", 0),
        "title": best_video.get("title", ""),
        "url": best_video.get("url", "")
    }
    
    save_performance_metrics(video_id, query, "video-search", search_duration, {
        "video_metadata": video_metadata
    })
    
    cache_hit = is_video_cached(video_id)
    
    if cache_hit:
        print(f"Cache hit - using cached results for video: {video_id}")
        cached_result = get_cached_video_result(video_id)
        if cached_result:
            timing_metrics["video-download"] = {"duration": 0.01}
            timing_metrics["frame-extraction"] = {"duration": 0.01}
            timing_metrics["ui-screens"] = {"duration": 0.01}
            timing_metrics["osatlas-processing"] = {"duration": 0.01}
            overall_end = time.time()
            timing_metrics["total"] = {"duration": round(overall_end - overall_start, 2)}
            
            video_metadata = {
                "duration_seconds": best_video.get("duration_seconds", 0),
                "views": best_video.get("views", 0),
                "resolution": best_video.get("definition", "unknown"),
                "relevance_score": best_video.get("relevance_score", 0),
                "title": best_video.get("title", ""),
                "url": best_video.get("url", "")
            }
            
            save_performance_metrics(video_id, query, "video-search", search_duration, {
                "video_metadata": video_metadata,
                "system_efficiency": {"cache_hit": True}
            })
            save_performance_metrics(video_id, query, "video-download", 0.01)
            save_performance_metrics(video_id, query, "frame-extraction", 0.01)
            save_performance_metrics(video_id, query, "ui-screens", 0.01)
            save_performance_metrics(video_id, query, "osatlas-processing", 0.01, {"step_count": len(cached_result)})
            save_performance_metrics(video_id, query, "total", timing_metrics["total"]["duration"])
            
            yield send_progress("video-download", "completed", "Using cached video")
            yield send_progress("frame-extraction", "completed", "Using cached frames")
            yield send_progress("ui-screens", "completed", "Using cached UI screens")
            yield send_progress("osatlas-processing", "completed", f"Loaded {len(cached_result)} cached steps")
            yield send_progress("complete", "success", f"Analysis complete with {len(cached_result)} cached steps", {"results": cached_result, "timing": timing_metrics, "video_id": video_id, "query": query})
            return
    
    try:
        download_start = time.time()
        yield send_progress("video-download", "active", f"Downloading video: {best_video['title']}")
        setup_folders(video_id, "output")
        video_path = download_video(best_video["url"], output_folder="output/videos", video_id=video_id)
        download_end = time.time()
        download_duration = round(download_end - download_start, 2)
        timing_metrics["video-download"] = {"duration": download_duration}
        
        if not video_path:
            yield send_progress("video-download", "error", "Failed to download video.")
            return
        
        save_performance_metrics(video_id, query, "video-download", download_duration)
        yield send_progress("video-download", "completed", f"Video downloaded successfully")
        
        frame_start = time.time()
        yield send_progress("frame-extraction", "active", "Extracting relevant frames...")
        try:
            import threading
            from queue import Queue
            
            result_queue = Queue()
            error_queue = Queue()
            
            def extract_frames_thread():
                try:
                    result = extract_relevant_frames(video_path, output_folder="output/videos", video_id=video_id)
                    result_queue.put(result)
                except Exception as e:
                    error_queue.put(e)
            
            extraction_thread = threading.Thread(target=extract_frames_thread)
            extraction_thread.start()
            
            while extraction_thread.is_alive():
                yield send_progress("frame-extraction", "active", "Processing frames...")
                await asyncio.sleep(10)
            
            if not error_queue.empty():
                error = error_queue.get()
                raise error
            
            frame_result = result_queue.get()
            frame_end = time.time()
            frame_duration = round(frame_end - frame_start, 2)
            timing_metrics["frame-extraction"] = {"duration": frame_duration}
            
            if isinstance(frame_result, tuple):
                frame_count, frame_metrics = frame_result
            else:
                frame_count = frame_result
                frame_metrics = {}
            
            save_performance_metrics(video_id, query, "frame-extraction", frame_duration, {
                "frame_count": frame_count,
                "frame_extraction": frame_metrics
            })
            yield send_progress("frame-extraction", "completed", f"Extracted {frame_count} frames")
            
        except Exception as e:
            yield send_progress("frame-extraction", "error", f"Frame extraction failed: {str(e)}")
            return
        
        ui_start = time.time()
        yield send_progress("ui-screens", "active", "Extracting UI screens...")
        extract_ui_screenshots(input_folder="output/videos", output_folder="output/videos", video_id=video_id)
        ui_end = time.time()
        ui_duration = round(ui_end - ui_start, 2)
        timing_metrics["ui-screens"] = {"duration": ui_duration}
        
        save_performance_metrics(video_id, query, "ui-screens", ui_duration)
        yield send_progress("ui-screens", "completed", "UI screens extracted successfully")
        
        osatlas_start = time.time()
        yield send_progress("osatlas-processing", "active", "Running OS-Atlas analysis...")
        
        try:
            result_queue = Queue()
            error_queue = Queue()
            progress_queue = Queue()
            
            def progress_handler(step, status, message):
                progress_queue.put((step, status, message))
            
            def osatlas_thread():
                try:
                    result = run_osatlas_with_progress(query, video_id, yield_progress=progress_handler)
                    if isinstance(result, tuple):
                        result_queue.put(result)
                    else:
                        result_queue.put((result, {}))
                except Exception as e:
                    error_queue.put(e)
            
            osatlas_thread_obj = threading.Thread(target=osatlas_thread)
            osatlas_thread_obj.start()
            
            while osatlas_thread_obj.is_alive() or not progress_queue.empty():
                if not progress_queue.empty():
                    step, status, message = progress_queue.get()
                    yield send_progress(step, status, message)
                
                await asyncio.sleep(0.1)
            
            osatlas_thread_obj.join()
            
            if not error_queue.empty():
                error = error_queue.get()
                raise error
            
            osatlas_result = result_queue.get()
            osatlas_end = time.time()
            osatlas_duration = round(osatlas_end - osatlas_start, 2)
            timing_metrics["osatlas-processing"] = {"duration": osatlas_duration}
            
            if isinstance(osatlas_result, tuple):
                result, osatlas_metrics = osatlas_result
            else:
                result = osatlas_result
                osatlas_metrics = {}
            
            try:
                from app.utils.osatlas import check_gpu_memory
                has_memory, memory_info = check_gpu_memory()
                gpu_memory = {
                    "has_sufficient_memory": has_memory,
                    "memory_info": memory_info
                }
            except:
                gpu_memory = {}
            
            save_performance_metrics(video_id, query, "osatlas-processing", osatlas_duration, {
                "step_count": len(result),
                "osatlas_processing": osatlas_metrics,
                "system_efficiency": {
                    "cache_hit": False,
                    "gpu_memory": gpu_memory
                }
            })
            yield send_progress("osatlas-processing", "completed", f"Generated {len(result)} steps")
            
            cache_video_result(video_id, result)
            
        except Exception as e:
            yield send_progress("osatlas-processing", "error", f"OS-Atlas processing failed: {str(e)}")
            return
        
        overall_end = time.time()
        total_duration = round(overall_end - overall_start, 2)
        timing_metrics["total"] = {"duration": total_duration}
        
        save_performance_metrics(video_id, query, "total", total_duration)
        print(f"Analysis complete: {len(result)} steps generated in {total_duration}s")
        yield send_progress("complete", "success", f"Analysis complete with {len(result)} steps", {"results": result, "timing": timing_metrics, "video_id": video_id, "query": query})
        yield "data: {\"step\": \"stream-end\", \"status\": \"closed\"}\n\n"
        
    except Exception as e:
        yield send_progress("error", "error", f"Analysis failed: {str(e)}")
        yield "data: {\"step\": \"stream-end\", \"status\": \"error\"}\n\n"

@app.post("/process-query")
async def process_query(query: str = Form(...)):
    best_video = get_best_video(query)
    if not best_video:
        return {"error": "No suitable video found."}
    
    video_id = extract_video_id(best_video["url"])
    setup_folders(video_id, "output")
    
    video_path = download_video(best_video["url"], output_folder="output/videos", video_id=video_id)
    if not video_path:
        return {"error": "Video download failed."}

    extract_relevant_frames(video_path, output_folder="output/videos", video_id=video_id)
    extract_ui_screenshots(input_folder="output/videos", output_folder="output/videos", video_id=video_id)
    result = run_osatlas(query, video_id)
    return result

@app.get("/process-query-stream")
async def process_query_stream(query: str):
    return StreamingResponse(
        process_query_with_progress(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "X-Content-Type-Options": "nosniff",
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/memory")
async def memory_check():
    try:
        from app.utils.osatlas import check_gpu_memory
        has_memory, memory_info = check_gpu_memory()
        return {
            "status": "healthy" if has_memory else "low_memory",
            "memory_info": memory_info,
            "has_sufficient_memory": has_memory
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/images/{video_id}/{step_folder}/{filename}")
async def get_step_image(video_id: str, step_folder: str, filename: str):
    image_path = f"./output/videos/{video_id}/os_atlas_steps/{step_folder}/{filename}"
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path, media_type="image/jpeg")

@app.get("/cache/stats")
async def get_cache_stats():
    cache_dir = "output/video_cache"
    if os.path.exists(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
        return {
            "cached_videos": len(cache_files),
            "cache_directory": cache_dir
        }
    return {"cached_videos": 0, "cache_directory": cache_dir}

@app.post("/cache/clear")
async def clear_cache():
    import shutil
    cache_dir = "output/video_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir, exist_ok=True)
    return {"message": "Cache cleared successfully"}

@app.get("/")
async def root():
    return {"message": "API is running", "root_path": "/api-vnava22"}

class AccuracyMetricsData(BaseModel):
    video_id: str
    query: str
    correct: int
    incorrect: int
    not_needed: int
    missing: int
    total: int
    accuracy: float
    step_qualities: list = []
    bbox_verifications: list

@app.post("/save-accuracy-metrics")
async def save_accuracy_metrics(metrics: AccuracyMetricsData):
    try:
        test_dir = f"test/{metrics.video_id}"
        os.makedirs(test_dir, exist_ok=True)
        
        metrics_file = os.path.join(test_dir, "accuracy_metrics.json")
        
        step_quality_counts = {}
        if metrics.step_qualities:
            for sq in metrics.step_qualities:
                quality = sq.get('quality')
                if quality:
                    step_quality_counts[quality] = step_quality_counts.get(quality, 0) + 1
        
        metrics_data = {
            "video_id": metrics.video_id,
            "query": metrics.query,
            "timestamp": datetime.now().isoformat(),
            "test_metrics": {
                "correct": metrics.correct,
                "incorrect": metrics.incorrect,
                "not_needed": metrics.not_needed,
                "missing": metrics.missing,
                "total": metrics.total,
                "accuracy": metrics.accuracy
            },
            "step_quality_assessment": {
                "counts": step_quality_counts,
                "total_assessed": len([sq for sq in metrics.step_qualities if sq.get('quality')]),
                "details": metrics.step_qualities
            },
            "bbox_verifications": metrics.bbox_verifications
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        return {
            "success": True,
            "message": f"Accuracy metrics saved to {metrics_file}",
            "filepath": metrics_file
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save accuracy metrics: {str(e)}")
