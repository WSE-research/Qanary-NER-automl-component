"""Put the AutomationService backend `app/` package root on sys.path so the
helper modules import the same way the service does (e.g. `helper.filehelper`).
"""
import os
import sys

_APP = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "AutomationService", "AutomationServiceBackend", "app",
)
if _APP not in sys.path:
    sys.path.insert(0, _APP)
