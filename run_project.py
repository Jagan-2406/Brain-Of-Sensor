"""
BoS (Brain of Sensors) — Master Runner Script

Launches both:
1. Flask Web Dashboard (src/app.py) on http://127.0.0.1:5000
2. YOLOv8 Live Vision Pipeline (src/main.py)

Usage:
  python run_project.py
"""

import sys
import os
import subprocess
import time
import webbrowser

def main():
    print("==================================================")
    print("  Brain of Sensors (BoS) — Launching Full System  ")
    print("==================================================")
    
    python_exe = sys.executable
    project_root = os.path.abspath(os.path.dirname(__file__))

    # 1. Launch Flask Web Dashboard in background
    print("\n[1/3] Starting Web Dashboard (src/app.py)...")
    app_proc = subprocess.Popen(
        [python_exe, os.path.join(project_root, 'src', 'app.py')],
        cwd=project_root
    )

    # Give Flask a second to spin up
    time.sleep(2)

    # 2. Open dashboard in browser
    print("[2/3] Opening Dashboard in browser: http://127.0.0.1:5000 ...")
    webbrowser.open("http://127.0.0.1:5000")

    # 3. Launch live vision pipeline
    print("[3/3] Starting Vision Feed (src/main.py)... Press 'q' in video window to stop.")
    try:
        main_proc = subprocess.run(
            [python_exe, os.path.join(project_root, 'src', 'main.py'), '--cam', '1'],
            cwd=project_root
        )
    except KeyboardInterrupt:
        print("\nStopping project...")
    finally:
        print("Shutting down Dashboard server...")
        app_proc.terminate()
        app_proc.wait()
        print("Project stopped cleanly.")

if __name__ == "__main__":
    main()
