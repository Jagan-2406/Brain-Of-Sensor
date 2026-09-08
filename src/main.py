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

def main():
    parser = argparse.ArgumentParser(description="BoS Phase 3 - Rules Engine")
    parser.add_argument('--cam', type=int, default=2, help="Camera number (1 for system built-in, 2 for external)")
    parser.add_argument('--conf', type=float, default=0.6, help="Minimum confidence threshold (e.g., 0.6)")
    parser.add_argument('--model', type=str, default='yolov8s.pt', help="YOLO model size (yolov8n.pt, yolov8s.pt, etc.)")
    args = parser.parse_args()

    # Load YOLOv8 model (will download if not present)
    model = YOLO(args.model)
    
    # OpenCV is 0-indexed, so we subtract 1 from the user's choice
    cv_cam_index = args.cam - 1
    cap = cv2.VideoCapture(cv_cam_index, cv2.CAP_DSHOW)
    
    # Force standard resolution to avoid DSHOW glitches/artifacting
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Dictionary to keep track of last event times for cooldown
    # Key: (zone, object_class_name), Value: timestamp (float)
    last_event_time = {}
    COOLDOWN_SECONDS = 3.0
    CONFIDENCE_THRESHOLD = args.conf
    
    print("Starting webcam feed with Rules Engine. Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from webcam.")
            break
            
        frame_height, frame_width = frame.shape[:2]
        
        # Run YOLOv8 inference
        results = model(frame, verbose=False)
        
        # Parse results
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Confidence score
                conf = float(box.conf[0])
                if conf < CONFIDENCE_THRESHOLD:
                    continue
                    
                # Class name
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                
                # Bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Calculate center
                x_center = (x1 + x2) / 2
                
                # Determine zone
                zone = get_zone(x_center, frame_width)
                
                # Check cooldown
                current_time = time.time()
                event_key = (zone, class_name)
                
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
                    event_dict["priority_tag_json"] = priority_tag.to_json()
                    
                    # Generate and validate plain-English summary (Phase 5)
                    raw_summary = summarize_event(priority_tag)
                    validated_summary = validate_summary(raw_summary, priority_tag)
                    event_dict["summary_text"] = validated_summary
                    
                    current_urgency = score_res["urgency"]
                    
                    log_event(event_dict)
                    print(f"Logged Event [{current_urgency.upper()}]: {zone} | {class_name} | Summary: '{validated_summary}'")
                    
                    # Update cooldown
                    last_event_time[event_key] = current_time
                
                # Color code bounding box by urgency: High=Red, Medium=Yellow, Low=Green
                if current_urgency == "high":
                    color = (0, 0, 255)
                elif current_urgency == "medium":
                    color = (0, 255, 255)
                else:
                    color = (0, 255, 0)

                # Draw bounding box and label for visualization
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{class_name} {conf:.2f} ({zone}) [{current_urgency.upper()}]"
                cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
        # Display the live feed
        cv2.imshow("BoS - Live Feed", frame)
        
        # Exit condition
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
