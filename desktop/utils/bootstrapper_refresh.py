"""
Keeps the installed CReaperBootstrapper.exe current.

An app update replaces the app, never the bootstrapper: every install keeps the bootstrapper it was first installed
with, and that bootstrapper asks the update server built into it. When the server moved (Dplexo -> Railway), old
bootstrappers would have stopped receiving updates once Dplexo was shut down. So each release carries its own
bootstrapper (bootstrapper/CReaperBootstrapper.exe inside the package, see build.py) and the app swaps it in when
the installed one is OLDER (by the Windows file version both are stamped with at build time; never a downgrade).

The bootstrapper has already exited when the app runs (it starts the app and quits), so the file can be replaced; a
locked file is simply tried again on the next launch.
"""
import ctypes
import os
import shutil
import sys
import threading
import time

BOOT_EXE = "CReaperBootstrapper.exe"


def file_version(path: str):
    """(major, minor, patch, build) from the exe's version resource, or None."""
    try:
        ver = ctypes.windll.version
        size = ver.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(path, 0, size, buf):
            return None
        ptr, length = ctypes.c_void_p(), ctypes.c_uint()
        if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)) or not length.value:
            return None
        fixed = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32 * 13)).contents
        ms, ls = fixed[2], fixed[3]                  # VS_FIXEDFILEINFO.dwFileVersionMS / LS
        return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return None


def paths(app_dir: str, local_app_data: str, install_root: str = ""):
    """(the bootstrapper bundled in this release, the installed one). The installed one sits in the install root,
    which is %LOCALAPPDATA%/CReaper unless the user installed to another drive."""
    root = install_root or os.path.join(local_app_data, "CReaper")
    return (os.path.join(app_dir, "bootstrapper", BOOT_EXE), os.path.join(root, BOOT_EXE))


def refresh(app_dir: str, local_app_data: str, version_of=file_version, log=lambda m: None, tries: int = 5,
            wait: float = 2.0, install_root: str = "") -> str:
    """-> what happened: "replaced" | "current" | "no_bundle" | "not_installed" | "unknown_version" | "locked"."""
    bundled, installed = paths(app_dir, local_app_data, install_root)
    if not os.path.isfile(bundled):
        return "no_bundle"
    if not os.path.isfile(installed):
        return "not_installed"                       # not a bootstrapper install (developer run): leave it
    new = version_of(bundled)
    if not new:
        return "unknown_version"
    old = version_of(installed) or (0, 0, 0, 0)      # unstamped = an old build
    if old >= new:
        return "current"
    tmp = installed + ".new"
    for attempt in range(tries):
        try:
            shutil.copy2(bundled, tmp)
            os.replace(tmp, installed)
            log(f"Bootstrapper updated {'.'.join(map(str, old))} -> {'.'.join(map(str, new))}")
            return "replaced"
        except OSError as e:
            log(f"Bootstrapper update attempt {attempt + 1} failed: {e}")
            time.sleep(wait)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return "locked"


def refresh_in_background(log=lambda m: None, delay: float = 10.0) -> None:
    """Runs refresh() once, a few seconds after start (the bootstrapper is gone by then). Packaged builds only."""
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return
    app_dir = os.path.dirname(os.path.abspath(sys.executable))
    local = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    from utils import install_location
    # this app's own folder (<root>ersions\<ver>) says where the install really is
    root = install_location.app_root_from_exe(sys.executable) or install_location.install_root()

    def run():
        time.sleep(delay)
        try:
            refresh(app_dir, local, log=log, install_root=root)
        except Exception as e:                       # never let this affect the app
            log(f"Bootstrapper refresh failed: {e}")
    threading.Thread(target=run, name="bootstrapper-refresh", daemon=True).start()
