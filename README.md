# 🧠 Brain of Sensors (BoS)

An AI system that turns raw camera/sensor motion detections into plain-language, priority-ranked incident summaries for security operations centers (malls, campuses, ports, warehouses). 

BoS cuts through alert fatigue and reduces human response time from **minutes** of digging through logs to **seconds** of understanding.

---

## 🛑 The Problem & Solution
Security teams get thousands of motion/camera alerts a day, almost all irrelevant. Existing rule-based systems just trigger on "motion = alert," with no memory or context. 

**Brain of Sensors (BoS)** adds a 30-day historical memory per zone so recurring, benign patterns get filtered out, and only genuine anomalies get flagged — explained in plain English instead of a raw log line.

## 🏗️ Architecture Flow

```text
Webcam → YOLOv8 detection → Zone mapping
       → Rules/Stats Engine (decides urgency — deterministic, no LLM)
       → LLM (translates structured result into plain-English summary only)
       → Dashboard (live, ranked, color-coded)
```

> **Key Design Choice:** The urgency decision is made by an auditable, rule-based engine — not the LLM. The LLM's only job is to translate the already-decided result into a readable sentence. This keeps every flagged alert explainable and traceable to a clear rule, not a black-box AI judgment.

---

## 🚀 Quickstart (Running Locally)

This project requires a webcam. All logic is executed locally on your machine.

### 1. Install Dependencies
Make sure you have an active Python virtual environment, then install the required packages:
```powershell
pip install -r requirements.txt
```

### 2. Run the Full System (Dashboard + Vision Feed)
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
  .\venv\Scripts\python.exe src/main.py --cam 2
  ```

### 3. Run System Test Suite
```powershell
.\venv\Scripts\python.exe scripts/test_system.py
```

---

## 🗺️ Phase Roadmap

- [x] **Phase 1: Detection & Zone Logging** — Webcam + YOLOv8, log events by zone.
- [x] **Phase 2: Storage & Historical Baseline** — SQLite database + 30-day synthetic history.
- [x] **Phase 3: Rules/Stats Engine** — Urgency decision & historical baseline comparison.
- [x] **Phase 4: Priority Tagging** — Structured, versioned JSON PriorityTag schema.
- [x] **Phase 5: LLM Summarizer** — Plain-English event summary sentence generation.
- [x] **Phase 6: Dashboard** — Live, urgency-ranked, auto-refreshing command center UI.

---

## 💻 Tech Stack
- **AI/Vision:** YOLOv8 (Ultralytics), OpenCV
- **Backend/Data:** Python, SQLAlchemy, SQLite, Pandas
- **Future Phases:** Flask, Claude/OpenAI API, HTML/JS Dashboard

---

## 🌍 SDG Alignment
- **Primary:** SDG 16 — Peace, Justice and Strong Institutions
- **Secondary:** SDG 11 — Sustainable Cities and Communities
- **Secondary:** SDG 9 — Industry, Innovation and Infrastructure