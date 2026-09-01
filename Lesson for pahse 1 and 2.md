# Brain of Sensors (BoS) - Developer Guide (Phases 1 & 2)

If a new developer joins the project today, this is the document you should hand them. It explains what the project does, how the files are organized, and exactly how data flows from the real-world webcam straight into the database.

---

## 1. The Big Picture
The **Brain of Sensors (BoS)** is a local, real-time AI system. It watches a webcam feed, uses a neural network to detect objects (like people and cars), figures out where they are standing, and logs that data into a SQLite database. 

It also maintains a "synthetic history"—a fake 30-day baseline of data used to calculate historical averages (so the system knows the difference between a busy daytime hour and a quiet nighttime hour).

---

## 2. The File Architecture
We structured the project into modular pieces so it's easy to read and scale:

- **`src/main.py` (The Engine)**: The core loop that runs the webcam and the AI. This is what you execute to start the system.
- **`src/zones.py` (The Map)**: Contains the spatial logic to map X/Y coordinates to physical zones.
- **`src/database.py` (The Storage Layer)**: Sets up the SQLite database (`bos.db`) using SQLAlchemy and provides query functions.
- **`src/event_logger.py` (The Bridge)**: Takes live events from `main.py` and routes them into the database and a backup CSV file.
- **`src/synthetic_history.py` (The Baseline)**: Generates 30 days of realistic past events to populate the database.
- **`scripts/verify_phase2.py` (The Tester)**: A standalone script to prove the database and query logic are working.

---

## 3. The Execution Flow (What calls what?)

When you type `python src/main.py` in the terminal, here is exactly what happens step-by-step:

### Step 1: Initialization
`main.py` loads the YOLOv8 AI model into memory. It then connects to your webcam using OpenCV (forcing a `640x480` resolution for stability). It enters a `while True:` loop, grabbing frames from the camera 30 times a second.

### Step 2: AI Inference
Each video frame is passed to the YOLOv8 model. The AI scans the image and returns a list of "bounding boxes" (rectangles drawn around detected objects) and a confidence score (e.g., "I am 85% sure this is a person").

### Step 3: Spatial Mapping
`main.py` calculates the exact center point of each bounding box. It then calls the `get_zone(x_center, frame_width)` function from **`zones.py`** to figure out if the object is in `zone_1` (left half of the screen) or `zone_2` (right half).

### Step 4: Event Throttling (Cooldown)
Because video runs at 30 frames a second, a person standing still would generate thousands of events. To fix this, `main.py` uses a cooldown dictionary. It checks: *"Have I logged a person in zone_1 in the last 3 seconds?"* If yes, it ignores them. If no, it proceeds to log them.

### Step 5: Logging (The Bridge to Phase 2)
`main.py` constructs a dictionary containing the timestamp, zone, object name, confidence, and sets `source: 'real'`. It passes this dictionary to the `log_event()` function in **`event_logger.py`**.

**`event_logger.py`** takes over and does two things:
1. It appends a row to `data/events.csv` (for a raw text backup).
2. It uses the `Event` model imported from **`database.py`** to insert the data cleanly into the SQLite database (`data/bos.db`).

---

## 4. How the Historical Baseline Works
If you look inside `database.py`, you'll see a function called `get_zone_history()`. 

Because we ran **`synthetic_history.py`**, the database is pre-filled with 30 days of events. When Phase 3 begins, the system will use `get_zone_history()` to query the database and ask: *"On average, how many people do we normally see in zone_1 at 2 AM?"*

By comparing the **live event** (from Step 5) against the **historical baseline** (from `get_zone_history()`), your Phase 3 Rules Engine will be able to make intelligent decisions!
