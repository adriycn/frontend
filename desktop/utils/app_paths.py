"""
Locations of bundled read-only assets and persistent per-user data.

Bundled assets (e.g. sfx/) are looked up, in order:
  1. <sys._MEIPASS>/<path>                    (PyInstaller: onedir _internal/ or onefile temp dir)
  2. <folder of CReaper.exe>/_internal/<path>
  3. <desktop source folder>/<path>           (development; independent of the working directory)

User data lives under %LOCALAPPDATA%/CReaper/ (the "anchor"), never next to the app or in a temp/build directory,
so it survives updates and restarts. The bulky folders (models, projects, caches, music, work files) follow the data
location the user chose in the installer (utils/install_location.py): D:/CReaper/data instead of C: when C: is full.
"""
import os
import sys

_DESKTOP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*parts: str) -> str:
    """Absolute path of a bundled asset; the first existing candidate wins (else the dev path)."""
    rel = os.path.join(*parts)
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, rel))
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "_internal", rel))
        candidates.append(os.path.join(exe_dir, rel))
    candidates.append(os.path.join(_DESKTOP_DIR, rel))
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[-1]


def user_data_dir(*parts: str) -> str:
    """The data folder <parts>, created on demand: under the anchor (%LOCALAPPDATA%/CReaper), or for the bulky
    folders under the chosen data location (install_location.BULK_DIRS)."""
    from utils import install_location
    path = install_location.data_path(*parts)
    os.makedirs(path, exist_ok=True)
    return path
