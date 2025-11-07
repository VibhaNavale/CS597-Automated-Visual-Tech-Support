import cv2
import numpy as np
import os

def detect_phone_screen(frame):
    height, width = frame.shape[:2]
    aspect_ratio = width / height
    
    # Detect video orientation based on aspect ratio
    # Portrait: aspect ratio < 1 (e.g., 0.56 for 9:16 shorts)
    # Landscape: aspect ratio > 1 (e.g., 1.78 for 16:9 tutorials)
    is_portrait = aspect_ratio < 1.0
    
    if is_portrait:
        # Portrait videos (shorts) - minimal cropping, phone screen fills most of the frame
        crop_width_pct = 0.98
        crop_height_pct = 0.98
    else:
        # Landscape videos (tutorials) - more aggressive cropping to remove side margins
        crop_width_pct = 0.75
        crop_height_pct = 0.95
    
    crop_w = int(width * crop_width_pct)
    crop_h = int(height * crop_height_pct)
    
    x = (width - crop_w) // 2
    y = (height - crop_h) // 2
    
    return (x, y, crop_w, crop_h)

def crop_phone_screen(frame, phone_rect):
    if phone_rect is None:
        return frame
    
    x, y, w, h = phone_rect
    
    phone_area = frame[y:y+h, x:x+w]
    
    if phone_area.size == 0:
        return frame
    
    min_width, min_height = 200, 300
    max_width, max_height = 1200, 1800
    
    current_w, current_h = phone_area.shape[1], phone_area.shape[0]
    
    if current_w < min_width or current_h < min_height:
        scale = max(min_width / current_w, min_height / current_h)
        new_w = int(current_w * scale)
        new_h = int(current_h * scale)
        phone_area = cv2.resize(phone_area, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    elif current_w > max_width or current_h > max_height:
        scale = min(max_width / current_w, max_height / current_h)
        new_w = int(current_w * scale)
        new_h = int(current_h * scale)
        phone_area = cv2.resize(phone_area, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return phone_area

def extract_ui_screenshots(input_folder="output/videos", output_folder="output/videos", video_id=None):
    if video_id is None:
        video_dirs = os.listdir(input_folder)
        for vd in video_dirs:
            if os.path.isdir(os.path.join(input_folder, vd)):
                extract_ui_screenshots(input_folder, output_folder, vd)
        return
    
    input_path = os.path.join(input_folder, video_id, "frames")
    output_path = os.path.join(output_folder, video_id, "ui-screens")
    os.makedirs(output_path, exist_ok=True)
    
    if not os.path.exists(input_path):
        print(f"Input folder {input_path} does not exist")
        return
    
    frame_files = sorted([f for f in os.listdir(input_path) if f.startswith("frame_")])
    successful = 0
    failed = 0
    
    print(f"UI screen extraction started: processing {len(frame_files)} frames")
    
    for frame_file in frame_files:
        img_path = os.path.join(input_path, frame_file)
        img = cv2.imread(img_path)
        
        if img is None:
            failed += 1
            continue
        
        phone_rect = detect_phone_screen(img)
        cropped_screen = crop_phone_screen(img, phone_rect)
        
        if cropped_screen is not None and cropped_screen.size > 0:
            output_file = os.path.join(output_path, frame_file)
            cv2.imwrite(output_file, cropped_screen, [cv2.IMWRITE_JPEG_QUALITY, 95])
            successful += 1
        else:
            failed += 1
    
    print(f"UI screen extraction completed: {successful} successful, {failed} failed")