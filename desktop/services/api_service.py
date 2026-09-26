import requests
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from utils.hardware import get_machine_id

API_URL = "http://141.11.237.78:30039"

class LicenseCheckerThread(QThread):
    # success, message, expiration_date, is_network_error
    result_signal = pyqtSignal(bool, str, str, bool)

    def __init__(self, license_key: str):
        super().__init__()
        self.license_key = license_key.strip()

    def run(self):
        try:
            if not self.license_key:
                self.result_signal.emit(False, "License key is required.", "", False)
                return
            
            # Moved off the main thread: get_machine_id() can sometimes block or raise 
            # unexpected OS-level errors when querying hardware via subprocess.
            machine_id = get_machine_id()
            
            try:
                resp = requests.post(f"{API_URL}/api/verify", json={
                    "license_key": self.license_key,
                    "machine_id": machine_id
                }, timeout=5)
            except requests.exceptions.RequestException:
                # Network failure. Fail closed safely.
                self.result_signal.emit(False, "Unable to contact the license server.", "", True)
                return
            
            try:
                data = resp.json()
            except ValueError:
                # Malformed JSON response
                self.result_signal.emit(False, "Received invalid data from the server.", "", True)
                return

            if resp.status_code == 200 and data.get("status") == "ACTIVE":
                # Convert ISO string for cleaner UI
                raw_date = data.get("expires_at", "")
                nice_date = raw_date.split("T")[0] if "T" in raw_date else raw_date
                self.result_signal.emit(True, "License Activated", nice_date, False)
            else:
                # Explicit API rejection (expired, revoked, wrong PC, etc.)
                self.result_signal.emit(False, data.get("detail", "Validation failed."), "", False)
                
        except Exception:
            # Catch-all for ANY unexpected exception (e.g., TypeError, hardware ID failure, etc.)
            logging.exception("Unexpected error in LicenseCheckerThread")
            self.result_signal.emit(False, "License verification failed due to an unexpected error.", "", True)