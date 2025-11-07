import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import os
import time
import warnings
import sys
from contextlib import contextmanager

@contextmanager
def suppress_stderr():
    original_stderr = sys.stderr
    original_stderr_fd = None
    devnull_fd = None
    try:
        original_stderr_fd = sys.stderr.fileno()
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, original_stderr_fd)
        sys.stderr = open(os.devnull, 'w')
        yield
    except (AttributeError, ValueError, OSError):
        try:
            sys.stderr = open(os.devnull, 'w')
        except:
            pass
        yield
    finally:
        if devnull_fd is not None:
            try:
                os.close(devnull_fd)
            except:
                pass
        sys.stderr.close()
        sys.stderr = original_stderr
        if original_stderr_fd is not None:
            try:
                os.dup2(original_stderr_fd, 2)
            except:
                pass

def is_good_frame(frame, last_frame=None, ssim_threshold=0.98):
    if last_frame is None:
        return True, "first_frame"
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    last_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
    
    if gray.shape != last_gray.shape:
        last_gray = cv2.resize(last_gray, (gray.shape[1], gray.shape[0]))
    
    similarity = ssim(gray, last_gray, data_range=255)
    
    if similarity > ssim_threshold:
        return False, f"too_similar_{similarity:.3f}"
    
    return True, "good"

def extract_relevant_frames(video_path, output_folder="output/videos", video_id=None):
    if video_id is None:
        video_id = os.path.basename(os.path.dirname(video_path))
    
    output_path = os.path.join(output_folder, video_id, "frames")
    os.makedirs(output_path, exist_ok=True)

    saved_count = 0
    examined_count = 0
    duplicate_count = 0
    ssim_scores = []
    
    start_time = time.time()
    
    with suppress_stderr():
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        target_frames = 15
        if duration <= 30:
            target_frames = 15
        elif duration <= 60:
            target_frames = 20
        elif duration <= 90:
            target_frames = 25
        else:
            target_frames = 30
        
        frame_interval = max(1, int(total_frames / target_frames))
        frames_to_examine = list(range(0, total_frames, frame_interval))
        
        print(f"Frame extraction started: {duration:.1f}s video ({total_frames} total frames at {fps:.1f} fps)")
        print(f"Using frame interval: {frame_interval} (sampling every {frame_interval/fps:.1f}s)")

        print("Calculating adaptive SSIM threshold")
        sample_ssim_scores = []
        prev_frame = None
        
        sample_indices = []
        if len(frames_to_examine) > 1:
            sample_count = min(25, len(frames_to_examine))
            step = max(1, len(frames_to_examine) // sample_count)
            sample_indices = list(range(0, len(frames_to_examine), step))[:sample_count]
        else:
            sample_indices = [0]
        
        for idx in sample_indices:
            if idx >= len(frames_to_examine):
                break
            frame_number = frames_to_examine[idx]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                break
            
            if prev_frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                if gray.shape != prev_gray.shape:
                    prev_gray = cv2.resize(prev_gray, (gray.shape[1], gray.shape[0]))
                similarity = ssim(gray, prev_gray, data_range=255)
                sample_ssim_scores.append(similarity)
            
            prev_frame = frame
        
        force_time_based = False
        time_based_interval = 1.0
        
        if sample_ssim_scores:
            avg_ssim = sum(sample_ssim_scores) / len(sample_ssim_scores)
            min_ssim = min(sample_ssim_scores)
            max_ssim = max(sample_ssim_scores)
            
            if avg_ssim >= 0.98:
                force_time_based = True
                time_based_interval = max(0.5, min(2.0, duration / target_frames))
                print(f"SSIM stats: min={min_ssim:.3f}, max={max_ssim:.3f}, avg={avg_ssim:.3f} - Using time-based extraction with {time_based_interval:.2f}s interval")
            elif avg_ssim >= 0.97:
                force_time_based = True
                time_based_interval = max(0.5, min(2.5, duration / target_frames))
                print(f"SSIM stats: min={min_ssim:.3f}, max={max_ssim:.3f}, avg={avg_ssim:.3f} - Using time-based extraction with {time_based_interval:.2f}s interval")
            elif avg_ssim >= 0.995:
                adaptive_threshold = 0.985
                print(f"SSIM stats: min={min_ssim:.3f}, max={max_ssim:.3f}, avg={avg_ssim:.3f}, adaptive threshold: {adaptive_threshold:.3f}")
            elif avg_ssim >= 0.99:
                adaptive_threshold = 0.975
                print(f"SSIM stats: min={min_ssim:.3f}, max={max_ssim:.3f}, avg={avg_ssim:.3f}, adaptive threshold: {adaptive_threshold:.3f}")
            elif avg_ssim >= 0.93:
                adaptive_threshold = min(0.982, max(0.97, avg_ssim + 0.03))
                print(f"SSIM stats: min={min_ssim:.3f}, max={max_ssim:.3f}, avg={avg_ssim:.3f}, adaptive threshold: {adaptive_threshold:.3f}")
                print(f"Note: Threshold accounts for higher similarity during extraction (compared to sampled frames)")
            else:
                adaptive_threshold = min(0.985, max(0.93, avg_ssim + 0.02))
                print(f"SSIM stats: min={min_ssim:.3f}, max={max_ssim:.3f}, avg={avg_ssim:.3f}, adaptive threshold: {adaptive_threshold:.3f}")
        else:
            adaptive_threshold = 0.985
            print(f"Could not calculate average SSIM, using default threshold: {adaptive_threshold:.3f}")
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        last_saved_frame = None
        last_saved_time = -1
        
        for frame_number in frames_to_examine:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                break
            
            examined_count += 1
            current_time = frame_number / fps if fps > 0 else 0
            
            if force_time_based:
                time_since_last = current_time - last_saved_time
                if last_saved_frame is None or time_since_last >= time_based_interval:
                    frame_filename = f"frame_{saved_count:03d}.jpg"
                    frame_path = os.path.join(output_path, frame_filename)
                    cv2.imwrite(frame_path, frame)
                    saved_count += 1
                    last_saved_frame = frame
                    last_saved_time = current_time
                else:
                    duplicate_count += 1
            else:
                is_good, reason = is_good_frame(frame, last_saved_frame, adaptive_threshold)
                
                if "too_similar" in reason:
                    duplicate_count += 1
                    ssim_score = float(reason.split("_")[-1])
                    ssim_scores.append(ssim_score)
                
                if is_good:
                    frame_filename = f"frame_{saved_count:03d}.jpg"
                    frame_path = os.path.join(output_path, frame_filename)
                    cv2.imwrite(frame_path, frame)
                    saved_count += 1
                    last_saved_frame = frame
                    last_saved_time = current_time
        
        cap.release()
    
    processing_time = time.time() - start_time
    avg_ssim = sum(ssim_scores) / len(ssim_scores) if ssim_scores else 0
    frames_per_minute = (saved_count / duration * 60) if duration > 0 else 0
    duplicate_rate = (duplicate_count / examined_count * 100) if examined_count > 0 else 0
    
    print(f"Frame extraction completed: {saved_count} frames in {processing_time:.1f}s")
    print(f"Statistics: {examined_count} frames examined (out of {total_frames} total), {duplicate_count} duplicates filtered ({duplicate_rate:.1f}%), avg SSIM: {avg_ssim:.3f}")
    
    metrics = {
        "frame_count": saved_count,
        "frames_examined": examined_count,
        "duplicate_frames_filtered": duplicate_count,
        "duplicate_rate_percent": round(duplicate_rate, 2),
        "average_ssim_score": round(avg_ssim, 3),
        "frames_per_minute": round(frames_per_minute, 2),
        "video_duration_seconds": round(duration, 2)
    }
    
    return saved_count, metrics

def extract_frames_legacy(video_path, output_folder="frames", query_folder=None):
    result = extract_relevant_frames(video_path, output_folder, query_folder)
    if isinstance(result, tuple):
        return result[0]
    return result