import cv2
import os
import numpy as np
from skimage.metrics import structural_similarity as ssim
from datetime import timedelta

def detect_phone_screen(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    max_contour = max(contours, key=cv2.contourArea)

    if cv2.contourArea(max_contour) < 0.1 * frame.shape[0] * frame.shape[1]:
        return None

    epsilon = 0.02 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)

    if len(approx) == 4:
        return approx.reshape(4, 2)

    return None

def extract_relevant_frames(video_path, output_folder="screenshots", frame_interval=15,
                           similarity_threshold=0.90, min_pixel_change_threshold=0.01,
                           output_quality=95, output_format="png"):
    query_folder = os.path.basename(os.path.dirname(video_path))
    query_screenshot_folder = os.path.join(output_folder, query_folder)
    os.makedirs(query_screenshot_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_count = 0
    screenshot_count = 0
    last_saved_frame = None

    output_ext = output_format.lower()
    if output_ext not in ["jpg", "png"]:
        output_ext = "png"

    if output_ext == "jpg":
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, output_quality]
    else:
        png_compression = min(9, max(0, 9 - int(output_quality / 10)))
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, png_compression]

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            phone_screen = detect_phone_screen(frame)
            process_frame = frame
            if phone_screen is not None:
                pass

            gray_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2GRAY)

            if last_saved_frame is None:
                save_path = os.path.join(query_screenshot_folder, f"frame_{screenshot_count+1}.{output_ext}")
                cv2.imwrite(save_path, process_frame, encode_params)
                last_saved_frame = gray_frame
                screenshot_count += 1
            else:
                try:
                    if last_saved_frame.shape != gray_frame.shape:
                        gray_frame = cv2.resize(gray_frame, (last_saved_frame.shape[1], last_saved_frame.shape[0]))
                    similarity = ssim(last_saved_frame, gray_frame)
                    pixel_diff = np.sum(np.abs(last_saved_frame.astype(float) - gray_frame.astype(float))) / \
                                (gray_frame.shape[0] * gray_frame.shape[1] * 255)

                    if (similarity < similarity_threshold) or (pixel_diff > min_pixel_change_threshold):
                        save_path = os.path.join(query_screenshot_folder, f"frame_{screenshot_count+1}.{output_ext}")
                        cv2.imwrite(save_path, process_frame, encode_params)
                        last_saved_frame = gray_frame
                        screenshot_count += 1
                except Exception as e:
                    print(f"Error processing frame {frame_count}: {e}")

        frame_count += 1

    cap.release()
    print(f"Extracted {screenshot_count} frames in '{query_screenshot_folder}'")
    return screenshot_count
