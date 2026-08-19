# Brain of Sensors (BoS) — Phase 1 Build Document
### Scope: Webcam → YOLOv8 Detection → Zone Logging (detection layer only)
### Target: Google Antigravity (agentic step-by-step execution)

---

## Phase 1 Objective

Build the detection layer only. Given a live webcam feed, detect objects in real time, assign each detection to a manually defined zone, and log it as a structured event. No rules engine, no LLM, no dashboard, no priority tagging in this phase — those are later phases.

**Definition of done:** running the project prints/stores a live event every time a person (or other object) is detected on webcam, with the correct zone, object type, and timestamp.

---

## Step 1 — Project Setup

**Task for agent:**
1. Create a new project folder: `bos-phase1/`
2. Initialize a Python virtual environment inside it
3. Create a `requirements.txt` with:
   ```
   ultralytics
   opencv-python
   pandas
   ```
4. Install all dependencies into the virtual environment
5. Create the following empty file structure:
   ```
   bos-phase1/
     ├── main.py
     ├── zones.py
     ├── event_logger.py
     ├── requirements.txt
     └── events.csv   (created empty, header only)
   ```

**Success check:** `pip list` inside the venv shows `ultralytics`, `opencv-python`, and `pandas` installed without errors.

---

## Step 2 — Webcam Capture

**Task for agent:**
1. In `main.py`, write code to open the default webcam using OpenCV (`cv2.VideoCapture(0)`)
2. Display the live feed in a window as a basic sanity check (no detection yet)
3. Add a clean exit condition (press `q` to close the window and release the camera)

**Success check:** running `python main.py` opens a window showing the live webcam feed, and pressing `q` closes it cleanly with no errors or hanging processes.

---

## Step 3 — Zone Definition

**Task for agent:**
1. In `zones.py`, define a function `get_zone(x_center, frame_width)` that:
   - Takes the horizontal center point of a detected object and the frame width
   - Returns `"zone_1"` if the point is in the left half of the frame
   - Returns `"zone_2"` if the point is in the right half of the frame
2. Keep this simple and hardcoded for Phase 1 — no need for configurable zone shapes yet
3. Import this function into `main.py` for use in Step 4

**Success check:** a quick standalone test (e.g. `get_zone(100, 640)` returns `zone_1`, `get_zone(500, 640)` returns `zone_2`) passes correctly.

---

## Step 4 — YOLOv8 Object Detection

**Task for agent:**
1. In `main.py`, load a pretrained YOLOv8 model from `ultralytics` (use the smallest model variant for real-time CPU performance)
2. For every frame captured from the webcam:
   - Run YOLOv8 inference on the frame
   - For each detected object, extract: object class name, confidence score, and bounding box coordinates
   - Filter detections to a confidence threshold (discard low-confidence noise)
3. Draw bounding boxes and labels on the live window for visual confirmation (helpful for demo and debugging)

**Success check:** the live webcam window now shows bounding boxes with labels (e.g. "person 0.87") drawn around detected objects in real time.

---

## Step 5 — Event Construction

**Task for agent:**
1. For each valid detection (post confidence-filtering) in a frame, construct an event as a structured record:
   ```
   {
     "timestamp": <current time, ISO format>,
     "zone": <from get_zone() using the bounding box x-center and frame width>,
     "object": <detected class name>,
     "confidence": <detection confidence score>
   }
   ```
2. Avoid duplicate/flooding events for the same object across consecutive frames — apply a simple cooldown (e.g. only log a new event for the same zone+object combination once every 3 seconds) so the log isn't spammed frame-by-frame

**Success check:** moving in front of the webcam produces one clean event per few seconds per object, not one per frame.

---

## Step 6 — Event Logging

**Task for agent:**
1. In `event_logger.py`, write a function `log_event(event_dict)` that appends the event to `events.csv` with columns: `timestamp, zone, object, confidence`
2. Call `log_event()` from `main.py` every time a new event is constructed in Step 5
3. Ensure the CSV header is written once on first run, and subsequent runs append without duplicating the header

**Success check:** after running the program and walking in front of the webcam for a minute, `events.csv` contains multiple correctly formatted rows with real zone, object, and timestamp data.

---

## Phase 1 Completion Checklist

- [ ] Webcam opens and displays live feed
- [ ] YOLOv8 detects objects in real time with visible bounding boxes
- [ ] Detections are correctly mapped to `zone_1` / `zone_2`
- [ ] Events are cooldown-throttled (no per-frame flooding)
- [ ] Every event is appended correctly to `events.csv`
- [ ] Program exits cleanly on `q`

**Phase 1 ends here.** Do not implement rules engine, urgency scoring, LLM summarization, priority tagging, or dashboard in this phase — those begin in Phase 2 onward, using `events.csv` (or its database successor) as the input.
