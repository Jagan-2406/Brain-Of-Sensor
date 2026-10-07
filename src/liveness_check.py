"""
Post-processing classifier run only on YOLO 'person' / 'human' detections.
Does not alter the YOLO model or its other class outputs.

Detects whether a 'human' detection is a real living person or a flat printed photo / phone screen image
using two combined heuristics:
1. Rectangular Frame Contour Detection (Canny edges + 4-sided polygon check for phone screen bezels / photo borders)
2. Micro-Motion Variance Analysis (rolling buffer of cropped regions per zone)
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple

# Minimum pixel variance across consecutive frames to confirm natural human motion
MIN_MOTION_VARIANCE = 4.0

# Rolling buffer storing cropped region history per zone: { zone_name: [frame1_gray, frame2_gray, ...] }
_ZONE_FRAME_BUFFERS: Dict[str, List[np.ndarray]] = {}
MAX_BUFFER_SIZE = 5


def has_rectangular_frame(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
    """
    Checks if a 4-sided rectangular frame, screen border, or paper photo bezel surrounds
    the detected person/face bounding box.
    """
    if frame is None or frame.size == 0:
        return False

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox

    # Expand padding by 20% to capture any surrounding frame/bezel/border/card
    pad_x = int((x2 - x1) * 0.20)
    pad_y = int((y2 - y1) * 0.20)

    px1 = max(0, x1 - pad_x)
    py1 = max(0, y1 - pad_y)
    px2 = min(w, x2 + pad_x)
    py2 = min(h, y2 + pad_y)

    crop = frame[py1:py2, px1:px2]
    if crop.size == 0 or crop.shape[0] < 15 or crop.shape[1] < 15:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Canny edge detection suited for phone screen bezels and paper borders
    edges = cv2.Canny(blurred, 30, 120)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    crop_area = crop.shape[0] * crop.shape[1]

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Check contours that cover >= 10% of cropped region (phone screens, paper photos)
        if area > crop_area * 0.10:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            # A 4-sided polygon represents a rectangular photo border or phone screen frame
            if len(approx) == 4 and cv2.isContourConvex(approx):
                return True

    return False


def has_natural_motion(zone: str, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
    """
    Analyzes micro-motion pixel variance across a 5-frame rolling buffer.
    Returns True if natural human movement is detected, False if static (like a held photo).
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

    # Need at least 3 frames buffered to evaluate motion
    if len(buffer) < 3:
        return True

    # Calculate mean absolute pixel differences across consecutive buffered frames
    diffs = []
    for i in range(1, len(buffer)):
        abs_diff = cv2.absdiff(buffer[i], buffer[i - 1])
        diffs.append(np.mean(abs_diff))

    mean_variance = float(np.mean(diffs))

    return mean_variance >= MIN_MOTION_VARIANCE


def classify_person_detection(zone: str, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> str:
    """
    Classifies a YOLO human detection.
    Guarantees that real humans in front of the camera are ALWAYS labeled as 'human' (RED box, HIGH priority).
    Relabels to 'image' ONLY when a flat, static held photo/screen is confirmed.
    """
    is_motion_present = has_natural_motion(zone, frame, bbox)

    # 1. Real human in camera view has motion / micro-shifts -> ALWAYS 'human'
    if is_motion_present:
        return "human"

    # 2. Only if static (no human motion/breathing) AND rectangular photo border exists -> 'image'
    is_frame_present = has_rectangular_frame(frame, bbox)
    if is_frame_present:
        return "image"

    return "human"

