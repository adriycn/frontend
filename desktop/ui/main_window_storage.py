"""Settings > Storage: cache overview, Clear Cache, and advanced removal of downloaded models."""
import os
import subprocess
import sys

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.components.app_dialog import ask, inform
from utils import install_location

from services import storage_service as ss


class _StorageWorker(QThread):
    """Runs one scan / cleanup off the UI thread (folder walks can take a while on slow disks)."""
    done = pyqtSignal(object, object, str)            # (job, result, error)

    def __init__(self, job: str, fn):
        super().__init__()
        self.job, self.fn = job, fn

    def run(self):
        try:
            self.done.emit(self.job, self.fn(), "")
        except Exception as e:
            self.done.emit(self.job, None, str(e) or type(e).__name__)


class StorageManager:
    def __init__(self, main_window):
        self.mw = main_window
        self.last_scan = None
        self._worker = None
        self._workers = set()

    # ------------------------------------------------------------------ install location
    def install_location_text(self) -> str:
        """Where the app and its data live, in words ("on D: ... " when it is not the default folder)."""
        exe_root = install_location.app_root_from_exe(sys.executable) if getattr(sys, "frozen", False) else ""
        root = exe_root or install_location.install_root()
        data = install_location.data_root()
        text = f"Installed in {root}."
        if os.path.normcase(data) != os.path.normcase(install_location.anchor()):
            text += f" Models, projects and work files are kept in {data}."
        else:
            text += " Settings and sign-in stay in your Windows profile whatever you pick."
        return text

    def bootstrapper_path(self) -> str:
        """The installed launcher that can move the install ('' when this isn't a launcher install)."""
        if not getattr(sys, "frozen", False):
            return ""
        root = install_location.app_root_from_exe(sys.executable) or install_location.install_root()
        path = os.path.join(root, "CReaperBootstrapper.exe")
        return path if os.path.isfile(path) else ""

    def change_install_location(self):
        """Hands over to the launcher (`--change-location`), which copies CReaper and its data to the new folder
        while the app is closed, then starts it again. Nothing is moved from here."""
        boot = self.bootstrapper_path()
        if not boot:
            inform(self.mw, "Change install location", "The location can be changed in the installed app, started from "
                   "CReaper's launcher.", "Run CReaperBootstrapper.exe with --change-location.")
            return
        jobs = self.active_jobs()
        if jobs:
            self._status(f"Wait until {', '.join(jobs)} finishes, then change the location.", error=True)
            return
        if ask(self.mw, "Change install location", "CReaper will close, ask where to move to, copy itself and its data "
               "there, and start again.", "Your account, settings and exported clips are not affected. Moving a lot of "
               "data can take a few minutes.", [("Cancel", "cancel"), ("Continue", "primary")]) != "Continue":
            return
        try:
            subprocess.Popen([boot, "--change-location"], cwd=os.path.dirname(boot), close_fds=True,
                             creationflags=0x00000008 | 0x00000200)
        except OSError as e:
            inform(self.mw, "Change install location", "Couldn't start the launcher.", str(e), tone="warning")
            return
        self.mw.close()                                  # the launcher waits for the app to exit before it moves anything

    # ------------------------------------------------------------------ what is running
    def active_jobs(self) -> list:
        """Work that writes to / reads from the caches right now (cleanup waits until it's done)."""
        mw, jobs = self.mw, []

        def running(t):
            try:
                return t is not None and t.isRunning()
            except RuntimeError:
                return False
        cm = getattr(mw, "clipper_mgr", None)
        if cm is not None:
            if running(getattr(cm, "clipper_thread", None)):
                jobs.append("Auto Clipper")
            if any(running(t) for t in list(getattr(cm, "_meta_threads", ()))):
                jobs.append("loading a video preview")
        dm = getattr(mw, "downloader_mgr", None)
        if dm is not None and running(getattr(dm, "dl_thread", None)):
            jobs.append("a download")
        em = getattr(mw, "editor_mgr", None)
        if em is not None and running(getattr(em, "trim_t", None)):
            jobs.append("a trim export")
        wm = getattr(mw, "workflow_mgr", None)
        if wm is not None and (running(getattr(wm, "transcript_t", None)) or running(getattr(wm, "ai_t", None))
                               or any(running(t) for t in list(getattr(wm, "_prefetch_threads", ())))):
            jobs.append("AI Best Moments")
        return jobs

    # ------------------------------------------------------------------ workers
    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _start(self, job: str, fn, status: str):
        self._set_buttons(False)
        self._status(status)
        w = _StorageWorker(job, fn)
        self._worker = w
        self._workers.add(w)
        w.done.connect(self._on_done)
        w.finished.connect(lambda w=w: self._workers.discard(w))
        w.start()

    def _set_buttons(self, enabled: bool):
        # Disabling the focused button makes Qt move focus to the next button (a "Remove" further down)
        # and the scroll area jumps to it. Park focus on the scroll area itself, which doesn't scroll.
        scroll = getattr(self.mw, "storage_scroll", None)
        if not enabled and scroll is not None:
            from PyQt6.QtWidgets import QApplication
            focused = QApplication.focusWidget()
            if focused is not None and scroll.isAncestorOf(focused):
                scroll.setFocus()
        for name in ("storage_clear_btn", "storage_refresh_btn"):
            b = getattr(self.mw, name, None)
            if b is not None:
                b.setEnabled(enabled)
        for b in getattr(self.mw, "storage_asset_buttons", []):
            try:
                b.setEnabled(enabled)
            except RuntimeError:
                pass

    def _status(self, text: str, error: bool = False):
        lbl = getattr(self.mw, "storage_status_lbl", None)
        if lbl is not None:
            lbl.setText(text)
            lbl.setStyleSheet("color: #EF4444;" if error else "")

    # ------------------------------------------------------------------ actions
    def refresh(self):
        if self._busy():
            return
        self._start("scan", ss.scan, "Checking storage...")

    def clear_cache(self):
        if self._busy():
            return
        jobs = self.active_jobs()
        if jobs:
            self._status(f"Wait until {', '.join(jobs)} finishes, then clear the cache.", error=True)
            return
        scan = self.last_scan
        estimate = ss.format_bytes(scan.reclaimable) if scan else "the cached files"
        if ask(self.mw, "Clear cache", f"Clear about {estimate} of cached files? Removes temporary work files, "
               "preview images, cached transcripts and cached background music. They are recreated when needed.",
               "Your clips, videos, settings, license, custom sounds and downloaded AI models are not touched.",
               [("Cancel", "cancel"), ("Clear Cache", "danger")], tone="danger") != "Clear Cache":
            return
        self._start("clear", ss.clear_cache, "Clearing cache...")

    def remove_asset(self, key: str):
        if self._busy():
            return
        jobs = self.active_jobs()
        if jobs:
            self._status(f"Wait until {', '.join(jobs)} finishes, then remove files.", error=True)
            return
        asset = next((a for a in (self.last_scan.assets if self.last_scan else []) if a.key == key), None)
        if asset is None:
            return
        if ask(self.mw, "Remove files", f"Remove {asset.label} ({ss.format_bytes(asset.bytes)})?",
               asset.description, [("Cancel", "cancel"), ("Remove", "danger")], tone="danger") != "Remove":
            return
        self._start("remove", lambda: ss.remove_asset(key), f"Removing {asset.label}...")

    def _on_done(self, job: str, result, error: str):
        self._set_buttons(True)
        if error:
            self._status(("Couldn't check storage: " if job == "scan" else "Cleanup stopped: ") + error[:160], True)
            return
        if job == "scan":
            self.last_scan = result
            self._render(result)
            import datetime
            self._status("Updated at " + datetime.datetime.now().strftime("%I:%M:%S %p").lstrip("0") + ".")
            return
        # clear / remove: report exactly what happened, then measure again
        msg = f"Freed {ss.format_bytes(result.freed)}."
        if result.skipped_in_use:
            msg += f" {ss.format_bytes(result.skipped_in_use)} was skipped because it may still be in use."
        if result.failed:
            msg += (f" {len(result.failed)} item{'s' if len(result.failed) != 1 else ''} couldn't be removed "
                    "(in use or access denied).")
        self._after_clean_msg = (msg, bool(result.failed))
        w = _StorageWorker("scan", ss.scan)
        self._worker = w
        self._workers.add(w)
        w.done.connect(self._on_rescan)
        w.finished.connect(lambda w=w: self._workers.discard(w))
        self._set_buttons(False)
        w.start()

    def _on_rescan(self, _job, result, error):
        self._set_buttons(True)
        if result is not None:
            self.last_scan = result
            self._render(result)
        msg, partial = getattr(self, "_after_clean_msg", ("", False))
        self._status(msg, error=partial)

    # ------------------------------------------------------------------ view
    def _render(self, scan):
        mw = self.mw
        scroll = getattr(mw, "storage_scroll", None)
        keep = scroll.verticalScrollBar().value() if scroll is not None else None
        mw.storage_total_lbl.setText(ss.format_bytes(scan.cache_total))
        for c in scan.categories:
            lbl = mw.storage_category_lbls.get(c.key)
            if lbl is not None:
                lbl.setText(ss.format_bytes(c.bytes))
        mw.storage_models_total_lbl.setText(ss.format_bytes(sum(a.bytes for a in scan.assets)))
        self._render_assets(scan.assets)
        if keep is not None:                              # rebuilt rows must not move the page
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: scroll.verticalScrollBar().setValue(keep))

    def _render_assets(self, assets):
        lay = self.mw.storage_assets_lay
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.mw.storage_asset_buttons = []
        if not assets:
            empty = QLabel("No downloaded models or other removable files found.")
            empty.setObjectName("sectionHint")
            lay.addWidget(empty)
            return
        for a in assets:
            row = QWidget()
            row.setProperty("cardContent", True)
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 6, 0, 6)
            h.setSpacing(14)
            txt = QVBoxLayout()
            txt.setSpacing(2)
            t = QLabel(a.label)
            t.setObjectName("sectionTitle")
            d = QLabel(a.description)
            d.setObjectName("sectionHint")
            d.setWordWrap(True)
            txt.addWidget(t)
            txt.addWidget(d)
            size = QLabel(ss.format_bytes(a.bytes))
            size.setObjectName("metaValue")
            size.setFixedWidth(72)
            size.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            btn = QPushButton("Remove")
            btn.setObjectName("secondaryBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedWidth(92)
            btn.clicked.connect(lambda _c=False, k=a.key: self.remove_asset(k))
            h.addLayout(txt, 1)
            h.addWidget(size, 0, Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
            lay.addWidget(row)
            self.mw.storage_asset_buttons.append(btn)
