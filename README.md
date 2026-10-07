# 🧠 Brain of Sensors (BoS) — High-Performance Surveillance Intelligence

An AI system that turns raw camera/sensor motion detections into plain-language, priority-ranked incident summaries for security operations centers (malls, campuses, ports, warehouses). 

BoS cuts through alert fatigue and reduces human response time from **minutes** of digging through logs to **seconds** of understanding.

---

## 🛑 The Problem & Solution
Security teams get thousands of motion/camera alerts a day, almost all irrelevant. Existing rule-based systems just trigger on "motion = alert," with no memory or context. 

**Brain of Sensors (BoS)** adds a 30-day historical memory per zone so recurring, benign patterns get filtered out, and only genuine anomalies get flagged — explained in plain English instead of a raw log line.

---

## 🏗️ Architecture Flow

```text
Webcam → YOLOv11 Detection (yolo11s.pt) → Normalized Label Taxonomy (human, vehicle, etc.)
       → Post-Processing Liveness Check (liveness_check.py)
       → Rules/Stats Engine (decides urgency — deterministic 30-day historical baseline comparison)
       → PriorityTag Dataclass Serialization (v1.0 JSON)
       → LLM Summarizer (translates structured result into plain-English summary sentence)
       → Multi-Page Command Center UI (Live Feed, Incident History, Analytics + Performance HUD)
```

> **Key Design Choice:** The urgency decision is made by an auditable, rule-based engine — not the LLM. The LLM's only job is to translate the already-decided result into a readable sentence. This keeps every flagged alert explainable and traceable to a clear rule, not a black-box AI judgment.

---

## 🚀 Quickstart (Running Locally)

This project requires a webcam. All logic is executed locally on your machine.

### 1. Install Dependencies
Make sure you have an active Python virtual environment, then install the required packages:
```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Run the Full System (Dashboard + YOLOv11 Vision Feed)
Run both the Web Dashboard and the Webcam Vision Pipeline with one single command:
```powershell
.\venv\Scripts\python.exe run_project.py
```
This automatically starts `src/app.py`, opens `http://127.0.0.1:5000` in your web browser, and launches `src/main.py`.

#### Running Separately in Two Terminals:
- **Terminal 1 (Dashboard Server):**
  ```powershell
  .\venv\Scripts\python.exe src/app.py
  ```
- **Terminal 2 (Webcam Feed):**
  ```powershell
  .\venv\Scripts\python.exe src/main.py --cam 1
  ```

### 3. Run Master System Verification Test Suite
```powershell
.\venv\Scripts\python.exe scripts/test_system.py
```

---

## 🗺️ Phase Roadmap & Completed Features

- [x] **Phase 1: Detection & Spatial Zone Logging** — Webcam + YOLOv11 (`yolo11s.pt`), log events by zone.
- [x] **Phase 2: Storage & Historical Baseline** — SQLite database + 30-day synthetic baseline history.
- [x] **Phase 3: Rules/Stats Engine** — Urgency decision & historical baseline comparison.
- [x] **Phase 4: Priority Tagging** — Structured, versioned JSON `PriorityTag` schema (v1.0).
- [x] **Phase 5: LLM Summarizer** — Plain-English event summary sentence generation with validation.
- [x] **Phase 6: Multi-Page Command UI** — Dark tactical UI (`Live Feed`, `Incident History`, `Analytics`).
- [x] **YOLOv11 & Performance Telemetry HUD** — Real-time FPS, inference latency (`ms`), and active detection overlay.
- [x] **Normalized Label Taxonomy** — `human`, `vehicle`, `animal`, `backpack`, `cellphone`, `chair`, `pen`, `image`.
- [x] **Real Human RED Box Guarantee** — `human` detections strictly receive **RED** bounding box `(0,0,255)` & `[HIGH]` priority. No non-human object can ever be RED.
- [x] **Liveness Classifier** — Photo/image detection heuristics (`liveness_check.py`) protecting real humans from misclassification.
- [x] **Feature 1: Multi-Page UI** — Live Feed, History, and 100% Authentic Live Analytics (`base.html`).
- [x] **Feature 2: 7-Day PDF Report Export** — Download weekly PDF report via `fpdf2` (`report_generator.py`).
- [x] **Feature 3: Audio Alert Chime** — High-priority notification alert sound (`alert.mp3`).

---

## 💻 Tech Stack
- **AI/Vision Engine:** YOLOv11 (`yolo11s.pt` via Ultralytics), OpenCV
- **Backend/Data:** Python, Flask, SQLAlchemy, SQLite, Pandas, FPDF2
- **Frontend/UI:** HTML5, CSS3 (Vanilla Dark Mode), JavaScript (Fetch API, Chart.js)

---

## 🌍 SDG Alignment
- **Primary:** SDG 16 — Peace, Justice and Strong Institutions
- **Secondary:** SDG 11 — Sustainable Cities and Communities
- **Secondary:** SDG 9 — Industry, Innovation and Infrastructure

---

## 💻 Commands Reference Guide

### 1. Run Full System (Dashboard + Camera Vision Feed)
```powershell
.\venv\Scripts\python.exe run_project.py
```
*(Starts Flask Dashboard at http://127.0.0.1:5000 and opens System Camera feed simultaneously).*

### 2. Run Components Separately
- **Web Dashboard Server Only:**
  ```powershell
  .\venv\Scripts\python.exe src/app.py
  ```
- **System Built-in Camera Feed Only:**
  ```powershell
  .\venv\Scripts\python.exe src/main.py --cam 1
  ```
- **External Camera Feed Only:**
  ```powershell
  .\venv\Scripts\python.exe src/main.py --cam 2
  ```

### 3. Run Master System Test Suite
```powershell
.\venv\Scripts\python.exe scripts/test_system.py
```

### 4. Install Dependencies
```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```
