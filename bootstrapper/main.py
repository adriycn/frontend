r"""
CReaperBootstrapper - the only file users download.

Install layout. <root> is %LOCALAPPDATA%\CReaper by default, or the folder the user picked (any drive):
    <root>\CReaperBootstrapper.exe        installed copy; all shortcuts point here
    <root>\state.json                     {"current", "previous", "pending_verify", "failed", ...}
    <root>\versions\<version>\CReaper.exe  one folder per installed version
    <root>\staging\ , downloads\         temporary; wiped on every start; on the same drive as the install
    <root>\data\                         bulky app data (AI models, projects, caches, work files) when moved
%LOCALAPPDATA%\CReaper (the "anchor") always holds the small per-user files shared with the app:
    location.json                  {"install_root": ..., "data_root": ...}  (absent = everything in the anchor)
    debug.log, .bootstrapper_handoff, settings.json, session.dat

The app reads the same location.json (desktop/utils/install_location.py; tests/test_install_location.py keeps the two
in agreement). The chosen folder is always a dedicated "CReaper" folder, so the cleanup that removes old packages can
never touch anything else on the drive.
"""
import ctypes
import datetime
import hashlib
import json
import os
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile

from PyQt6.QtCore import (QEasingCurve, QObject, QPointF, QPropertyAnimation, QRectF, QThread, QTimer, Qt,
                          pyqtProperty, pyqtSignal)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (QApplication, QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                             QPushButton, QSizePolicy, QVBoxLayout, QWidget)

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
API_URL = "https://backend-production-e424.up.railway.app/api/update/latest"
APP_NAME = "CReaper"
APP_EXE = "CReaper.exe"
BOOT_EXE = "CReaperBootstrapper.exe"

FAIL_BACKOFF = 6 * 3600            
ALLOW_LAUNCH_OLD_ON_UPDATE_FAILURE = False   
CHUNK = 1024 * 1024
MAX_API_BYTES = 1024 * 1024
USER_AGENT = "CReaperBootstrapper/1.0"

LOCAL = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
ANCHOR = os.path.join(LOCAL, "CReaper")                 # small per-user files, always on the profile drive
LOCATION_FILE = os.path.join(ANCHOR, "location.json")
HANDOFF_FILE = os.path.join(ANCHOR, ".bootstrapper_handoff")   # the app looks here (desktop/main.py)
LOG_FILE = os.path.join(ANCHOR, "debug.log")                   # shared with the app
FOLDER_NAME = "CReaper"
BULK_DIRS = ("models", "projects", "cache", "preview_cache", "music", "tmp")   # follow the data root
MIN_FREE_BYTES = 3 * 1024 ** 3                          # a download, its unpacked copy and room to update
# Windows stops at 260 characters per file path. The package's deepest file is 101 characters inside the version
# folder, which adds versions/<ver>/ (about 22 characters) on top of the install folder: 100 characters keeps a wide margin.
MAX_ROOT_LEN = 100

VERSION_RE = re.compile(r"\d+(\.\d+){0,3}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")

ROOT = VERSIONS_DIR = STAGING_DIR = DOWNLOAD_DIR = STATE_FILE = ""


def set_root(root: str):
    """Points every install path at `root` (the install folder). Called at start and when the user picks another."""
    global ROOT, VERSIONS_DIR, STAGING_DIR, DOWNLOAD_DIR, STATE_FILE
    ROOT = root
    VERSIONS_DIR = os.path.join(ROOT, "versions")
    STAGING_DIR = os.path.join(ROOT, "staging")
    DOWNLOAD_DIR = os.path.join(ROOT, "downloads")
    STATE_FILE = os.path.join(ROOT, "state.json")


def _abs(p) -> str:
    if not isinstance(p, str) or not p.strip():
        return ""
    p = os.path.normpath(os.path.expandvars(p.strip().strip('"')))
    return p if os.path.isabs(p) else ""


def read_location() -> dict:
    try:
        with open(LOCATION_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    return {"install_root": _abs(d.get("install_root")), "data_root": _abs(d.get("data_root"))}


def write_location(install_root: str = "", data_root: str = ""):
    """Records the roots; a root equal to the anchor is left out (no entry = the default layout)."""
    os.makedirs(ANCHOR, exist_ok=True)
    body = {"version": 1}
    for key, val in (("install_root", install_root), ("data_root", data_root)):
        val = _abs(val)
        if val and os.path.normcase(val) != os.path.normcase(ANCHOR):
            body[key] = val
    tmp = LOCATION_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LOCATION_FILE)


def drive_ready(path: str) -> bool:
    d = os.path.splitdrive(path)[0]
    return bool(d) and os.path.isdir(d + os.sep)


def dedicated_folder(path: str) -> str:
    """The folder CReaper installs into for what the user picked: the picked folder if it is already called CReaper,
    otherwise a CReaper folder inside it (D:/ -> D:/CReaper). Never a shared folder, because cleanup() deletes
    leftovers inside the install root."""
    p = _abs(path)
    if not p:
        return ""
    return p if os.path.basename(p).lower() == FOLDER_NAME.lower() else os.path.join(p, FOLDER_NAME)


def check_install_folder(path: str) -> tuple:
    """-> (install root, "") or ("", the reason it cannot be used). Creates nothing that is left behind."""
    root = dedicated_folder(path)
    if not root:
        return "", "Enter a full folder path, for example D:\\CReaper."
    if root.startswith("\\\\"):
        return "", "Network folders are not supported. Pick a folder on a drive in this PC."
    if len(root) > MAX_ROOT_LEN:
        return "", (f"That folder path is too long ({len(root)} characters, at most {MAX_ROOT_LEN}). Windows limits file "
                    f"paths to 260 characters and CReaper's files are nested deeply. Choose a shorter path, for example "
                    f"D:" + os.sep + FOLDER_NAME + ".")
    if not drive_ready(root):
        return "", f"The drive {os.path.splitdrive(root)[0]} is not available."
    try:
        os.makedirs(root, exist_ok=True)
        probe = os.path.join(root, ".write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
    except OSError as e:
        return "", f"CReaper can't write to {root}.\n\n{e.strerror or e}"
    free = shutil.disk_usage(root).free
    if free < MIN_FREE_BYTES:
        return "", f"{root[:2]} has only {human_bytes(free)} free. CReaper needs at least {human_bytes(MIN_FREE_BYTES)}."
    return root, ""


def drives() -> list:
    """[(letter, free bytes, total bytes)] of the local drives that can be picked."""
    out = []
    for i in range(26):
        d = f"{chr(65 + i)}:\\"
        try:
            if os.path.isdir(d):
                u = shutil.disk_usage(d)
                out.append((d[:2], u.free, u.total))
        except OSError:
            continue
    return out


def command_line_value(name: str) -> str:
    """The value of `--name value` or `--name=value` on the command line ('' if absent)."""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return ""


def apply_new_location(root: str):
    """A fresh install goes to `root` (nothing is moved). The app learns it from location.json."""
    set_root(root)
    write_location(root, data_root_for(root))


def is_first_run() -> bool:
    """No install anywhere yet: the folder is worth asking about."""
    if os.path.isfile(LOCATION_FILE):
        return False
    return not is_installed(read_state().get("current"))


set_root(read_location()["install_root"] or ANCHOR)


class UpdateError(Exception):
    pass


class DriveMissing(UpdateError):
    """The drive CReaper is installed on isn't there (unplugged, offline). Never worked around by installing to C:."""


def log(msg: str):
    try:
        os.makedirs(ANCHOR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] [BOOT] {msg}\n")
    except Exception:
        pass


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, name)
    if not os.path.exists(path) and not hasattr(sys, "_MEIPASS"):      # running from source: the app's assets
        path = os.path.join(os.path.dirname(base), "desktop", name)
    return path


def is_creaper_running() -> bool:
    """Checks if CReaper.exe is currently running to avoid redundant launches."""
    try:
        output = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq CReaper.exe', '/NH'],
            text=True,
            creationflags=0x08000000
        )
        return "CReaper.exe" in output
    except Exception:
        return False


# ----------------------------------------------------------------------------
# Single instance (named mutex)
# ----------------------------------------------------------------------------
class SingleInstance:
    def __init__(self):
        self._handle = None

    def acquire(self) -> bool:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = ctypes.c_void_p
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        self._handle = k32.CreateMutexW(None, False, "Local\\CReaperBootstrapper.Singleton")
        return ctypes.get_last_error() != 183


# ----------------------------------------------------------------------------
# State / filesystem helpers
# ----------------------------------------------------------------------------
def read_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def write_state(state: dict):
    os.makedirs(ROOT, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_FILE)


def version_dir(v: str) -> str:
    return os.path.join(VERSIONS_DIR, v)


def version_exe(v: str) -> str:
    return os.path.join(version_dir(v), APP_EXE)


def is_installed(v) -> bool:
    return isinstance(v, str) and bool(VERSION_RE.fullmatch(v)) and os.path.isfile(version_exe(v))


def wipe(path: str):
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def replace_retry(src: str, dst: str, tries: int = 6):
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(1)


# ----------------------------------------------------------------------------
# Network
# ----------------------------------------------------------------------------
class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith("https://"):
            raise UpdateError("Refusing to follow a redirect to a non-HTTPS URL.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_ssl_context() -> ssl.SSLContext:
    """
    Full certificate verification against BOTH:
      * the Windows certificate store (keeps corporate proxies / antivirus HTTPS scanning working), and
      * Mozilla's root list (certifi, bundled into the launcher).
    Python only reads the roots Windows already has; Windows downloads most roots on demand the first
    time a browser needs one, so a fresh PC can lack the root of the download server's chain
    (GitHub's release CDN) and every download failed with CERTIFICATE_VERIFY_FAILED.
    Verification is never disabled.
    """
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception as e:                      # bundle missing/unreadable: the Windows store still applies
        log(f"bundled CA certificates unavailable ({type(e).__name__}: {e}); using the Windows store only")
    return ctx


def is_certificate_error(e) -> bool:
    for x in (e, getattr(e, "reason", None), getattr(e, "__cause__", None)):
        if isinstance(x, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(x or ""):
            return True
    return False


CERT_HELP = ("CReaper couldn't verify the download server's security certificate, so nothing was "
             "downloaded. Usually one of these is the cause:\n\n"
             "•  The PC's date and time are wrong (check them in Windows Settings)\n"
             "•  Antivirus \"HTTPS scanning\" or \"web shield\" is on (pause it and try again)\n"
             "•  A school or work network is inspecting secure connections\n\nDetails: {}")


def certificate_failure(e) -> "UpdateError":
    reason = getattr(e, "reason", None) or e
    log(f"certificate verification failed: {reason}")
    return UpdateError(CERT_HELP.format(getattr(reason, "verify_message", None) or reason))


_opener = urllib.request.build_opener(_HttpsOnlyRedirect, urllib.request.HTTPSHandler(context=make_ssl_context()))


def fetch_metadata() -> dict:
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/json", "Cache-Control": "no-cache", "User-Agent": USER_AGENT})
    try:
        with _opener.open(req, timeout=20) as r:
            raw = r.read(MAX_API_BYTES + 1)
    except UpdateError:
        raise
    except (urllib.error.URLError, OSError) as e:
        if is_certificate_error(e):
            raise certificate_failure(e)
        raise UpdateError(f"Could not reach the CReaper update server.\n\n{e}")
    if len(raw) > MAX_API_BYTES:
        raise UpdateError("Update server response is too large.")
    try:
        d = json.loads(raw.decode("utf-8"))
        version = str(d["version"]).strip()
        url = str(d["download_url"]).strip()
        size = d["size"]
        sha = str(d["sha256"]).strip().lower()
    except Exception:
        raise UpdateError("The update server returned an invalid response.")
    return {"version": version, "download_url": url, "size": size, "sha256": sha}


def _download_once(meta: dict, dest: str, progress):
    size = meta["size"]
    h = hashlib.sha256()
    written = 0
    req = urllib.request.Request(meta["download_url"], headers={"User-Agent": USER_AGENT})
    with _opener.open(req, timeout=30) as r, open(dest, "wb") as f:
        cl = r.headers.get("Content-Length")
        if cl and cl.isdigit() and int(cl) != size:
            raise UpdateError("Server file size does not match the update metadata.")
        while True:
            chunk = r.read(CHUNK)
            if not chunk:
                break
            written += len(chunk)
            if written > size:
                raise UpdateError("Downloaded file is larger than expected.")
            h.update(chunk)
            f.write(chunk)
            progress(written, size)
        f.flush()
        os.fsync(f.fileno())
    if written != size:
        raise UpdateError(f"Download incomplete ({written} of {size} bytes).")
    if h.hexdigest() != meta["sha256"]:
        raise UpdateError("Downloaded file failed SHA-256 verification.")


def download_package(meta: dict, dest: str, progress):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    free = shutil.disk_usage(os.path.dirname(dest)).free
    if free < meta["size"] * 3:
        raise UpdateError("Not enough free disk space to install the update.")
    last = None
    for attempt in range(1, 4):
        try:
            _download_once(meta, dest, progress)
            return
        except (UpdateError, urllib.error.URLError, OSError) as e:
            last = e
            log(f"download attempt {attempt} failed: {e}")
            wipe(dest)
            if is_certificate_error(e):
                raise certificate_failure(e)           # retrying can't fix an untrusted certificate
            if attempt < 3:
                time.sleep(2 * attempt)
    raise UpdateError(f"Download failed.\n\n{last}")


def extract_package(zip_path: str, target: str, progress):
    os.makedirs(target, exist_ok=True)
    base = os.path.realpath(target)
    try:
        with zipfile.ZipFile(zip_path) as z:
            infos = z.infolist()
            for i in infos:
                dest = os.path.realpath(os.path.join(base, i.filename))
                if dest != base and not dest.startswith(base + os.sep):
                    raise UpdateError("Package contains an unsafe path.")
            total = sum(i.file_size for i in infos) or 1
            done = 0
            for i in infos:
                z.extract(i, base)
                done += i.file_size
                progress(done, total)
    except zipfile.BadZipFile:
        raise UpdateError("The downloaded package is not a valid archive.")
    if not os.path.isfile(os.path.join(base, APP_EXE)):
        raise UpdateError(f"Package is missing {APP_EXE}.")


# ----------------------------------------------------------------------------
# Install / cleanup / shortcuts / launch
# ----------------------------------------------------------------------------
def install_version(meta: dict, state: dict, status_cb, progress_cb):
    ver = meta["version"]
    wipe(STAGING_DIR)
    wipe(DOWNLOAD_DIR)
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(VERSIONS_DIR, exist_ok=True)

    part = os.path.join(DOWNLOAD_DIR, f"CReaper-{ver}.zip.part")
    status_cb("Downloading")
    download_package(meta, part, progress_cb)

    status_cb("Extracting")
    stage = os.path.join(STAGING_DIR, ver)
    extract_package(part, stage, progress_cb)
    wipe(part)

    target = version_dir(ver)
    if os.path.exists(target):
        replace_retry(target, os.path.join(STAGING_DIR, "old-" + ver))
    replace_retry(stage, target)

    old = state.get("current")
    if is_installed(old) and old != ver:
        state["previous"] = old
    state["current"] = ver
    state.pop("failed", None)
    write_state(state)
    log(f"installed {ver} (previous={state.get('previous')})")


def install_self() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    src = os.path.abspath(sys.executable)
    dst = os.path.join(ROOT, BOOT_EXE)
    if os.path.normcase(src) == os.path.normcase(dst):
        return True
    try:
        os.makedirs(ROOT, exist_ok=True)
        tmp = dst + ".new"
        shutil.copy2(src, tmp)
        replace_retry(tmp, dst, tries=3)
        return True
    except Exception as e:
        log(f"self-install failed: {e}")
        return os.path.isfile(dst)


_LNK_PS = (
    "$ws=New-Object -ComObject WScript.Shell;"
    "$d=[Environment]::GetFolderPath($env:CR_FOLDER);"
    "if(-not(Test-Path $d)){New-Item -ItemType Directory -Path $d|Out-Null};"
    "$s=$ws.CreateShortcut((Join-Path $d ($env:CR_NAME+'.lnk')));"
    "$s.TargetPath=$env:CR_TARGET;$s.WorkingDirectory=$env:CR_WORKDIR;"
    "$s.IconLocation=($env:CR_TARGET+',0');$s.Description='CReaper';$s.Save()"
)


def _make_shortcut(folder: str, target: str):
    env = dict(os.environ, CR_FOLDER=folder, CR_NAME=APP_NAME, CR_TARGET=target, CR_WORKDIR=os.path.dirname(target))
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _LNK_PS],
        env=env, check=True, timeout=30, creationflags=0x08000000,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ensure_shortcuts(state: dict, did_install: bool):
    target = os.path.join(ROOT, BOOT_EXE)
    if not getattr(sys, "frozen", False) or not os.path.isfile(target):
        return
    if os.environ.get("CREAPER_NO_SHORTCUTS") == "1":      # scripted installs and tests: leave the user's shortcuts alone
        return
    start_lnk = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME + ".lnk")
    changed = did_install or state.get("shortcut_target") != target
    if changed or not os.path.isfile(start_lnk):
        try:
            _make_shortcut("Programs", target)
            if changed:
                _make_shortcut("Desktop", target)
            state["shortcut_target"] = target
            write_state(state)
        except Exception as e:
            log(f"shortcut creation failed: {e}")


def cleanup(state: dict):
    keep = {state.get("current"), state.get("previous")}
    try:
        for name in os.listdir(VERSIONS_DIR):
            if name not in keep:
                wipe(os.path.join(VERSIONS_DIR, name))
    except FileNotFoundError:
        pass
    wipe(STAGING_DIR)
    wipe(DOWNLOAD_DIR)
    try:
        for name in os.listdir(ROOT):
            low = name.lower()
            if low.startswith("app-") or low in ("packages", ".dead", "update.exe", "squirrelsetup.log"):
                wipe(os.path.join(ROOT, name))
    except Exception:
        pass
    retire_old_install()


def dir_size(path: str) -> int:
    total = 0
    for base, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    return total


def data_root_for(install_root: str) -> str:
    """Where the bulky app data goes for an install folder: next to it, unless it is the default folder."""
    if os.path.normcase(install_root) == os.path.normcase(ANCHOR):
        return ANCHOR
    return os.path.join(install_root, "data")


def migrate_install(old_root: str, old_data: str, new_root: str, new_data: str, state: dict, status_cb) -> str:
    """Carries an existing install and its data to another folder or drive. Copy first, delete last: whatever fails,
    the old install keeps working.
      * the installed version folders: all or nothing (UpdateError, and nothing has changed);
      * the bulky data folders (BULK_DIRS): one by one; one that can't be carried stays where it is and is still
        found there by the app (desktop/utils/install_location.data_path).
    Returns the data root that is in effect afterwards (new_data, or old_data if a data folder had to stay)."""
    versions_new = os.path.join(new_root, "versions")
    os.makedirs(versions_new, exist_ok=True)
    keep = [v for v in dict.fromkeys((state.get("current"), state.get("previous")))
            if isinstance(v, str) and VERSION_RE.fullmatch(v)
            and os.path.isfile(os.path.join(old_root, "versions", v, APP_EXE))]
    todo = [(v, os.path.join(old_root, "versions", v), os.path.join(versions_new, v)) for v in keep
            if not os.path.isfile(os.path.join(versions_new, v, APP_EXE))]
    bulk = [(n, os.path.join(old_data, n), os.path.join(new_data, n)) for n in BULK_DIRS
            if os.path.isdir(os.path.join(old_data, n)) and not os.path.exists(os.path.join(new_data, n))]
    need = sum(dir_size(src) for _v, src, _d in todo) + sum(dir_size(src) for _n, src, _d in bulk)
    free = shutil.disk_usage(new_root).free
    if free < need + MIN_FREE_BYTES:
        raise UpdateError(f"{new_root[:2]} doesn't have enough free space: {human_bytes(need + MIN_FREE_BYTES)} needed, "
                          f"{human_bytes(free)} free.")

    done = []
    try:
        for v, src, dst in todo:
            status_cb(f"Moving CReaper {v}")
            wipe(dst)
            shutil.copytree(src, dst, symlinks=True)
            done.append(dst)
    except Exception as e:
        for dst in [d for _v, _s, d in todo]:
            wipe(dst)
        raise UpdateError(f"Couldn't copy CReaper to {new_root}.\n\n{e}")

    stayed = False
    for name, src, dst in bulk:
        status_cb(f"Moving your {name} folder")
        try:
            shutil.copytree(src, dst, symlinks=True)
            wipe(src)
        except Exception as e:
            log(f"data folder {name} could not be moved and stays at {old_data}: {e}")
            wipe(dst)                                  # a half copy must never hide the complete original
            stayed = True
    data_in_effect = old_data if (stayed and os.path.normcase(old_data) != os.path.normcase(ANCHOR)) else new_data

    # switch over: the new state and pointer first, the old files last
    set_root(new_root)
    state.pop("shortcut_target", None)                 # shortcuts are made again for the new launcher
    write_state(state)
    write_location(new_root, data_in_effect)
    for v, src, _dst in todo:
        wipe(src)
    wipe(os.path.join(old_root, "state.json"))
    log(f"moved the install {old_root} -> {new_root} (data: {data_in_effect})")
    return data_in_effect


def retire_old_install():
    """After a move: what the old default folder still holds of the install (never the user's data or settings)."""
    if os.path.normcase(ROOT) == os.path.normcase(ANCHOR):
        return
    for name in ("versions", "staging", "downloads", "state.json"):
        wipe(os.path.join(ANCHOR, name))
    old_exe = os.path.join(ANCHOR, BOOT_EXE)
    mine = os.path.normcase(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else ""
    if os.path.isfile(old_exe) and os.path.normcase(old_exe) != mine:
        try:
            os.remove(old_exe)
        except OSError:
            pass                                       # still running or locked: removed on a later start


def launch(version: str):
    exe = version_exe(version)
    token = secrets.token_hex(16)
    os.makedirs(ANCHOR, exist_ok=True)
    with open(HANDOFF_FILE, "w", encoding="utf-8") as f:
        f.write(f"{token}:{time.time()}")
    env = dict(os.environ, CREAPER_BOOTSTRAPPER_TOKEN=token)
    log(f"launching {exe}")
    subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env, close_fds=True,
                     creationflags=0x00000008 | 0x00000200)


def recently_failed(state: dict, version: str) -> bool:
    f = state.get("failed")
    try:
        return isinstance(f, dict) and f.get("version") == version and time.time() - float(f.get("time", 0)) < FAIL_BACKOFF
    except Exception:
        return False


# ----------------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------------
class Worker(QThread):
    status = pyqtSignal(str)
    progress = pyqtSignal(int)
    transfer = pyqtSignal(object, object)   # bytes done, bytes total (speed / time left in the window)
    version = pyqtSignal(str)               # the version being checked / installed
    ready = pyqtSignal(bool, str)       # is_new_install, version
    failed = pyqtSignal(str)
    drive_missing = pyqtSignal(str)         # the install drive isn't there: the window offers another folder
    migrate = None                          # (old_root, old_data, new_root, new_data): carry an install to a new folder

    def _progress_cb(self):
        last = [0.0]
        def cb(done, total):
            now = time.monotonic()
            if done < total and now - last[0] < 0.08:
                return
            last[0] = now
            self.progress.emit(int(done * 1000 / total))
            self.transfer.emit(done, total)
        return cb

    def run(self):
        try:
            self._flow()
        except DriveMissing as e:
            log(f"error: {e}")
            self.drive_missing.emit(str(e))
        except UpdateError as e:
            log(f"error: {e}")
            self.failed.emit(str(e))
        except Exception as e:
            log(traceback.format_exc())
            self.failed.emit(f"Unexpected error: {e}")

    def _flow(self):
        if self.migrate:
            old_root, old_data, new_root, new_data = self.migrate
            self.progress.emit(-1)
            self.status.emit("Moving your files")
            migrate_install(old_root, old_data, new_root, new_data, read_state(), self.status.emit)
            self.migrate = None
        if not drive_ready(ROOT):
            raise DriveMissing(f"The drive {os.path.splitdrive(ROOT)[0]} that CReaper is installed on isn't available.\n\n"
                               f"Connect it and try again, or choose another folder.")
        os.makedirs(VERSIONS_DIR, exist_ok=True)
        self.status.emit("Checking for updates")
        self.progress.emit(-1)
        state = read_state()
        wipe(STAGING_DIR)
        wipe(DOWNLOAD_DIR)

        meta = fetch_metadata()
        self.version.emit(meta["version"])
        ok = is_installed(state.get("current"))
        need = (not ok) or state.get("current") != meta["version"]
        if need and ok and recently_failed(state, meta["version"]):
            log(f"skipping {meta['version']}: it failed recently")
            need = False

        did_install = False
        if need:
            try:
                install_version(meta, state, self.status.emit, self._progress_cb())
                did_install = True
            except Exception as e:
                wipe(STAGING_DIR)
                wipe(DOWNLOAD_DIR)
                if ALLOW_LAUNCH_OLD_ON_UPDATE_FAILURE and ok:
                    log(f"update failed: {e}")
                elif isinstance(e, UpdateError):
                    raise
                else:
                    raise UpdateError(f"Installation failed.\n\n{e}")

        if not install_self() and getattr(sys, "frozen", False):
            raise UpdateError("Could not install the launcher into the CReaper folder.")
        
        ensure_shortcuts(state, did_install)
        cleanup(state)

        cur = state.get("current") or meta["version"]
        self.ready.emit(did_install, cur)


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
# The launcher window. Drawn in CReaper's own look (zinc neutrals, the purple accent, Segoe UI Variable)
# so it reads as the app's front door. One window for every state: working (checking / downloading /
# unpacking), installed, up to date, and failed (the error lives here too, no stock Windows message box).
C_BG = "#0F0F11"
C_SURFACE = "#18181B"
C_BORDER = "#27272A"
C_BORDER_HI = "#3F3F46"
C_TEXT = "#FAFAFA"
C_MUTED = "#A1A1AA"
C_SUBTLE = "#71717A"
C_ACCENT = "#9333EA"
C_ACCENT_HOVER = "#7E22CE"
C_ACCENT_PRESSED = "#6B21A8"
C_ACCENT_LIGHT = "#A855F7"
C_OK = "#10B981"
C_BAD = "#EF4444"
SHADOW_PAD = 26                    # transparent margin the card's shadow falls into
CARD_W = 460


def ui_font(px: int, weight=QFont.Weight.Normal, tabular=False) -> QFont:
    f = QFont()
    f.setFamilies(["Segoe UI Variable Text", "Segoe UI"])
    f.setPixelSize(px)
    f.setWeight(weight)
    if tabular:
        try:
            f.setFeature(QFont.Tag("tnum"), 1)       # numbers that don't jitter while they count
        except Exception:
            pass
    return f


def human_bytes(n: float) -> str:
    n = float(n or 0)
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.0f} MB" if n >= 100 * 1024 ** 2 else f"{n / 1024 ** 2:.1f} MB"
    return f"{max(0.0, n) / 1024:.0f} KB"


def human_eta(seconds: float) -> str:
    s = int(round(seconds))
    if s < 5:
        return "a few seconds left"
    if s < 60:
        return f"about {s} s left"
    m = round(s / 60)
    return f"about {m} min left" if m < 60 else f"about {m // 60} h {m % 60:02d} min left"


def error_title(message: str) -> str:
    low = (message or "").lower()
    if "security certificate" in low:
        return "Couldn't verify the download"
    if "could not reach" in low or "lost connection" in low:
        return "Can't reach the CReaper server"
    if "disk space" in low:
        return "Not enough disk space"
    if "download" in low:
        return "The download didn't finish"
    return "CReaper couldn't be installed"


class _Glyph(QWidget):
    """A small line icon drawn with QPainter: 'close', 'check', 'alert', 'folder'."""

    def __init__(self, kind: str, colour: str, size: int = 16, stroke: float = 1.7):
        super().__init__()
        self.kind, self.colour, self.stroke = kind, QColor(colour), stroke
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_colour(self, colour: str):
        self.colour = QColor(colour)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        k = self.width() / 24.0
        p.scale(k, k)
        p.setPen(QPen(self.colour, self.stroke / k * (24 / 16) if self.width() <= 16 else self.stroke,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        if self.kind == "close":
            p.drawLine(QPointF(7, 7), QPointF(17, 17))
            p.drawLine(QPointF(17, 7), QPointF(7, 17))
        elif self.kind == "check":
            path = QPainterPath(QPointF(6, 12.5))
            path.lineTo(10.2, 16.5)
            path.lineTo(18, 8)
            p.drawPath(path)
        elif self.kind == "alert":
            p.drawLine(QPointF(12, 7), QPointF(12, 13))
            p.drawPoint(QPointF(12, 17))
        elif self.kind == "folder":
            path = QPainterPath(QPointF(3.5, 7))
            path.lineTo(3.5, 18.5)
            path.lineTo(20.5, 18.5)
            path.lineTo(20.5, 9)
            path.lineTo(11.5, 9)
            path.lineTo(9.5, 6.5)
            path.lineTo(4, 6.5)
            path.closeSubpath()
            p.drawPath(path)


class _StateBadge(QWidget):
    """40 px tinted square with a check (installed) or an exclamation (failed), as in the app's dialogs."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(40, 40)
        self.colour = QColor(C_OK)
        self.glyph = _Glyph("check", C_OK, 24, 2.0)
        self.glyph.setParent(self)
        self.glyph.move(8, 8)

    def set_kind(self, kind: str):
        self.colour = QColor(C_OK if kind == "check" else C_BAD)
        self.glyph.kind = kind
        self.glyph.set_colour(self.colour.name())
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self.colour)
        bg.setAlpha(34)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0, 0, 40, 40), 11, 11)


class _ProgressBar(QWidget):
    """6 px track; the fill glides to each new value. Indeterminate: a soft segment sweeps across."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(6)
        self._value = 0.0
        self._phase = 0.0
        self.indeterminate = True
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(320)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._sweep = QTimer(self)
        self._sweep.setInterval(16)
        self._sweep.timeout.connect(self._tick)
        self._sweep.start()

    def _tick(self):
        self._phase = (self._phase + 0.011) % 1.0
        self.update()

    def get_value(self) -> float:
        return self._value

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, float(v)))
        self.update()

    value = pyqtProperty(float, fget=get_value, fset=set_value)

    def set_busy(self):
        self.indeterminate = True
        if not self._sweep.isActive():
            self._sweep.start()

    def glide_to(self, v: float):
        if self.indeterminate:
            self.indeterminate = False
            self._sweep.stop()
            self.set_value(0.0)
        if v < self._value:                    # a new phase (download -> unpack) starts from zero
            self._anim.stop()
            self.set_value(v)
            return
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(max(0.0, min(1.0, v)))
        self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_BORDER))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        if self.indeterminate:
            seg = w * 0.28
            x = -seg + (w + seg) * QEasingCurve(QEasingCurve.Type.InOutSine).valueForProgress(self._phase)
            grad = QLinearGradient(x, 0, x + seg, 0)
            c0, c1 = QColor(C_ACCENT_LIGHT), QColor(C_ACCENT_LIGHT)
            c0.setAlpha(0)
            grad.setColorAt(0.0, c0)
            grad.setColorAt(0.5, c1)
            grad.setColorAt(1.0, c0)
            p.setClipRect(QRectF(0, 0, w, h))
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(x, 0, seg, h), r, r)
            return
        fw = max(h, w * self._value) if self._value > 0 else 0
        if fw:
            p.setBrush(QColor(C_ACCENT_LIGHT))
            p.drawRoundedRect(QRectF(0, 0, fw, h), r, r)


class _IconButton(QPushButton):
    """The header's close button: a drawn X on a soft square that lights up on hover."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Close")
        self.setAccessibleName("Close")
        self.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 8px; }}
            QPushButton:hover {{ background: {C_BORDER}; }}
            QPushButton:pressed {{ background: {C_BORDER_HI}; }}
            QPushButton:focus {{ outline: none; border: 1px solid {C_ACCENT_LIGHT}; }}""")
        self.glyph = _Glyph("close", C_MUTED, 18, 1.8)
        self.glyph.setParent(self)
        self.glyph.move(6, 6)

    def enterEvent(self, e):
        self.glyph.set_colour(C_TEXT)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.glyph.set_colour(C_MUTED)
        super().leaveEvent(e)


def _button(text: str, primary: bool) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFixedHeight(36)
    b.setFont(ui_font(13, QFont.Weight.DemiBold))
    if primary:
        css = f"""
            QPushButton {{ background: {C_ACCENT}; color: #FFFFFF; border: none; border-radius: 9px; padding: 0 18px; }}
            QPushButton:hover {{ background: {C_ACCENT_HOVER}; }}
            QPushButton:pressed {{ background: {C_ACCENT_PRESSED}; }}
            QPushButton:disabled {{ background: {C_BORDER}; color: {C_SUBTLE}; }}
            QPushButton:focus {{ outline: none; border: 2px solid {C_ACCENT_LIGHT}; }}"""
    else:
        css = f"""
            QPushButton {{ background: {C_SURFACE}; color: {C_TEXT}; border: 1px solid {C_BORDER};
                           border-radius: 9px; padding: 0 16px; }}
            QPushButton:hover {{ background: {C_BORDER}; border-color: {C_BORDER_HI}; }}
            QPushButton:pressed {{ background: {C_BORDER_HI}; }}
            QPushButton:focus {{ outline: none; border: 1px solid {C_ACCENT_LIGHT}; }}"""
    b.setStyleSheet(css)
    return b


class ProgressWindow(QDialog):
    retry_requested = pyqtSignal()
    change_location_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("CReaper")
        self.setFixedWidth(CARD_W + 2 * SHADOW_PAD)
        self._drag_pos = None
        self.target_version = None
        self.version = ""
        self.base_status = "Checking for updates"
        self._samples = []                       # (time, bytes) for speed / time left
        self._mode = "working"
        self._relocate = False                   # the error screen offers "Choose another folder"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_PAD, SHADOW_PAD - 8, SHADOW_PAD, SHADOW_PAD + 8)
        self.card = QFrame(self)
        self.card.setObjectName("Card")
        self.card.setStyleSheet(f"QFrame#Card {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: 16px; }}")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(46)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(24, 18, 18, 22)
        lay.setSpacing(0)

        # header: logo, name, version, close
        head = QHBoxLayout()
        head.setSpacing(10)
        self.logo = QLabel()
        pm = QPixmap(resource_path("CRPR.png"))
        if not pm.isNull():
            dpr = self.devicePixelRatioF() or 1.0
            pm = pm.scaled(int(26 * dpr), int(26 * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            self.logo.setPixmap(pm)
        self.logo.setFixedSize(26, 26)
        self.name_label = QLabel("CReaper")
        self.name_label.setFont(ui_font(14, QFont.Weight.DemiBold))
        self.name_label.setStyleSheet(f"color: {C_TEXT};")
        self.version_label = QLabel("")
        self.version_label.setFont(ui_font(12, tabular=True))
        self.version_label.setStyleSheet(f"color: {C_SUBTLE};")
        self.close_btn = _IconButton()
        self.close_btn.clicked.connect(self.force_exit)
        head.addWidget(self.logo)
        head.addWidget(self.name_label)
        head.addWidget(self.version_label)
        head.addStretch()
        head.addWidget(self.close_btn)
        lay.addLayout(head)
        lay.addSpacing(22)

        # body: (badge) heading + percent, detail line, bar
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 6, 0)
        body.setSpacing(14)
        self.badge = _StateBadge()
        self.badge.hide()
        body.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        title_row = QHBoxLayout()
        self.status_label = QLabel(self.base_status)
        self.status_label.setFont(ui_font(19, QFont.Weight.DemiBold))
        self.status_label.setStyleSheet(f"color: {C_TEXT};")
        self.status_label.setWordWrap(True)
        self.percent_label = QLabel("")
        self.percent_label.setFont(ui_font(19, QFont.Weight.DemiBold, tabular=True))
        self.percent_label.setStyleSheet(f"color: {C_ACCENT_LIGHT};")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        title_row.addWidget(self.status_label, 1)
        title_row.addWidget(self.percent_label, 0, Qt.AlignmentFlag.AlignTop)
        text_col.addLayout(title_row)
        self.detail_label = QLabel("Contacting the CReaper update server")
        self.detail_label.setFont(ui_font(13, tabular=True))
        self.detail_label.setStyleSheet(f"color: {C_MUTED};")
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_col.addWidget(self.detail_label)
        body.addLayout(text_col, 1)
        lay.addLayout(body)
        lay.addSpacing(18)
        self.bar = _ProgressBar()
        bar_row = QHBoxLayout()
        bar_row.setContentsMargins(0, 0, 6, 0)
        bar_row.addWidget(self.bar)
        lay.addLayout(bar_row)
        lay.addSpacing(20)

        # footer: where it installs | actions
        foot = QHBoxLayout()
        foot.setContentsMargins(0, 0, 6, 0)
        foot.setSpacing(8)
        self.path_icon = _Glyph("folder", C_SUBTLE, 16, 1.6)
        self.path_label = QLabel()
        self.path_label.setFont(ui_font(12))
        self.path_label.setStyleSheet(f"color: {C_SUBTLE};")
        self.refresh_install_path()
        self.secondary_btn = _button("Open folder", primary=False)
        self.primary_btn = _button("Launch CReaper", primary=True)
        self.secondary_btn.hide()
        self.primary_btn.hide()
        self.secondary_btn.clicked.connect(self._on_secondary)
        self.primary_btn.clicked.connect(self._on_primary)
        for btn in (self.secondary_btn, self.primary_btn):
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        foot.addWidget(self.path_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        foot.addWidget(self.path_label, 1)
        foot.addStretch(0)
        foot.addWidget(self.secondary_btn)
        foot.addWidget(self.primary_btn)
        lay.addLayout(foot)

        self.setWindowOpacity(0.0)
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(220)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def refresh_install_path(self):
        """The footer line: the folder CReaper installs to (changes when the user picks another)."""
        self.path_label.setToolTip(ROOT)
        self.path_label.setText(QFontMetrics(self.path_label.font()).elidedText(
            f"Installs to {ROOT}", Qt.TextElideMode.ElideMiddle, CARD_W - 90))

    def restart_ui(self):
        """Back to the working screen for another attempt."""
        self.primary_btn.setEnabled(False)
        self.status_label.setText("Checking for updates")
        self.detail_label.setText("Contacting the CReaper update server")
        self._set_mode("working")
        self.bar.set_busy()

    # ---------------------------------------------------------------- appearance
    def showEvent(self, e):
        super().showEvent(e)
        if self.windowOpacity() < 1.0:
            self._fade.stop()
            self._fade.setStartValue(self.windowOpacity())
            self._fade.setEndValue(1.0)
            self._fade.start()

    def _set_mode(self, mode: str):
        """working | done | failed"""
        self._mode = mode
        working = mode == "working"
        self.bar.setVisible(working)
        self.percent_label.setVisible(working)
        self.path_icon.setVisible(working)
        self.path_label.setVisible(working)
        self.badge.setVisible(not working)
        self.secondary_btn.setVisible(not working)
        self.primary_btn.setVisible(not working)
        self.primary_btn.setEnabled(True)
        if not working:
            self.badge.set_kind("check" if mode == "done" else "alert")
        self.adjustSize()

    # ---------------------------------------------------------------- worker signals
    def set_version(self, version: str):
        self.version = version
        self.version_label.setText(f"v{version}")

    def set_status(self, text):
        self.base_status = text.rstrip(".")
        if self._mode != "working":
            self._set_mode("working")
        heading = {"Checking for updates": "Checking for updates",
                   "Downloading": f"Downloading CReaper {self.version}".strip(),
                   "Extracting": "Installing"}.get(self.base_status, self.base_status)
        self.status_label.setText(heading)
        if self.base_status == "Extracting":
            self.detail_label.setText("Unpacking files. This takes a few seconds.")
        elif self.base_status == "Checking for updates":
            self.detail_label.setText("Contacting the CReaper update server")
        elif self.base_status.startswith("Moving"):
            self.detail_label.setText(f"Copying to {ROOT if self.base_status == 'Moving your files' else 'the new folder'}. "
                                      "Large data can take a few minutes; the old copy is removed only afterwards.")
        self._samples = []

    def animate_dots(self):            # kept for compatibility: the bar shows activity now
        pass

    def set_progress(self, permille):
        if permille < 0:
            self.bar.set_busy()
            self.percent_label.setText("")
        else:
            self.bar.glide_to(permille / 1000.0)
            self.percent_label.setText(f"{min(100, max(0, permille // 10))}%")

    def on_transfer(self, done, total):
        if self.base_status != "Downloading" or not total:
            return
        now = time.monotonic()
        self._samples.append((now, done))
        self._samples = [s for s in self._samples if now - s[0] <= 4.0]
        parts = [f"{human_bytes(done)} of {human_bytes(total)}"]
        if len(self._samples) >= 2 and self._samples[-1][0] - self._samples[0][0] >= 0.8:
            (t0, b0), (t1, b1) = self._samples[0], self._samples[-1]
            speed = (b1 - b0) / max(1e-6, t1 - t0)
            if speed > 0:
                parts.append(f"{human_bytes(speed)}/s")
                parts.append(human_eta((total - done) / speed))
        self.detail_label.setText("  ·  ".join(parts))

    def show_ready(self, is_new: bool, version: str):
        self.target_version = version
        self.set_version(version)
        if is_new:
            self._set_mode("done")
            self.status_label.setText(f"CReaper {version} is installed")
            self.detail_label.setText("Shortcuts are on your desktop and in the Start menu.")
            self.secondary_btn.setText("Open folder")
            self.primary_btn.setText("Launch CReaper")
            self.primary_btn.setFocus()
        else:
            self.bar.glide_to(1.0)
            self.percent_label.setText("")
            self.status_label.setText("CReaper is up to date")
            self.detail_label.setText("Starting CReaper...")
            QTimer.singleShot(500, self.on_launch_clicked)

    def show_error(self, message: str, relocate: bool = False):
        self._set_mode("failed")
        self._relocate = relocate
        self.status_label.setText("The install drive isn't available" if relocate else error_title(message))
        self.detail_label.setText(message.strip())
        self.secondary_btn.setText("Choose another folder" if relocate else "Close")
        self.primary_btn.setText("Try again")
        self.primary_btn.setFocus()
        self.adjustSize()
        if not self.isVisible():
            self.show()

    # ---------------------------------------------------------------- actions
    def _on_primary(self):
        if self._mode == "failed":
            self.restart_ui()
            self.retry_requested.emit()
        else:
            self.on_launch_clicked()

    def _on_secondary(self):
        if self._mode == "failed":
            if self._relocate:
                self.change_location_requested.emit()
                return
            os._exit(1)
        try:
            os.startfile(ROOT)
        except OSError:
            pass

    def on_launch_clicked(self):
        self.primary_btn.setEnabled(False)
        self.status_label.setText("Starting CReaper")
        if self.target_version:
            launch(self.target_version)
        time.sleep(0.2)
        os._exit(0)

    def force_exit(self):
        os._exit(0)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.force_exit() if self._mode != "failed" else os._exit(1)
            return
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.primary_btn.isVisible() and self.primary_btn.isEnabled():
            self._on_primary()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def closeEvent(self, e):
        os._exit(0)


class _DriveRow(QWidget):
    """One drive as a selectable row: letter, free space and a usage bar. Painted like the launcher's own controls."""
    chosen = pyqtSignal(str)

    def __init__(self, letter: str, free: int, total: int):
        super().__init__()
        self.letter, self.free, self.total = letter, free, total
        self.selected = False
        self.hover = False
        self.usable = free >= MIN_FREE_BYTES
        self.setFixedHeight(58)
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.usable else Qt.CursorShape.ForbiddenCursor)
        self.setMouseTracking(True)
        self.setAccessibleName(f"Drive {letter}, {human_bytes(free)} free")

    def set_selected(self, on: bool):
        self.selected = on
        self.update()

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.usable and self.rect().contains(e.position().toPoint()):
            self.chosen.emit(self.letter)
        e.accept()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        border = C_ACCENT if self.selected else (C_BORDER_HI if self.hover and self.usable else C_BORDER)
        fill = QColor(C_ACCENT)
        fill.setAlphaF(0.10)
        p.setPen(QPen(QColor(border), 1.5 if self.selected else 1.0))
        p.setBrush(fill if self.selected else QColor(C_SURFACE))
        p.drawRoundedRect(r, 10, 10)
        dim = 1.0 if self.usable else 0.45
        p.setOpacity(dim)

        # drive letter in a small tile
        tile = QRectF(14, 13, 32, 32)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_ACCENT if self.selected else C_BORDER))
        p.drawRoundedRect(tile, 8, 8)
        p.setPen(QColor("#FFFFFF" if self.selected else C_MUTED))
        p.setFont(ui_font(14, QFont.Weight.DemiBold))
        p.drawText(tile, Qt.AlignmentFlag.AlignCenter, self.letter.rstrip(":"))

        # name and free space
        p.setPen(QColor(C_TEXT))
        p.setFont(ui_font(13, QFont.Weight.DemiBold))
        p.drawText(QRectF(58, 10, self.width() - 160, 20), Qt.AlignmentFlag.AlignVCenter, f"Drive {self.letter.rstrip(':')}")
        p.setPen(QColor(C_BAD if not self.usable else C_MUTED))
        p.setFont(ui_font(12))
        sub = f"{human_bytes(self.free)} free of {human_bytes(self.total)}"
        if not self.usable:
            sub = f"Only {human_bytes(self.free)} free, not enough"
        p.drawText(QRectF(58, 29, self.width() - 160, 18), Qt.AlignmentFlag.AlignVCenter, sub)

        # usage bar (the same slim track as the progress bar)
        bar = QRectF(self.width() - 118, 24, 100, 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_BORDER))
        p.drawRoundedRect(bar, 3, 3)
        used = 0.0 if not self.total else max(0.0, min(1.0, 1.0 - self.free / self.total))
        if used > 0:
            p.setBrush(QColor(C_BAD if used > 0.92 else C_ACCENT_LIGHT))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), max(6.0, bar.width() * used), bar.height()), 3, 3)


class _PathField(QFrame):
    """The folder box: a folder glyph, the path, and a Browse button inside one rounded outline."""

    def __init__(self, text: str):
        super().__init__()
        from PyQt6.QtWidgets import QLineEdit
        self.setObjectName("PathField")
        self.setFixedHeight(44)
        self._apply_style(False)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 6, 0)
        row.setSpacing(8)
        row.addWidget(_Glyph("folder", C_SUBTLE, 16, 1.6), 0, Qt.AlignmentFlag.AlignVCenter)
        self.edit = QLineEdit(text)
        self.edit.setFont(ui_font(13))
        self.edit.setFrame(False)
        self.edit.setStyleSheet(f"QLineEdit {{ background: transparent; color: {C_TEXT}; border: none; "
                                f"selection-background-color: {C_ACCENT}; }}")
        self.edit.setPlaceholderText("Choose a folder")
        self.edit.setCursorPosition(0)                  # show the start of a long path, not its tail
        self.browse = QPushButton("Browse")
        self.browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse.setFixedHeight(30)
        self.browse.setFont(ui_font(12, QFont.Weight.DemiBold))
        self.browse.setStyleSheet(f"""
            QPushButton {{ background: {C_BORDER}; color: {C_TEXT}; border: none; border-radius: 7px; padding: 0 12px; }}
            QPushButton:hover {{ background: {C_BORDER_HI}; }}
            QPushButton:focus {{ outline: none; border: 1px solid {C_ACCENT_LIGHT}; }}""")
        row.addWidget(self.edit, 1)
        row.addWidget(self.browse)
        self.edit.installEventFilter(self)

    def _apply_style(self, focused: bool):
        self.setStyleSheet(f"QFrame#PathField {{ background: {C_SURFACE}; border: 1px solid "
                           f"{C_ACCENT if focused else C_BORDER}; border-radius: 10px; }}")

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if obj is self.edit and ev.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self._apply_style(ev.type() == QEvent.Type.FocusIn)
        return super().eventFilter(obj, ev)


class LocationDialog(QDialog):
    """Where to install CReaper: any drive, any folder. The same card as the launcher window. The result always ends
    in a dedicated CReaper folder (see dedicated_folder) and has been checked for existence, write access and free
    space before it can be accepted."""

    def __init__(self, current: str, first_run: bool, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("CReaper")
        self.setModal(True)
        self.setFixedWidth(CARD_W + 2 * SHADOW_PAD)
        self.chosen = ""
        self._drag_pos = None
        self._first_run = first_run

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_PAD, SHADOW_PAD - 8, SHADOW_PAD, SHADOW_PAD + 8)
        self.card = QFrame(self)
        self.card.setObjectName("Card")
        self.card.setStyleSheet(f"QFrame#Card {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: 16px; }}")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(46)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(24, 18, 18, 22)
        lay.setSpacing(0)

        # header: logo, name, close (as in the launcher window)
        head = QHBoxLayout()
        head.setSpacing(10)
        logo = QLabel()
        pm = QPixmap(resource_path("CRPR.png"))
        if not pm.isNull():
            dpr = self.devicePixelRatioF() or 1.0
            pm = pm.scaled(int(26 * dpr), int(26 * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            logo.setPixmap(pm)
        logo.setFixedSize(26, 26)
        name = QLabel("CReaper")
        name.setFont(ui_font(14, QFont.Weight.DemiBold))
        name.setStyleSheet(f"color: {C_TEXT};")
        close = _IconButton()
        close.clicked.connect(self.reject)
        head.addWidget(logo)
        head.addWidget(name)
        head.addStretch()
        head.addWidget(close)
        lay.addLayout(head)
        lay.addSpacing(20)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 6, 0)
        body.setSpacing(0)
        title = QLabel("Where should CReaper be installed?" if first_run else "Move CReaper to another folder")
        title.setFont(ui_font(19, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {C_TEXT};")
        title.setWordWrap(True)
        body.addWidget(title)
        body.addSpacing(6)
        intro = QLabel("The app, its AI models, projects and work files all go there, so a full C: drive is no problem. "
                       "Your account and settings stay in your Windows profile." if first_run else
                       "CReaper and its data are copied to the new folder first, then removed from the old one. "
                       "Your account and settings stay where they are.")
        intro.setWordWrap(True)
        intro.setFont(ui_font(13))
        intro.setStyleSheet(f"color: {C_MUTED};")
        body.addWidget(intro)
        body.addSpacing(16)

        self.rows = []
        rows_lay = QVBoxLayout()
        rows_lay.setSpacing(8)
        for letter, free, total in drives():
            row = _DriveRow(letter, free, total)
            row.chosen.connect(self._drive_chosen)
            self.rows.append(row)
            rows_lay.addWidget(row)
        body.addLayout(rows_lay)
        body.addSpacing(14)

        folder_lbl = QLabel("Folder")
        folder_lbl.setFont(ui_font(12, QFont.Weight.DemiBold))
        folder_lbl.setStyleSheet(f"color: {C_SUBTLE};")
        body.addWidget(folder_lbl)
        body.addSpacing(6)
        self.field = _PathField(current)
        self.field.browse.clicked.connect(self._browse)
        self.field.edit.textChanged.connect(self._refresh_note)
        self.path_edit = self.field.edit
        body.addWidget(self.field)
        body.addSpacing(10)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setFont(ui_font(12, tabular=True))
        self.note.setMinimumHeight(34)
        self.note.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.addWidget(self.note)
        lay.addLayout(body)
        lay.addSpacing(14)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 6, 0)
        buttons.setSpacing(8)
        buttons.addStretch()
        self.cancel_btn = _button("Cancel", primary=False)
        self.ok = _button("Install" if first_run else "Move", primary=True)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok.clicked.connect(self._accept)
        self.ok.setDefault(True)
        self.cancel_btn.setMinimumWidth(92)
        self.ok.setMinimumWidth(104)                    # "Install" was clipped at the default width
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.ok)
        lay.addLayout(buttons)

        self._select_row(os.path.splitdrive(current)[0].upper())
        self._refresh_note()

    # ---------------------------------------------------------------- behaviour
    def _select_row(self, letter: str):
        for row in self.rows:
            row.set_selected(row.letter.upper() == letter.upper())

    def _drive_chosen(self, letter: str):
        self._select_row(letter)
        if os.path.splitdrive(self.path_edit.text())[0].upper() != letter.upper():
            self.path_edit.setText(os.path.join(letter + os.sep, FOLDER_NAME))
            self.path_edit.setCursorPosition(0)

    def _browse(self):
        from PyQt6.QtWidgets import QFileDialog
        text = self.path_edit.text()
        start = text if os.path.isdir(os.path.dirname(text) or ".") and text else os.path.expanduser("~")
        picked = QFileDialog.getExistingDirectory(self, "Choose where to install CReaper", start)
        if picked:
            self.path_edit.setText(os.path.normpath(picked))
            self.path_edit.setCursorPosition(0)

    def _refresh_note(self):
        """Where it will really go, or why it can't be used. Shown while typing; creates nothing."""
        text = self.path_edit.text()
        self._select_row(os.path.splitdrive(text)[0].upper())
        root = dedicated_folder(text)
        bad = True
        if not root:
            msg = "Enter a full folder path, for example D:" + os.sep + FOLDER_NAME
        elif root.startswith(os.sep * 2):
            msg = "Network folders are not supported. Pick a folder on a drive in this PC."
        elif not drive_ready(root):
            msg = f"The drive {os.path.splitdrive(root)[0]} is not available."
        elif len(root) > MAX_ROOT_LEN:
            msg = f"That path is too long ({len(root)} characters, at most {MAX_ROOT_LEN}). Choose a shorter folder."
        else:
            free = shutil.disk_usage(os.path.splitdrive(root)[0] + os.sep).free
            if free < MIN_FREE_BYTES:
                msg = f"{root[:2]} has only {human_bytes(free)} free. CReaper needs at least {human_bytes(MIN_FREE_BYTES)}."
            else:
                bad = False
                msg = f"Installs to {root}"
        self.note.setText(msg)
        self.note.setStyleSheet(f"color: {C_BAD if bad else C_MUTED};")
        self.ok.setEnabled(not bad)

    def _accept(self):
        root, err = check_install_folder(self.path_edit.text())
        if err:
            self.note.setText(err)
            self.note.setStyleSheet(f"color: {C_BAD};")
            return
        self.chosen = root
        self.accept()

    # ---------------------------------------------------------------- window behaviour (as the launcher window)
    def showEvent(self, e):
        super().showEvent(e)
        self.adjustSize()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.ok.isEnabled():
            self._accept()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()


def ask_location(current: str, first_run: bool) -> str:
    """The folder the user picked ('' = cancelled)."""
    dlg = LocationDialog(dedicated_folder(current) or current, first_run)
    return dlg.chosen if dlg.exec() == QDialog.DialogCode.Accepted else ""


class Controller(QObject):
    def __init__(self, app, win, migrate=None):
        super().__init__()
        self.app, self.win, self.worker = app, win, None
        self.migrate = migrate
        win.retry_requested.connect(self.start)
        win.change_location_requested.connect(self.change_location)
        self.start()

    def change_location(self):
        """From the error screen (the install drive is gone): pick another folder, then install there."""
        root = ask_location(ROOT, first_run=True)
        if not root:
            return
        apply_new_location(root)
        self.win.restart_ui()
        self.start()

    def start(self):
        w = Worker()
        w.migrate, self.migrate = self.migrate, None
        self.win.refresh_install_path()
        w.status.connect(self.win.set_status)
        w.progress.connect(self.win.set_progress)
        w.transfer.connect(self.win.on_transfer)
        w.version.connect(self.win.set_version)
        w.ready.connect(self.win.show_ready)
        w.failed.connect(self.on_fail)
        w.drive_missing.connect(lambda msg: self.win.show_error(msg, relocate=True))
        self.worker = w
        w.start()
        self.win.show()

    def on_fail(self, msg):
        self.win.show_error(msg)


def main() -> int:
    if sys.platform != "win32":
        return 1

    if is_creaper_running():
        if not ("--change-location" in sys.argv or command_line_value("--install-dir")):
            return 0
        # asked to move the install by the app, which is closing: nothing may be moved while it runs
        deadline = time.monotonic() + 30
        while is_creaper_running() and time.monotonic() < deadline:
            time.sleep(0.5)
        if is_creaper_running():
            return 0

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    icon = resource_path("CRPR.ico")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    lock = SingleInstance()
    if not lock.acquire():
        return 0

    # Where to install: asked once on a first install. Afterwards `CReaperBootstrapper.exe --change-location` moves
    # the install. `--install-dir <folder>` answers the question without a dialog (silent installs, scripts, tests).
    migrate = None
    wanted = command_line_value("--install-dir")
    first = is_first_run()
    if first or wanted or "--change-location" in sys.argv:
        if wanted:
            root, err = check_install_folder(wanted)
            if err:
                log(f"--install-dir {wanted!r} refused: {err}")
                return 2
        else:
            root = ask_location(ROOT, first_run=first)
        if not root:
            if first:
                return 0                                # cancelled the first install
        elif first:
            apply_new_location(root)
        elif os.path.normcase(root) != os.path.normcase(ROOT):
            old_data = read_location()["data_root"] or ANCHOR
            migrate = (ROOT, old_data, root, data_root_for(root))

    win = ProgressWindow()
    ctrl = Controller(app, win, migrate)
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log(traceback.format_exc())
        os._exit(1)