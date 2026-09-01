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

### 2. Run the System
Start the main webcam detection loop (this will automatically download the YOLOv8 model on the first run):
```powershell
python src/main.py
```
*(By default, this uses your external webcam. To use your system's built-in webcam, run `python src/main.py --cam 1`)*

### 3. Verify Database & Synthetic History
To verify the SQLite database and see the synthetic 30-day baseline generation, run the verification script:
```powershell
python scripts/verify_phase2.py
```

---

## 🗺️ Phase Roadmap

- [x] **Phase 1: Detection & Zone Logging** — Webcam + YOLOv8, log events by zone.
- [x] **Phase 2: Storage & Historical Baseline** — Event database + 30-day synthetic history.
- [ ] **Phase 3: Rules/Stats Engine** — Compare live events to baseline, decide urgency.
- [ ] **Phase 4: Priority Tagging** — Formalize urgency into a clean structured tag.
- [ ] **Phase 5: LLM Summarizer** — Structured result → one plain-English sentence.
- [ ] **Phase 6: Dashboard** — Live, color-coded feed of ranked incidents.

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