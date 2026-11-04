"""
Storage overview and cache cleanup for Settings > Storage.

What is measured (everything else is never touched, and the overview says so):

  Regular "Clear Cache" (regenerable, recreated automatically when needed):
    temp         %TEMP%/creaper_*            work folders of trims, renders, previews, audio downloads
                                             (left behind by crashed or interrupted jobs)
    preview      <data>/cache/preview        preview frames
    transcripts  <data>/cache/transcripts    cached video transcripts (7-day cache)
    music        <data>/music                downloaded background-music tracks
  <data> is %LOCALAPPDATA%/CReaper, or the drive chosen in the installer (utils/install_location.py); %TEMP% is
  moved there too, so a full C: no longer stops the app.

  Advanced (shown one by one, removed only individually after a warning):
    models/...   downloaded AI models (may need downloading again, or stop working offline)
    debug.log    diagnostic log

  Never touched: exported clips, the user's own videos, settings.json / state.json (settings,
  license key), custom sounds (sounds/), the installed app (versions/, bootstrapper), ui/ assets.

Safety: every deletion target comes from this module's own fixed locations (never from a path the UI
passes in), is resolved and checked to lie inside its designated folder, and links/junctions are
removed as links without ever following them. Files changed in the last moments (TEMP: 30 min) are
treated as in use and skipped. Locked files are skipped and reported, never retried in a loop.
"""
import os
import re
import stat
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

TEMP_MIN_AGE_SEC = 30 * 60        # a %TEMP% work folder younger than this may belong to a running job
CACHE_MIN_AGE_SEC = 60            # cache files written this recently may still be in use
_TEMP_NAME = re.compile(r"^creaper_[A-Za-z0-9_\-.]+$")

_CLEAN_LOCK = threading.Lock()    # one cleanup at a time (scan + delete)


class StorageBusy(RuntimeError):
    pass


def app_data_root() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "CReaper")


def data_dir(*parts: str) -> str:
    """A bulky data folder (models, projects, caches, music): the data location chosen in the installer, or the
    app data root. Nothing is created here."""
    from utils import install_location
    return install_location.data_path(*parts)


def temp_root() -> str:
    return tempfile.gettempdir()


# --------------------------------------------------------------------------------- definitions
@dataclass
class Category:
    key: str
    label: str
    description: str
    regenerable: bool
    bytes: int = 0
    files: int = 0
    in_use_bytes: int = 0          # recent files that a clean would skip


@dataclass
class Asset:
    key: str
    label: str
    description: str
    bytes: int = 0
    exists: bool = True


@dataclass
class ScanResult:
    categories: List[Category] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def reclaimable(self) -> int:
        return sum(c.bytes - c.in_use_bytes for c in self.categories if c.regenerable)

    @property
    def cache_total(self) -> int:
        return sum(c.bytes for c in self.categories if c.regenerable)

    @property
    def total(self) -> int:
        return sum(c.bytes for c in self.categories) + sum(a.bytes for a in self.assets)


@dataclass
class CleanResult:
    freed: int = 0
    removed: int = 0
    skipped_in_use: int = 0
    failed: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.failed


_CACHE_DIRS = (   # key, path parts under app_data_root(), label, description
    ("preview", ("cache", "preview"), "Preview images",
     "Video frames used by the Auto Clipper preview. Recreated when you open a video."),
    ("transcripts", ("cache", "transcripts"), "Cached transcripts",
     "Transcripts of recently used videos, so they aren't fetched again. Fetched again when needed."),
    ("music", ("music",), "Background music cache",
     "Downloaded music tracks for Auto Clipper. Downloaded again when needed."),
)

# Downloaded model folders under models/. Anything else found there is listed as "other".
_MODEL_ASSETS = (
    ("whisper_base", (("whisper", "base"),), "Transcription model (base)",
     "Used to transcribe videos that have no captions. Downloaded again automatically the next time "
     "it is needed (about 140 MB)."),
    ("whisper_small_en", (("whisper", "small.en"), ("whisper", "models--Systran--faster-whisper-small.en")),
     "Offline caption model (small.en)",
     "Backup for word captions when the CReaper server can't be reached. It is NOT downloaded again "
     "automatically: without it, captions need the server."),
    ("legacy_whisper_base", (("models--Systran--faster-whisper-base",),), "Old transcription model copy",
     "Left behind by an older CReaper version; this version doesn't use it."),
    ("legacy_onnx", (("onnx",),), "Old alignment model (ONNX)",
     "Left behind by an older CReaper version; this version doesn't use it."),
    ("legacy_whisperx", (("whisperx",),), "Old alignment model (WhisperX)",
     "Left behind by an older CReaper version; this version doesn't use it."),
)
_LOG_ASSET = ("debug_log", "Diagnostic log",
              "Technical log used only for troubleshooting. A new one starts automatically.")


def format_bytes(n: int) -> str:
    n = max(0, int(n or 0))
    for unit, size in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= size:
            value = n / size
            return f"{value:.1f} {unit}" if value < 100 else f"{value:.0f} {unit}"
    return f"{n} B"


# --------------------------------------------------------------------------------- path safety
def _is_link(path: str) -> bool:
    try:
        if os.path.islink(path):
            return True
        isjunction = getattr(os.path, "isjunction", None)
        if isjunction and isjunction(path):
            return True
        st = os.lstat(path)
        return bool(getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    except OSError:
        return False


def _inside(path: str, root: str) -> bool:
    """True when `path` (not following a final link) is strictly inside `root`."""
    try:
        root_real = os.path.realpath(root)
        parent_real = os.path.realpath(os.path.dirname(os.path.abspath(path)))
        target = os.path.join(parent_real, os.path.basename(os.path.abspath(path)))
        return os.path.commonpath([os.path.normcase(target), os.path.normcase(root_real)]) == \
            os.path.normcase(root_real) and os.path.normcase(target) != os.path.normcase(root_real)
    except (OSError, ValueError):
        return False


def _size(path: str, min_age: float = 0.0, now: Optional[float] = None) -> Tuple[int, int, int]:
    """(bytes, files, bytes changed within min_age) without following links."""
    now = now or time.time()
    total = files = recent = 0
    try:
        if _is_link(path):
            return 0, 0, 0
        if os.path.isfile(path):
            st = os.stat(path)
            return st.st_size, 1, st.st_size if now - st.st_mtime < min_age else 0
        stack = [path]
        while stack:
            d = stack.pop()
            try:
                with os.scandir(d) as it:
                    for e in it:
                        try:
                            if e.is_symlink() or _is_link(e.path):
                                continue
                            if e.is_dir(follow_symlinks=False):
                                stack.append(e.path)
                            elif e.is_file(follow_symlinks=False):
                                st = e.stat(follow_symlinks=False)
                                total += st.st_size
                                files += 1
                                if now - st.st_mtime < min_age:
                                    recent += st.st_size
                        except OSError:
                            continue
            except OSError:
                continue
    except OSError:
        pass
    return total, files, recent


def _newest_mtime(path: str) -> float:
    newest = 0.0
    try:
        newest = os.lstat(path).st_mtime
        if os.path.isdir(path) and not _is_link(path):
            for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
                for n in filenames + dirnames:
                    try:
                        newest = max(newest, os.lstat(os.path.join(dirpath, n)).st_mtime)
                    except OSError:
                        pass
    except OSError:
        pass
    return newest


def _remove(path: str, root: str, result: CleanResult, min_age: float = 0.0, now: Optional[float] = None):
    """Deletes `path` (file, folder, or link itself) if it lies inside `root`. Never follows links."""
    now = now or time.time()
    if not _inside(path, root):
        result.failed.append((path, "outside the cache folder"))
        return
    try:
        if _is_link(path):
            # a link/junction: remove the link only, never what it points to
            (os.rmdir if os.path.isdir(path) else os.unlink)(path)
            result.removed += 1
            return
        if os.path.isdir(path):
            with os.scandir(path) as it:
                entries = [e.path for e in it]
            for p in entries:
                _remove(p, root, result, min_age, now)
            try:
                os.rmdir(path)
            except OSError:
                pass                                      # not empty: something inside was kept
            return
        st = os.lstat(path)
        if min_age and now - st.st_mtime < min_age:
            result.skipped_in_use += st.st_size
            return
        try:
            os.remove(path)
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)                 # read-only file
            os.remove(path)
        result.freed += st.st_size
        result.removed += 1
    except FileNotFoundError:
        pass
    except OSError as e:
        result.failed.append((path, "in use or access denied" if isinstance(e, PermissionError) else str(e)))


# --------------------------------------------------------------------------------- scan
def _temp_entries() -> List[str]:
    root = temp_root()
    out = []
    try:
        with os.scandir(root) as it:
            for e in it:
                if _TEMP_NAME.match(e.name):
                    out.append(e.path)
    except OSError:
        pass
    return out


def _model_paths(parts_list) -> List[str]:
    models = data_dir("models")
    return [os.path.join(models, *parts) for parts in parts_list]


def _asset_targets() -> Dict[str, Tuple[List[str], str, str, str]]:
    """key -> (paths, root that must contain them, label, description). Built only from fixed locations."""
    models = data_dir("models")
    out = {}
    known = set()
    for key, parts_list, label, desc in _MODEL_ASSETS:
        paths = _model_paths(parts_list)
        out[key] = (paths, models, label, desc)
        known.update(os.path.normcase(os.path.abspath(p)) for p in paths)
    whisper = os.path.join(models, "whisper")
    for parent in (models, whisper):
        try:
            names = sorted(os.listdir(parent))
        except OSError:
            continue
        for n in names:
            p = os.path.join(parent, n)
            if n in ("CACHEDIR.TAG",) or n.startswith(".") or os.path.normcase(os.path.abspath(p)) in known:
                continue
            if parent == models and n == "whisper":
                continue
            key = "other_" + re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.relpath(p, models))
            out[key] = ([p], models, f"Other model files ({os.path.relpath(p, models)})",
                        "Downloaded model files CReaper doesn't recognise. A feature that needs them may "
                        "have to download them again.")
    out[_LOG_ASSET[0]] = ([os.path.join(app_data_root(), "debug.log")], app_data_root(), _LOG_ASSET[1], _LOG_ASSET[2])
    # editable copies of Auto Clipper clips (timeline editor). User data: never removed by Clear Cache.
    out["clip_projects"] = ([data_dir("projects")], data_dir("projects"), "Clip editor projects",
                            "Editable copies of your Auto Clipper clips, used by Edit Clip. Your finished and exported "
                            "videos are not affected, but clips made before removing these can no longer be edited.")
    return out


def scan(now: Optional[float] = None) -> ScanResult:
    now = now or time.time()
    res = ScanResult()
    temp = Category("temp", "Temporary processing files",
                    "Work files from trims, renders, previews and downloads that weren't cleaned up "
                    "(for example after a crash).", True)
    for p in _temp_entries():
        b, f, _ = _size(p, now=now)
        temp.bytes += b
        temp.files += f
        if now - _newest_mtime(p) < TEMP_MIN_AGE_SEC:
            temp.in_use_bytes += b
    res.categories.append(temp)
    for key, parts, label, desc in _CACHE_DIRS:
        b, f, recent = _size(data_dir(*parts), CACHE_MIN_AGE_SEC, now)
        res.categories.append(Category(key, label, desc, True, b, f, recent))
    for key, (paths, _root, label, desc) in _asset_targets().items():
        existing = [p for p in paths if os.path.exists(p) or _is_link(p)]
        if not existing:
            continue
        b = sum(_size(p, now=now)[0] for p in existing)
        res.assets.append(Asset(key, label, desc, b))
    return res


# --------------------------------------------------------------------------------- cleanup
def clear_cache(now: Optional[float] = None, cancel_check: Callable[[], bool] = lambda: False) -> CleanResult:
    """Regular cleanup: regenerable caches and stale temp folders only. Never models or user data."""
    if not _CLEAN_LOCK.acquire(blocking=False):
        raise StorageBusy("A cleanup is already running.")
    try:
        now = now or time.time()
        result = CleanResult()
        troot = temp_root()
        for p in _temp_entries():
            if cancel_check():
                return result
            if now - _newest_mtime(p) < TEMP_MIN_AGE_SEC:
                result.skipped_in_use += _size(p)[0]          # may belong to a running job
                continue
            _remove(p, troot, result, now=now)
        for _key, parts, _label, _desc in _CACHE_DIRS:
            folder = data_dir(*parts)
            if not os.path.isdir(folder) or _is_link(folder):
                continue
            try:
                with os.scandir(folder) as it:
                    entries = [e.path for e in it]
            except OSError as e:
                result.failed.append((folder, str(e)))
                continue
            for p in entries:                                  # the folder itself stays
                if cancel_check():
                    return result
                _remove(p, folder, result, CACHE_MIN_AGE_SEC, now)
        return result
    finally:
        _CLEAN_LOCK.release()


def remove_asset(key: str) -> CleanResult:
    """Advanced cleanup of ONE listed asset, chosen by key (paths come from this module, not the caller)."""
    targets = _asset_targets()
    if key not in targets:
        raise KeyError("Unknown storage item.")
    if not _CLEAN_LOCK.acquire(blocking=False):
        raise StorageBusy("A cleanup is already running.")
    try:
        paths, root, _label, _desc = targets[key]
        result = CleanResult()
        for p in paths:
            if os.path.exists(p) or _is_link(p):
                _remove(p, root, result)
        if key.startswith("whisper") or key.startswith("legacy") or key.startswith("other_"):
            _forget_loaded_models()
        return result
    finally:
        _CLEAN_LOCK.release()


def _forget_loaded_models():
    """A model removed from disk must not stay 'available' because a copy is loaded in memory."""
    try:
        from services import caption_engine as ce
        with ce._MODEL_LOCK:
            ce._CACHED_MODEL = None
            ce._CACHED_MODEL_NAME = None
    except Exception:
        pass
