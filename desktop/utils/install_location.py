"""
Where CReaper is installed and where its bulky data lives, shared by the app and the bootstrapper.

Everything used to sit under %LOCALAPPDATA%\\CReaper, so a full C: drive meant no CReaper. Now a small pointer file
in that folder, the ANCHOR, says where the rest is:

    %LOCALAPPDATA%\\CReaper\\location.json   {"version": 1, "install_root": "D:\\\\CReaper", "data_root": "D:\\\\CReaper\\\\data"}

  install_root  versions\\<ver>\\CReaper.exe, CReaperBootstrapper.exe, state.json, staging\\, downloads\\
  data_root     BULK_DIRS (AI models, clip projects, caches, music, work files)
  anchor        always on the profile drive: this pointer, settings.json, session.dat (sign-in), device_id.json,
                debug.log, the bootstrapper hand-off file. Small, per user, found without any lookup.

No pointer = both roots are the anchor = the layout every existing install already has, so nothing moves for them.

A BULK_DIRS folder is looked for in data_root first, then in the anchor (data from before the move that has not been
carried over yet), so a failed or interrupted move never hides anyone's projects. New data goes to data_root.

bootstrapper/main.py carries its own copy of this logic (it ships as a single exe); tests/test_install_location.py
checks the two agree on the file format and on every rule below.
"""
import json
import os

LOCATION_FILE = "location.json"
FOLDER_NAME = "CReaper"
# folders that grow large and follow data_root (settings.json, session.dat, ui/, sounds/ stay with the anchor)
BULK_DIRS = ("models", "projects", "cache", "preview_cache", "music", "tmp")


def local_app_data() -> str:
    return os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")


def anchor() -> str:
    return os.path.join(local_app_data(), FOLDER_NAME)


def location_path() -> str:
    return os.path.join(anchor(), LOCATION_FILE)


def drive_of(path: str) -> str:
    """'D:' for 'D:\\x', '\\\\server\\share' for a UNC path, '' for a relative one."""
    return os.path.splitdrive(path)[0]


def drive_available(path: str) -> bool:
    d = drive_of(path)
    if not d:
        return False
    return os.path.isdir(d + os.sep)


def _clean(p) -> str:
    if not isinstance(p, str) or not p.strip():
        return ""
    p = os.path.normpath(os.path.expandvars(p.strip().strip('"')))
    return p if os.path.isabs(p) else ""


def read_location() -> dict:
    """{"install_root": str, "data_root": str} with '' for anything not set or not an absolute path."""
    try:
        with open(location_path(), "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    return {"install_root": _clean(d.get("install_root")), "data_root": _clean(d.get("data_root"))}


def write_location(install_root: str = "", data_root: str = "") -> None:
    """Records the roots ('' = the anchor, which removes the entry). Atomic: a crash never leaves half a file."""
    os.makedirs(anchor(), exist_ok=True)
    body = {"version": 1}
    if _clean(install_root) and os.path.normcase(_clean(install_root)) != os.path.normcase(anchor()):
        body["install_root"] = _clean(install_root)
    if _clean(data_root) and os.path.normcase(_clean(data_root)) != os.path.normcase(anchor()):
        body["data_root"] = _clean(data_root)
    path = location_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def install_root() -> str:
    return read_location()["install_root"] or anchor()


def data_root() -> str:
    """Where new bulk data goes. A configured drive that is not there right now (unplugged, offline) falls back
    to the anchor for this session instead of crashing the app or creating a fake D:\\ tree."""
    root = read_location()["data_root"]
    if root and drive_available(root):
        return root
    return anchor()


def app_root_from_exe(exe_path: str) -> str:
    """The install root of a running app: <root>\\versions\\<ver>\\CReaper.exe -> <root>. '' if it is not laid out so."""
    ver_dir = os.path.dirname(os.path.abspath(exe_path))
    versions = os.path.dirname(ver_dir)
    if os.path.basename(versions).lower() == "versions":
        return os.path.dirname(versions)
    return ""


def data_path(*parts: str) -> str:
    """Absolute path under the data area (not created). BULK_DIRS go to data_root, unless the folder only exists
    at the anchor (older data not carried over); everything else stays at the anchor."""
    a = anchor()
    if not parts or parts[0] not in BULK_DIRS:
        return os.path.join(a, *parts)
    root = data_root()
    if os.path.normcase(root) == os.path.normcase(a):
        return os.path.join(a, *parts)
    new_top, old_top = os.path.join(root, parts[0]), os.path.join(a, parts[0])
    top = old_top if (os.path.isdir(old_top) and not os.path.isdir(new_top)) else new_top
    return os.path.join(top, *parts[1:])


def apply_temp_dir() -> str:
    """Points TEMP/TMP at <data_root>\\tmp when the data lives off the profile drive, so FFmpeg and download work
    files do not fill C:. Call once at start, before anything uses tempfile. Returns the folder in use ('' = unchanged)."""
    root = data_root()
    if os.path.normcase(root) == os.path.normcase(anchor()):
        return ""
    tmp = os.path.join(root, "tmp")
    try:
        os.makedirs(tmp, exist_ok=True)
    except OSError:
        return ""
    for name in ("TEMP", "TMP", "TMPDIR"):
        os.environ[name] = tmp
    import tempfile
    tempfile.tempdir = tmp
    return tmp
