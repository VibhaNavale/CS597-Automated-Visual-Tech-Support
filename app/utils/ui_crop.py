import cv2
import os
import numpy as np

def detect_phone_screen(image):
    original = image.copy()
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    canny = cv2.Canny(blurred, 50, 150)
    edges = cv2.bitwise_or(thresh, canny)
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    phone_contours = []

    for contour in contours[:10]:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(approx)
        if w * h < (width * height) / 20:
            continue
        if len(approx) >= 4 and len(approx) <= 8:
            aspect_ratio = h / w if w > 0 else 0
            if aspect_ratio > 1.5 and aspect_ratio < 2.5:
                phone_contours.append(approx)

    if phone_contours:
        largest = max(phone_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32)

    return None

def crop_screen_with_perspective(image, screen_contour):
    if screen_contour is None or len(screen_contour) != 4:
        return None
    ordered_points = order_points(screen_contour)
    width = int(np.linalg.norm(ordered_points[1] - ordered_points[0]))
    height = int(np.linalg.norm(ordered_points[2] - ordered_points[1]))
    dst_points = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(ordered_points, dst_points)
    cropped = cv2.warpPerspective(image, matrix, (width, height))
    return cropped

def order_points(pts):
    sorted_by_y = pts[np.argsort(pts[:, 1])]
    top_points = sorted_by_y[:2]
    bottom_points = sorted_by_y[2:]
    top_left, top_right = top_points[np.argsort(top_points[:, 0])]
    bottom_left, bottom_right = bottom_points[np.argsort(bottom_points[:, 0])]
    return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)

def extract_ui_screenshots(input_folder="screenshots", output_folder="ui-screens"):
    screenshot_dirs = os.listdir(input_folder)
    for query_folder in screenshot_dirs:
        full_input_path = os.path.join(input_folder, query_folder)
        full_output_path = os.path.join(output_folder, query_folder)
        debug_folder = os.path.join(output_folder, "debug")
        os.makedirs(full_output_path, exist_ok=True)
        os.makedirs(debug_folder, exist_ok=True)
        screenshot_files = sorted(os.listdir(full_input_path))
        for screenshot in screenshot_files:
            img_path = os.path.join(full_input_path, screenshot)
            img = cv2.imread(img_path)
            if img is None:
                continue
            screen_contour = detect_phone_screen(img)
            if screen_contour is not None:
                cropped_screen = crop_screen_with_perspective(img, screen_contour)
                if cropped_screen is not None and cropped_screen.size > 0:
                    save_path = os.path.join(full_output_path, screenshot)
                    cv2.imwrite(save_path, cropped_screen)
