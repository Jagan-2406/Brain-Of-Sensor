# 🧠 Brain of Sensors (BoS) — Master Project Guide & Architecture Lesson

---

## 📌 Executive Overview & Core Problem

Traditional physical security camera systems suffer from **Alert Fatigue**. Standard motion detection triggers hundreds of false alarms daily whenever a leaf blows, a light flickers, or a person walks past a door during peak business hours. Security operators become overwhelmed by digging through endless raw log files, increasing response times from seconds to minutes.

### The BoS Solution
**Brain of Sensors (BoS)** introduces **Contextual Anomaly Detection** to physical surveillance:
1. It maintains a **30-day historical memory baseline** per zone for every hour of the day.
2. Normal recurring activity (e.g. 10 people walking by during 2:00 PM) is recognized as benign and scored **LOW URGENCY**.
3. Unexpected activity (e.g. 10 people at 3:00 AM, or an unusual cluster in a quiet area) is instantly flagged as **MEDIUM** or **HIGH URGENCY**.
4. Real humans (`human`) are guaranteed to trigger **HIGH URGENCY** in **RED** bounding boxes `(0, 0, 255)`, while static photos (`image`) are filtered via liveness checks.
5. High-performance object detection is powered by **YOLOv11** (`yolo11s.pt`) with real-time performance telemetry (FPS, inference latency `ms`).
6. The system translates the alert into a **single plain-English summary sentence** and displays it on a **multi-page tactical command dashboard** (`Live Feed`, `Incident History`, `Analytics`).

---

## 🏗️ End-to-End System Architecture & Pipeline

```text
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│   Webcam Feed  │ ───► │  YOLOv11 Detection &    │ ───► │ Post-Processing Liveness│
│   (OpenCV)     │      │  Normalized Labels      │      │ Check (liveness_check)  │
└────────────────┘      └─────────────────────────┘      └─────────────────────────┘
                                                                      │
                                                                      ▼
┌────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Live Dashboard │ ◄─── │     SQLite Storage      │ ◄─── │ Rules / Stats Engine    │
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
1. YOLOv11 Inference (yolo11s.pt)
       │  (Runs detection with confidence >= 0.60, tracks FPS & inference ms latency)
       ▼
2. Class Label Normalization & Spatial Zone Assignment (src/zones.py)
       │  (Maps raw labels to: human, vehicle, animal, backpack, cellphone, chair, pen)
       │  (x_center < frame_width / 2 ? "zone_1" : "zone_2")
       ▼
3. Secondary Liveness Verification (src/liveness_check.py)
       │  ├─ Checks micro-motion buffer & rectangular border contours
       │  └─ Relabels static photos/screens to "image", real human to "human"
       ▼
4. Cooldown Check & Urgency Scoring (src/main.py & src/rules_engine.py)
       │  ├─ Has 3.0s elapsed for key (zone, object)?
       │  ├─ Compare live count vs SQLite 30-day baseline hourly average
       │  └─ "human" strictly forced to HIGH urgency RED (0,0,255); non-human NEVER RED
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
8. Multi-Page Command Center UI & Telemetry (src/app.py & templates/)
       ├─ Live Feed: GET /api/events -> Ranked incident list with audio alerts on HIGH
       ├─ Incident History: GET /api/events/history -> Searchable multi-filter audit log
       ├─ Analytics: GET /api/analytics/summary -> 100% authentic 7-day metrics & trend charts
       └─ Weekly PDF Export: GET /api/report/weekly -> Downloads 7-day PDF report
```

---

## 📚 Phase-by-Phase Technical Breakdown

### 🔹 Phase 1 — Vision Base, YOLOv11 & Spatial Mapping
- **Files**: [`src/main.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/main.py), [`src/zones.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/zones.py), [`src/liveness_check.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/liveness_check.py)
- **What it does**:
  - Captures video frames from webcam via OpenCV (`cv2.VideoCapture`).
  - Passes frames to **YOLOv11** (`yolo11s.pt`) object detection model.
  - Normalizes class names into clean project labels: `human`, `vehicle`, `animal`, `backpack`, `cellphone`, `chair`, `pen`, `image`.
  - Runs secondary post-processing liveness classifier to differentiate real moving humans from held paper photos or phone screens.
  - Displays real-time **Performance HUD** (`FPS`, `Inference Latency ms`, `Detections Count`).
  - Strictly enforces: **Real Human (`human`) receives RED `(0, 0, 255)` bounding box & `[HIGH]` priority. No non-human object is ever drawn in RED.**

---

### 🔹 Phase 2 — Persistence Layer & Historical Baseline
- **Files**: [`src/database.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/database.py), [`src/event_logger.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/event_logger.py), [`src/synthetic_history.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/synthetic_history.py)
- **What it does**:
  - Configures SQLite database (`data/bos.db`) with an `events` table using SQLAlchemy ORM.
  - Generates **30 days of realistic synthetic historical events (~7,400 records)**:
    - Daytime (7 AM – 9 PM): 3 to 12 human events/hr per zone.
    - Nighttime (9 PM – 7 AM): 0 to 1 human events/hr per zone.
  - Provides `get_zone_history(zone, hour_of_day)` helper function to calculate exact 30-day baseline hourly averages.

---

### 🔹 Phase 3 — Rules / Stats Engine (Deterministic Urgency Decision)
- **Files**: [`src/rules_engine.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/rules_engine.py)
- **What it does**:
  - Evaluates live detection against historical baseline using strict mathematical multipliers:
    - `HIGH_MULTIPLIER = 3.0` (Live count >= 3.0x historical avg)
    - `MEDIUM_MULTIPLIER = 1.5` (Live count >= 1.5x historical avg)
    - Nighttime hours (9 PM – 7 AM) apply heightened multipliers.
  - Incorporates `OBJECT_RISK_WEIGHT` (`human`: 1.0, `vehicle`: 0.8, `animal`: 0.5, `backpack`: 0.4, `image`: 0.0).
  - Forces confirmed `human` detections to High Urgency (`person_security_alert`).

---

### 🔹 Phase 4 — Priority Tagging (Versioned JSON Schema)
- **Files**: [`src/priority_tag.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/priority_tag.py)
- **What it does**:
  - Standardizes the event output into a typed dataclass `PriorityTag` (`schema_version="1.0"`).
  - Validates that `urgency` is strictly in `{"low", "medium", "high"}`.
  - Serializes to JSON (`priority_tag_json`) and stores it in SQLite for downstream systems (LLMs, Dashboard, APIs).

---

### 🔹 Phase 5 — LLM Summarizer (Translation Layer)
- **Files**: [`src/summarizer.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/summarizer.py)
- **What it does**:
  - Uses the LLM **strictly as a translator** (never a decision maker).
  - `build_prompt()`: Constructs a constrained prompt instructing LLM to write 1 plain-English sentence using tag data only.
  - `fallback_summarize()`: Provides a deterministic non-LLM summary string if no API key is configured or network fails.
  - `validate_summary()`: Rejects summaries >40 words or summaries containing urgency level contradictions.

---

### 🔹 Phase 6 & Multi-Page Command Center
- **Files**: [`src/app.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/app.py), [`src/report_generator.py`](file:///c:/Studies/Mini%20project%202026/BOS/src/report_generator.py), [`templates/`](file:///c:/Studies/Mini%20project%202026/BOS/templates/)
- **What it does**:
  - Starts Flask web server on `http://127.0.0.1:5000`.
  - Serves 3 navigation views:
    - **Live Feed (`/`)**: Real-time auto-refreshing incident feed with audio chime alerts on new high-priority events.
    - **Incident History (`/history`)**: Searchable, multi-filter historical audit log.
    - **Analytics (`/analytics`)**: 100% authentic 7-day metric telemetry (Total Incidents, High Urgency Rate, Top Active Zone, Mean Confidence, Daily Trends).
  - **7-Day PDF Report Export (`/api/report/weekly`)**: Streams downloadable 7-day security PDF report generated via `fpdf2`.

---

## 🛠️ Complete File Call Hierarchy & Execution Map

```text
[ run_project.py ]  (Master Launcher)
  ├── 1. Spawns Subprocess: python src/app.py
  │      ├── Loads SQLite DB: data/bos.db
  │      ├── Serves Route GET /             ──► Renders templates/dashboard.html
  │      ├── Serves Route GET /history      ──► Renders templates/history.html
  │      ├── Serves Route GET /analytics    ──► Renders templates/analytics.html
  │      ├── Serves Route GET /api/events   ──► Queries events table from SQLite
  │      └── Serves Route GET /api/report/weekly ──► Calls src/report_generator.py
  │
  ├── 2. Opens Browser: http://127.0.0.1:5000
  │
  └── 3. Runs Pipeline: python src/main.py
         ├── Captures Webcam Frame (OpenCV)
         ├── Runs YOLOv11 Detection (yolo11s.pt) & Measures Inference Latency (ms)
         ├── Maps Object Class (human, vehicle, animal, backpack, cellphone, chair, pen)
         ├── Calls src/liveness_check.py -> classify_person_detection()
         ├── Calls src/zones.py -> get_zone()
         ├── Checks 3s Cooldown
         ├── Calls src/rules_engine.py -> score_event()
         │      └── Queries 30-Day Hist Avg via src/database.py -> get_zone_history()
         ├── Calls src/priority_tag.py -> build_priority_tag()
         ├── Calls src/summarizer.py -> summarize_event() & validate_summary()
         ├── Calls src/event_logger.py -> log_event() (Inserts Row into SQLite data/bos.db)
         └── Renders OpenCV Frame + Performance Telemetry HUD (FPS, ms latency)
```

---

## 🚦 How to Run & Test the Project

### 1. Launch Full Live System
```powershell
.\venv\Scripts\python.exe run_project.py
```

### 2. Run Automated Master Test Suite
```powershell
.\venv\Scripts\python.exe scripts/test_system.py
```
