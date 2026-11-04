import sys
import os

# Prevent OpenMP runtime collision crashes across ML and computer vision runtimes
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
try:
    import cv2
    cv2.ocl.setUseOpenCL(False)
except Exception:
    pass

# Settings > Performance: every FFmpeg the app starts from here on gets the CPU cap / thread limits / slots
# (utils/resources.py). Installed before yt-dlp or anything else imports subprocess.Popen: yt-dlp subclasses it
# at import time, and its segment downloads must be capped too.
try:
    from utils.resources import install as _install_performance_budget
    _install_performance_budget()
except Exception:
    pass

import time
import datetime
import traceback
import subprocess

# Light imports only. The heavy UI import (ui.main_window) happens AFTER the
# bootstrapper handoff check, so slow imports can't eat the handoff time window.
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

HANDOFF_MAX_AGE_SECONDS = 120.0

def _setup_crash_logging():
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local"))
    log_dir = os.path.join(local_app_data, "CReaper")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "debug.log")

    if getattr(sys, 'frozen', False):
        log_handle = open(log_file, 'a', encoding='utf-8')
        if sys.stdout is None: sys.stdout = log_handle
        if sys.stderr is None: sys.stderr = log_handle
    return log_file

CRASH_LOG_FILE = _setup_crash_logging()


def _apply_data_location():
    """Bulky data (and TEMP) may live on another drive than C: (chosen in the installer). Must run before anything
    creates a temp file; a failure here must never stop the app."""
    try:
        from utils import install_location
        tmp = install_location.apply_temp_dir()
        if tmp:
            _debug_log(f"Work files go to {tmp}")
    except Exception as e:
        _debug_log(f"Data location not applied: {e}")

def _debug_log(msg: str):
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        with open(CRASH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [MAIN] {msg}\n")
    except Exception: pass

def _install_exception_hooks():
    """PyQt6 ABORTS the whole process on an exception raised inside a signal handler when no sys.excepthook is
    installed: one bad value in a finished job's result closed the app with nothing in the log. With this hook
    the exception is written to debug.log and the app keeps running."""
    import threading

    def log_exc(exc_type, exc, tb):
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return sys.__excepthook__(exc_type, exc, tb)
        _debug_log("Unhandled exception (the app kept running):\n" + "".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = log_exc
    threading.excepthook = lambda a: log_exc(a.exc_type, a.exc_value, a.exc_traceback) if a.exc_type else None

def resource_path(filename: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"): return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def _get_app_dir() -> str:
    if getattr(sys, "frozen", False): return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def _verify_bootstrapper_handoff_or_redirect() -> bool:
    token_arg = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--bootstrapper-token" and i + 1 < len(sys.argv):
            token_arg = sys.argv[i + 1]
            break
        i += 1

    provided_token = token_arg or os.environ.get("CREAPER_BOOTSTRAPPER_TOKEN")
    handoff_file = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CReaper", ".bootstrapper_handoff")

    if provided_token and os.path.exists(handoff_file):
        try:
            with open(handoff_file, "r", encoding="utf-8") as f: content = f.read().strip()
            parts = content.split(":", 1)
            valid = (len(parts) == 2 and parts[0] == provided_token
                     and abs(time.time() - float(parts[1])) <= HANDOFF_MAX_AGE_SECONDS)
            if valid:
                # One-time use: consume the handoff only once it has been validated.
                try: os.remove(handoff_file)
                except Exception: pass
                return True
            _debug_log("handoff token mismatch or expired")
        except Exception:
            _debug_log("handoff file unreadable: " + traceback.format_exc())

    # Direct launch detected. Redirect to bootstrapper.
    # Install layout: <install root>\CReaperBootstrapper.exe
    #                 <install root>\versions\<ver>\CReaper.exe  (this app)
    # The install root is %LOCALAPPDATA%\CReaper unless the user picked another drive (utils/install_location.py):
    # the app's own folder says where it really is, the pointer file and the default cover the rest.
    app_dir = _get_app_dir()
    from utils import install_location
    own_root = install_location.app_root_from_exe(sys.executable)
    bootstrapper_candidates = [
        os.path.join(root, "CReaperBootstrapper.exe")
        for root in dict.fromkeys(r for r in (own_root, install_location.install_root(), install_location.anchor()) if r)
    ] + [
        os.path.abspath(os.path.join(app_dir, "..", "..", "CReaperBootstrapper.exe")),
        os.path.join(app_dir, "CReaperBootstrapper.exe"),
    ]

    bootstrapper_exe = next((b for b in bootstrapper_candidates if os.path.exists(b)), None)
    if bootstrapper_exe:
        subprocess.Popen([bootstrapper_exe], cwd=os.path.dirname(bootstrapper_exe))
    else:
        _show_message("Can't start CReaper",
                      "CReaper must be started with CReaperBootstrapper.exe, which could not be found.",
                      "Run CReaperBootstrapper.exe again to repair the installation.", tone="warning")
    return False

def _show_message(title: str, text: str, detail: str = "", tone: str = "info"):
    """The app's own dialog; the plain Windows box only if that can't be shown (e.g. a broken install)."""
    try:
        from ui.components.app_dialog import inform
        inform(None, title, text, detail, tone=tone)
    except Exception:
        QMessageBox.warning(None, "CReaper", "\n\n".join(x for x in (title, text, detail) if x))


def main():
    _debug_log("=== CReaper Application Started ===")
    _apply_data_location()
    _install_exception_hooks()
    app_dir = _get_app_dir()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # One instance per Windows user session: a duplicate launch focuses the running window and exits.
    from utils.single_instance import acquire_or_signal_existing, install_activation_handler
    if not acquire_or_signal_existing():
        _debug_log("Another CReaper instance is already running; brought it to the front and exiting.")
        sys.exit(0)
    install_activation_handler(app)

    icon_path = resource_path("CRPR.ico")
    if os.path.exists(icon_path): app.setWindowIcon(QIcon(icon_path))

    # Handoff check FIRST - before any heavy imports.
    if getattr(sys, "frozen", False):
        is_dev_mode = False
        dev_file_path = os.path.join(app_dir, "dev_mode.txt")
        
        # Strict validation: The file must exist AND contain your exact secret phrase
        if os.path.exists(dev_file_path):
            try:
                with open(dev_file_path, "r", encoding="utf-8") as f:
                    if f.read().strip() == "RXADRIAN_DEV_OVERRIDE_8891":
                        is_dev_mode = True
            except Exception:
                pass
                
        # Also secure the command line argument just in case
        if "--dev=RXADRIAN_DEV_OVERRIDE_8891" in sys.argv:
            is_dev_mode = True

        if is_dev_mode:
            _debug_log("Developer mode active (valid secret found). Skipping bootstrapper handoff.")
        else:
            if not _verify_bootstrapper_handoff_or_redirect():
                sys.exit(0)

    try: os.chdir(app_dir)
    except Exception: pass

    from ui.main_window import MainWindow   # heavy import, deliberately after the handoff check

    window = MainWindow()
    window.show()
    # an install's bootstrapper is never replaced by an app update: swap in this release's one if it's newer
    from utils.bootstrapper_refresh import refresh_in_background
    refresh_in_background(log=_debug_log)
    sys.exit(app.exec())

if __name__ == "__main__":
    try: main()
    except Exception as fatal_error:
        _debug_log(traceback.format_exc())
        try:
            if QApplication.instance() is None:
                _app = QApplication(sys.argv)
            _show_message("CReaper failed to start", str(fatal_error), "Details were written to debug.log.",
                          tone="error")
        except Exception: pass
        sys.exit(1)