import argparse
import cv2
from ultralytics import YOLO
import datetime
import time
from zones import get_zone
from event_logger import log_event
from rules_engine import score_event
from priority_tag import build_priority_tag
from summarizer import summarize_event, validate_summary
from database import SessionLocal, Event, extract
import liveness_check

import torch

# Normalized Project Class Label Mapping
LABEL_MAP = {
    # Human mapping
    "person": "human",
    "human": "human",

    # Vehicles mapping
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "motorcycle": "vehicle",
    "bicycle": "vehicle",
    "vehicle": "vehicle",

    # Animals mapping
    "dog": "animal",
    "cat": "animal",
    "bird": "animal",
    "horse": "animal",
    "sheep": "animal",
    "cow": "animal",
    "bear": "animal",
    "elephant": "animal",
    "animal": "animal",

    # Personal Items & Furniture mapping
    "backpack": "backpack",
    "handbag": "backpack",
    "suitcase": "backpack",

    "cell phone": "cellphone",
    "cellphone": "cellphone",

    "chair": "chair",
    "sofa": "chair",
    "bench": "chair",

    "pen": "pen",
    "pencil": "pen",

    # Photo liveness classifier output
    "image": "image"
}

def main():
    parser = argparse.ArgumentParser(description="BoS Surveillance Intelligence with YOLOv11 & GPU Acceleration")
    parser.add_argument('--cam', type=int, default=1, help="Camera number (1 for system built-in, 2 for external)")
    parser.add_argument('--conf', type=float, default=0.6, help="Minimum confidence threshold (e.g., 0.6)")
    parser.add_argument('--model', type=str, default='yolo11s.pt', help="YOLOv11 model weights (yolo11n.pt, yolo11s.pt, yolo11m.pt)")
    parser.add_argument('--device', type=str, default=None, help="Inference device ('cuda' or 'cpu')")
    args = parser.parse_args()

    # Determine GPU vs CPU hardware target
    if args.device:
        device_target = args.device
    else:
        device_target = 'cuda' if torch.cuda.is_available() else 'cpu'

    if torch.cuda.is_available() and device_target != 'cpu':
        device_name = torch.cuda.get_device_name(0)
        hud_device_label = f"GPU: {device_name}"
    else:
        hud_device_label = "CPU Mode"

    # Load YOLOv11 model
    print(f"Loading YOLOv11 Model ({args.model}) on [{hud_device_label}]...")
    model = YOLO(args.model)
    
    # OpenCV is 0-indexed, so we subtract 1 from the user's choice
    cv_cam_index = args.cam - 1
    cap = cv2.VideoCapture(cv_cam_index, cv2.CAP_DSHOW)
    
    # Force standard resolution and minimum buffer size to eliminate webcam lag
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Dictionary to keep track of last event times for cooldown
    last_event_time = {}
    last_urgency = {}
    COOLDOWN_SECONDS = 3.0
    CONFIDENCE_THRESHOLD = args.conf
    
    prev_frame_time = time.time()
    
    print(f"Starting YOLOv11 webcam feed on {hud_device_label}. Press 'q' to quit.")
    
    while True:
        loop_start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from webcam.")
            break
            
        frame_height, frame_width = frame.shape[:2]
        
        # Run YOLOv11 GPU accelerated inference with precision timing
        inference_start = time.time()
        results = model(frame, device=device_target, verbose=False)
        inference_time_ms = (time.time() - inference_start) * 1000.0
        
        detection_count = 0

        # Parse results
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Confidence score
                conf = float(box.conf[0])
                if conf < CONFIDENCE_THRESHOLD:
                    continue
                    
                # Class name from YOLOv11 model
                raw_class_id = int(box.cls[0])
                raw_class_name = model.names[raw_class_id]

                # Map to normalized project label
                class_name = LABEL_MAP.get(raw_class_name, raw_class_name.lower())
                
                # Bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Calculate center
                x_center = (x1 + x2) / 2
                
                # Determine zone
                zone = get_zone(x_center, frame_width)

                # Post-processing liveness check for human detections
                if class_name in ("human", "person"):
                    class_name = liveness_check.classify_person_detection(zone, frame, (x1, y1, x2, y2))
                
                detection_count += 1

                # Check cooldown
                current_time = time.time()
                event_key = (zone, class_name)

                # Track and persist urgency per event key across cooldown frames
                high_urgency_classes = ("human", "vehicle")
                medium_urgency_classes = ("animal",)
                
                if class_name in high_urgency_classes:
                    current_urgency = "high"
                elif class_name in medium_urgency_classes:
                    current_urgency = "medium"
                elif event_key in last_urgency:
                    current_urgency = last_urgency[event_key]
                else:
                    current_urgency = "low"
                
                if event_key not in last_event_time or (current_time - last_event_time[event_key] >= COOLDOWN_SECONDS):
                    now_dt = datetime.datetime.now()
                    
                    # Calculate live count so far in current hour for this zone
                    session = SessionLocal()
                    try:
                        start_of_hour = now_dt.replace(minute=0, second=0, microsecond=0)
                        hour_count = session.query(Event).filter(
                            Event.zone == zone,
                            Event.timestamp >= start_of_hour,
                            Event.source == "real"
                        ).count()
                    except Exception:
                        hour_count = 0
                    finally:
                        session.close()

                    live_count = hour_count + 1

                    # Construct base event
                    event_dict = {
                        "timestamp": now_dt.isoformat(),
                        "zone": zone,
                        "object": class_name,
                        "confidence": round(conf, 2),
                        "source": "real"
                    }
                    
                    # Evaluate Rules Engine
                    score_res = score_event(event_dict, live_count=live_count)
                    event_dict["urgency"] = score_res["urgency"]
                    event_dict["reason_codes"] = score_res["reason_codes"]
                    event_dict["historical_avg"] = score_res["historical_average"]
                    
                    # Build formal PriorityTag (Phase 4)
                    priority_tag = build_priority_tag(event_dict, score_res)
                    priority_tag.urgency = score_res["urgency"]
                    event_dict["priority_tag_json"] = priority_tag.to_json()
                    
                    # Generate and validate plain-English summary (Phase 5)
                    raw_summary = summarize_event(priority_tag)
                    validated_summary = validate_summary(raw_summary, priority_tag)
                    event_dict["summary_text"] = validated_summary
                    
                    current_urgency = score_res["urgency"]
                    last_urgency[event_key] = current_urgency
                    
                    log_event(event_dict)
                    print(f"Logged Event [{current_urgency.upper()}]: {zone} | {class_name} | Summary: '{validated_summary}'")
                    
                    # Update cooldown
                    last_event_time[event_key] = current_time
                
                # Fixed Color Code: human/vehicle = RED (High), animal = YELLOW (Medium), others = GREEN (Low)
                if class_name in high_urgency_classes or current_urgency == "high":
                    color = (0, 0, 255) # RED for High Urgency (human, vehicle)
                    urgency_label = "HIGH"
                elif class_name in medium_urgency_classes or current_urgency == "medium":
                    color = (0, 255, 255) # Yellow for Medium Urgency (animal)
                    urgency_label = "MEDIUM"
                else:
                    color = (0, 255, 0) # Green for Low Urgency (others: pen, cellphone, chair, image, etc.)
                    urgency_label = "LOW"

                # Draw bounding box and label for visualization
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{class_name} {conf:.2f} ({zone}) [{urgency_label}]"
                cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Performance Metrics HUD Overlay
        loop_duration = time.time() - loop_start_time
        fps = 1.0 / max(loop_duration, 0.001)
        hud_text = f"YOLOv11 [{hud_device_label}] | FPS: {fps:.1f} | Inference: {inference_time_ms:.1f}ms | Detections: {detection_count}"
        cv2.rectangle(frame, (0, 0), (frame_width, 24), (15, 22, 35), -1)
        cv2.putText(frame, hud_text, (10, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
                
        # Display the live feed
        cv2.imshow("BoS - Live Feed (YOLOv11)", frame)
        
        # Exit condition
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
