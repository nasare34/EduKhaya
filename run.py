#!/usr/bin/env python3
"""
EduAI Ghana - Startup Script
Runs both Flask (port 5000) and FastAPI (port 8000) concurrently.
"""
import subprocess
import sys
import os
import time
import signal

BASE = os.path.dirname(os.path.abspath(__file__))

def run():
    print("""
╔══════════════════════════════════════════════╗
║         EduAI Ghana — Teacher Assistant      ║
║  AI-Powered Education for Ghanaian Teachers  ║
╠══════════════════════════════════════════════╣
║  Flask  (UI)    → http://127.0.0.1:5000      ║
║  FastAPI (API)  → http://127.0.0.1:8000      ║
║  API Docs       → http://127.0.0.1:8000/docs ║
╚══════════════════════════════════════════════╝
    """)

    fastapi_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "fastapi_app.main:app",
         "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=BASE
    )
    time.sleep(2)

    flask_proc = subprocess.Popen(
        [sys.executable, "flask_app/app.py"],
        cwd=BASE
    )

    def shutdown(sig, frame):
        print("\nShutting down...")
        fastapi_proc.terminate()
        flask_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    fastapi_proc.wait()
    flask_proc.wait()

if __name__ == "__main__":
    run()
