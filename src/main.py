import argparse
import cv2
from ultralytics import YOLO
import datetime
import time
from zones import get_zone
from event_logger import log_event

def main():
    parser = argparse.ArgumentParser(description="BoS Phase 1")
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
    
    print("Starting webcam feed. Press 'q' to quit.")
    
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
                
                if event_key not in last_event_time or (current_time - last_event_time[event_key] >= COOLDOWN_SECONDS):
                    # Construct and log event
                    event_dict = {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "zone": zone,
                        "object": class_name,
                        "confidence": round(conf, 2),
                        "source": "real"
                    }
                    log_event(event_dict)
                    print(f"Logged event: {event_dict}")
                    
                    # Update cooldown
                    last_event_time[event_key] = current_time
                
                # Draw bounding box and label for visualization
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{class_name} {conf:.2f} ({zone})"
                cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
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
