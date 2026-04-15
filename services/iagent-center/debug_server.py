"""
Debug entry point — use this instead of `uvicorn iagent.main:app` when you want breakpoints.

Why a separate file instead of modifying main.py?
  - debugpy.listen() must run BEFORE uvicorn imports the app
  - --reload spawns a subprocess that loses the debugpy connection
    so we run uvicorn programmatically here with reload=False

Usage:
  cd services/iagent-center
  python debug_server.py

Then attach VS Code via F5 (launch.json "Attach to iAgent").
You can attach at any time — the server does NOT wait for you.
Set breakpoints, send a request, and VS Code will pause at the right line.
"""
import debugpy

# Open port 5678 for VS Code to connect.
# listen() is non-blocking — the server starts immediately,
# VS Code can attach before or after the first request.
debugpy.listen(("0.0.0.0", 5678))
print("🔍 debugpy listening on port 5678 — attach VS Code now or after the server starts")

import uvicorn

uvicorn.run(
    "iagent.main:app",
    host="0.0.0.0",
    port=8000,
    reload=False,       # MUST be False — reload forks a subprocess and breaks debugpy
    log_level="info",
)
