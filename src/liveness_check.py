"""
Post-processing classifier run only on YOLOv8 'person' detections.
Does not alter the YOLOv8 model or its other class outputs.

Detects whether a 'person' detection is a real human or a flat printed photo/phone screen
using two combined heuristics:
1. Rectangular Frame Contour Detection (Canny edges + 4-sided polygon check)
2. Micro-Motion Variance Analysis (rolling buffer of cropped regions per zone)
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple

# Minimum pixel variance across consecutive frames to confirm natural human motion
MIN_MOTION_VARIANCE = 5.0

# Rolling buffer storing cropped region history per zone: { zone_name: [frame1_gray, frame2_gray, ...] }
_ZONE_FRAME_BUFFERS: Dict[str, List[np.ndarray]] = {}
MAX_BUFFER_SIZE = 5


def has_rectangular_frame(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
    """
    Checks if a strong, 4-sided rectangular frame or screen border surrounds or sits
    behind the detected person/face bounding box.
    """
    if frame is None or frame.size == 0:
        return False

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox

    # Expand padding by 15% to capture any surrounding frame/bezel/border
    pad_x = int((x2 - x1) * 0.15)
    pad_y = int((y2 - y1) * 0.15)

    px1 = max(0, x1 - pad_x)
    py1 = max(0, y1 - pad_y)
    px2 = min(w, x2 + pad_x)
    py2 = min(h, y2 + pad_y)

    crop = frame[py1:py2, px1:px2]
    if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    crop_area = crop.shape[0] * crop.shape[1]

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Check contours that cover a significant portion of the cropped region (e.g. >= 15% of crop)
        if area > crop_area * 0.15:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            # A 4-sided polygon represents a rectangular photo border or phone screen frame
            if len(approx) == 4 and cv2.isContourConvex(approx):
                return True

    return False


def has_natural_motion(zone: str, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
    """
    Analyzes micro-motion pixel variance across a 5-frame rolling buffer.
    Returns True if natural movement is detected, False if static (like a held photo).
    """
    if frame is None or frame.size == 0:
        return True

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = map(int, bbox)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return True

    gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    resized_crop = cv2.resize(gray_crop, (80, 80))

    if zone not in _ZONE_FRAME_BUFFERS:
        _ZONE_FRAME_BUFFERS[zone] = []

    buffer = _ZONE_FRAME_BUFFERS[zone]
    buffer.append(resized_crop)

    if len(buffer) > MAX_BUFFER_SIZE:
        buffer.pop(0)

    # Assume real person until at least 5 frames are buffered to avoid false positives on 1st frame
    if len(buffer) < MAX_BUFFER_SIZE:
        return True

    # Calculate mean absolute pixel differences across consecutive buffered frames
    diffs = []
    for i in range(1, len(buffer)):
        abs_diff = cv2.absdiff(buffer[i], buffer[i - 1])
        diffs.append(np.mean(abs_diff))

    mean_variance = float(np.mean(diffs))

    # Real human breathing/micro-shifts yield variance >= MIN_MOTION_VARIANCE
    return mean_variance >= MIN_MOTION_VARIANCE


def classify_person_detection(zone: str, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> str:
    """
    Combines rectangular frame and micro-motion heuristics to classify a YOLOv8 person detection.
    Returns 'image' ONLY if a held static photo/screen is confirmed (both static and framed),
    ensuring real humans in front of the camera are never misclassified as an image or placed in a green box.
    """
    is_frame_present = has_rectangular_frame(frame, bbox)
    is_motion_present = has_natural_motion(zone, frame, bbox)

    # Real human moving or present in live feed is ALWAYS 'person'
    if is_motion_present:
        return "person"

    # Only classify as flat photo/screen if static AND framed
    if is_frame_present and not is_motion_present:
        return "image"

    return "person"

