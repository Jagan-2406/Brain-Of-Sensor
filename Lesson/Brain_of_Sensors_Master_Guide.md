# 🧠 Brain of Sensors (BoS) — Master Project Guide & Architecture Lesson

---

## 📌 Executive Overview & Core Problem

Traditional physical security camera systems suffer from **Alert Fatigue**. Standard motion detection triggers hundreds of false alarms daily whenever a leaf blows, a light flickers, or a person walks past a door during peak business hours. Security operators become overwhelmed by digging through endless raw log files, increasing response times from seconds to minutes.

### The BoS Solution
**Brain of Sensors (BoS)** introduces **Contextual Anomaly Detection** to physical surveillance:
1. It maintains a **30-day historical memory baseline** per zone for every hour of the day.
2. Normal recurring activity (e.g. 10 people walking by during 2:00 PM) is recognized as benign and scored **LOW URGENCY**.
3. Unexpected activity (e.g. 10 people at 3:00 AM, or an unusual cluster in a quiet area) is instantly flagged as **MEDIUM** or **HIGH URGENCY**.
4. The system translates the alert into a **single plain-English summary sentence** and displays it on a **ranked tactical dashboard**.

---

## 🏗️ End-to-End System Architecture & Pipeline

```text
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│   Webcam Feed  │ ───► │  YOLOv8 Detection &     │ ───► │ Zone Mapping &          │
│   (OpenCV)     │      │  Confidence Filtering   │      │ 3-Second Cooldown       │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
                                                                      │
                                                                      ▼
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Live Dashboard │ ◄─── │ SQLite Storage          │ ◄─── │ Rules / Stats Engine    │
│ (Flask UI)     │      │ (events table in DB)    │      │ (30-Day Hist Avg Comp)  │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
        ▲                                                             │
        │                                                             ▼
┌────────────────┐                                       ┌─────────────────────────┐
│ 3s Polling     │ ◄──────────────────────────────────── │ PriorityTag (v1.0 JSON) │
│ AJAX Fetch     │                                       │ & LLM Plain-English     │
└────────────────┘                                       └─────────────────────────┘
```

---

## 🔍 Detailed Dataflow Sequence

```text
[ Webcam Frame ]
       │
       ▼
1. YOLOv8 Inference (yolov8s.pt)
       │  (Filters objects with confidence >= 0.60, e.g. "person" @ 0.92)
       ▼
2. Spatial Zone Assignment (src/zones.py)
       │  (x_center < frame_width / 2 ? "zone_1" : "zone_2")
       ▼
3. Cooldown Check (src/main.py)
       │  (Has 3.0 seconds elapsed for key (zone, object)? If yes, process event)
       ▼
4. Rules Engine Anomaly Evaluation (src/rules_engine.py)
       │  ├─ Query SQLite 30-day baseline hourly avg for (zone, hour_of_day)
       │  ├─ Compare live count vs historical average
       │  └─ Compute Urgency: HIGH (count >= 3x avg), MEDIUM (count >= 1.5x avg), LOW
       ▼
5. Priority Tag Serialization (src/priority_tag.py)
       │  (Builds versioned "1.0" PriorityTag dataclass & converts to JSON)
       ▼
6. LLM Plain-English Translation (src/summarizer.py)
       │  ├─ Constrained Prompt sent to Claude LLM (or deterministic fallback engine)
       │  └─ Validate summary length (<40 words) and check urgency consistency
       ▼
7. SQLite Database Persistence (src/event_logger.py & src/database.py)
       │  (Saves row with raw fields + urgency + priority_tag_json + summary_text)
       ▼
8. Command Center Live Rendering (src/app.py & templates/index.html)
       └─ Flask API serves GET /api/events -> UI polls every 3s -> Renders ranked feed
```

---

## 📚 Phase-by-Phase Technical Breakdown

### 🔹 Phase 1 — Vision Base & Spatial Mapping
- **Files**: [`src/main.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/main.py), [`src/zones.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/zones.py)
- **What it does**:
  - Captures video frames from webcam via OpenCV (`cv2.VideoCapture`).
  - Passes frames to **YOLOv8** (`yolov8s.pt`) object detection model.
  - Divides the video frame spatially into `zone_1` (left half) and `zone_2` (right half).
  - Enforces a **3.0-second cooldown per (zone, object)** to prevent duplicate event spamming while a person remains standing in front of the camera.

---

### 🔹 Phase 2 — Persistence Layer & Historical Baseline
- **Files**: [`src/database.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/database.py), [`src/event_logger.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/event_logger.py), [`src/synthetic_history.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/synthetic_history.py)
- **What it does**:
  - Configures SQLite database (`data/bos.db`) with an `events` table using SQLAlchemy ORM.
  - Generates **30 days of realistic synthetic historical events (~7,400 records)**:
    - Daytime (7 AM – 9 PM): 3 to 12 person events/hr per zone.
    - Nighttime (9 PM – 7 AM): 0 to 1 person events/hr per zone.
  - Provides `get_zone_history(zone, hour_of_day)` helper function to calculate exact 30-day baseline hourly averages.

---

### 🔹 Phase 3 — Rules / Stats Engine (Deterministic Urgency Decision)
- **Files**: [`src/rules_engine.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/rules_engine.py)
- **What it does**:
  - Evaluates live detection against historical baseline using strict mathematical multipliers:
    - `HIGH_MULTIPLIER = 3.0` (Live count >= 3.0x historical avg)
    - `MEDIUM_MULTIPLIER = 1.5` (Live count >= 1.5x historical avg)
    - Nighttime hours (9 PM – 7 AM) apply heightened multipliers.
  - Generates auditable `reason_codes` (`unusual_zone_frequency`, `nighttime_activity`).
  - **Key Design Philosophy**: The urgency decision is **100% deterministic (no black-box AI)**. Security decisions must be auditable and explainable.

---

### 🔹 Phase 4 — Priority Tagging (Versioned JSON Schema)
- **Files**: [`src/priority_tag.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/priority_tag.py)
- **What it does**:
  - Standardizes the event output into a typed dataclass `PriorityTag` (`schema_version="1.0"`).
  - Validates that `urgency` is strictly in `{"low", "medium", "high"}` (raises `ValueError` on bad inputs).
  - Serializes to JSON (`priority_tag_json`) and stores it in SQLite for downstream systems (LLMs, Dashboard, APIs).

---

### 🔹 Phase 5 — LLM Summarizer (Translation Layer)
- **Files**: [`src/summarizer.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/summarizer.py)
- **What it does**:
  - Uses the LLM **strictly as a translator** (never a decision maker).
  - `build_prompt()`: Constructs a constrained prompt instructing Claude LLM to write 1 plain-English sentence (max 25 words) using tag data only.
  - `fallback_summarize()`: Provides a deterministic non-LLM summary string if no API key is configured or network fails.
  - `validate_summary()`: Rejects summaries >40 words or summaries containing urgency level contradictions (e.g. summary saying "low priority" when tag is marked "high").

---

### 🔹 Phase 6 — Interactive Command Center Dashboard
- **Files**: [`src/app.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/app.py), [`templates/index.html`](file:///c:/Studies/Mini%20project%202026/BOS/templates/index.html)
- **What it does**:
  - Starts Flask web server on `http://127.0.0.1:5000`.
  - Exposes REST API endpoint `GET /api/events` returning recent event records as JSON.
  - Renders a **Dark Tactical Cyber Command UI**:
    - Live polling heartbeat every 3 seconds via AJAX.
    - Urgency-first ranking algorithm (High Urgency → Medium → Low, then recency).
    - Glowing visual cards with color-coded urgency borders (Red = High, Gold = Medium, Green = Low).
    - Dynamic filter tabs (`ALL`, `HIGH URGENCY`, `MEDIUM`, `LOW`).

---

## 🛠️ Complete File Call Hierarchy & Execution Map

```text
[ run_project.py ]  (Master Launcher)
  ├── 1. Spawns Subprocess: python src/app.py
  │      ├── Loads SQLite DB: data/bos.db
  │      ├── Serves Route GET /         ──► Renders templates/index.html
  │      └── Serves Route GET /api/events ──► Queries events table from SQLite
  │
  ├── 2. Opens Browser: http://127.0.0.1:5000
  │
  └── 3. Runs Pipeline: python src/main.py
         ├── Captures Webcam Frame (OpenCV)
         ├── Runs YOLOv8 Detection (yolov8s.pt)
         ├── Calls src/zones.py -> get_zone()
         ├── Checks 3s Cooldown
         ├── Calls src/rules_engine.py -> score_event()
         │      └── Queries 30-Day Hist Avg via src/database.py -> get_zone_history()
         ├── Calls src/priority_tag.py -> build_priority_tag()
         ├── Calls src/summarizer.py -> summarize_event() & validate_summary()
         └── Calls src/event_logger.py -> log_event()
                └── Inserts Row into SQLite data/bos.db
```

---

## 🚦 How to Run & Test the Project

### 1. Launch Full Live System
```powershell
.\venv\Scripts\python.exe run_project.py
```

### 2. Run Automated Master Test Suite (All 6 Phases)
```powershell
.\venv\Scripts\python.exe scripts/test_system.py
```
