import os
import logging
import requests
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QFrame, 
                             QSpacerItem, QSizePolicy, QProgressBar, QFileDialog, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from .styles import MAIN_STYLE
from ui.components.range_slider import RangeSlider
from ui.auth_window import AuthWindow
from services.youtube_service import YouTubeCheckerThread
from services.trim_service import TrimServiceThread
from services.api_service import LicenseCheckerThread
from utils.helpers import format_duration, parse_duration, sanitize_filename
from utils.settings import AppSettings

# Safe background thumbnail fetcher
class ThumbnailFetcherThread(QThread):
    finished_signal = pyqtSignal(bytes)
    def __init__(self, url):
        super().__init__()
        self.url = url
    def run(self):
        try:
            resp = requests.get(self.url, timeout=5)
            if resp.status_code == 200:
                self.finished_signal.emit(resp.content)
        except Exception:
            pass # Ignore silently, fallback to empty thumbnail

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AdTrim")
        self.setMinimumSize(850, 650)
        self.setStyleSheet(MAIN_STYLE)
        
        self.settings = AppSettings()
        self.video_data = None
        self.force_hours = False
        self._pending_url = ""
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        self.auth_ui = AuthWindow(on_success_callback=self.show_main_app)
        self.main_ui = QWidget()
        self.setup_main_ui()
        
        self.stack.addWidget(self.auth_ui)
        self.stack.addWidget(self.main_ui)
        
        if self.settings.get_saved_key():
            self.auth_ui.verify_license()

    def show_main_app(self):
        self.stack.setCurrentWidget(self.main_ui)

    def setup_main_ui(self):
        layout = QVBoxLayout(self.main_ui)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # --- Header ---
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title = QLabel("AdTrim")
        title.setObjectName("appTitle")
        
        watermark = QLabel("AdriFx")
        watermark.setObjectName("appWatermark")
        
        header.addWidget(title)
        header.addSpacing(8) # Fine-tune the horizontal gap between title and branding
        header.addWidget(watermark)
        header.addStretch()
        layout.addLayout(header)

        # --- Top Input Section ---
        input_card = QFrame()
        input_card.setObjectName("card")
        input_lay = QHBoxLayout(input_card)
        input_lay.setContentsMargins(16, 16, 16, 16)
        input_lay.setSpacing(12)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here...")
        self.url_input.setMinimumHeight(44)
        
        self.check_btn = QPushButton("Check Video")
        self.check_btn.setMinimumHeight(44)
        self.check_btn.setFixedWidth(140)
        self.check_btn.clicked.connect(self.check_url)
        
        input_lay.addWidget(self.url_input)
        input_lay.addWidget(self.check_btn)
        layout.addWidget(input_card)

        # --- Feedback Status (Global) ---
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

        # --- Dynamic View Stack (Empty vs Editor) ---
        self.editor_stack = QStackedWidget()
        layout.addWidget(self.editor_stack)
        
        # 1. Empty State
        empty_state = QWidget()
        empty_lay = QVBoxLayout(empty_state)
        empty_icon = QLabel("🎬")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text = QLabel("Enter a YouTube URL to start trimming.")
        empty_text.setObjectName("subtitle")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lay.addStretch()
        empty_lay.addWidget(empty_icon)
        empty_lay.addWidget(empty_text)
        empty_lay.addStretch()
        self.editor_stack.addWidget(empty_state)
        
        # 2. Active Editor State
        editor_state = QWidget()
        editor_lay = QVBoxLayout(editor_state)
        editor_lay.setContentsMargins(0, 0, 0, 0)
        editor_lay.setSpacing(24)

        # --- Media Preview Card ---
        self.media_card = QFrame()
        self.media_card.setObjectName("mediaCard")
        media_lay = QHBoxLayout(self.media_card)
        media_lay.setContentsMargins(16, 16, 16, 16)
        media_lay.setSpacing(20)
        
        self.thumb_lbl = QLabel()
        self.thumb_lbl.setFixedSize(160, 90)
        self.thumb_lbl.setStyleSheet("background-color: #09090B; border-radius: 6px;")
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_lay = QVBoxLayout()
        self.video_title_lbl = QLabel("Video Title")
        self.video_title_lbl.setObjectName("h2")
        self.video_title_lbl.setWordWrap(True)
        self.video_dur_lbl = QLabel("00:00")
        self.video_dur_lbl.setObjectName("subtitle")
        
        info_lay.addWidget(self.video_title_lbl)
        info_lay.addWidget(self.video_dur_lbl)
        info_lay.addStretch()
        
        media_lay.addWidget(self.thumb_lbl)
        media_lay.addLayout(info_lay)
        media_lay.addStretch()
        editor_lay.addWidget(self.media_card)

        # --- Trim Controls Card ---
        trim_card = QFrame()
        trim_card.setObjectName("card")
        t_lay = QVBoxLayout(trim_card)
        t_lay.setContentsMargins(24, 24, 24, 24)
        t_lay.setSpacing(24)
        
        # Timeline
        self.slider = RangeSlider()
        self.slider.rangeChanged.connect(self.on_slider_moved)
        t_lay.addWidget(self.slider)
        
        # Exact Inputs & Output display
        times_lay = QHBoxLayout()
        
        self.st_in = QLineEdit()
        self.st_in.setFixedWidth(100)
        self.st_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.st_in.editingFinished.connect(self.on_ts_edited)
        
        self.en_in = QLineEdit()
        self.en_in.setFixedWidth(100)
        self.en_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.en_in.editingFinished.connect(self.on_ts_edited)
        
        self.out_dur_lbl = QLabel("Output: 00:00")
        self.out_dur_lbl.setObjectName("successText")
        
        times_lay.addWidget(QLabel("Start Time:"))
        times_lay.addWidget(self.st_in)
        times_lay.addStretch()
        times_lay.addWidget(self.out_dur_lbl)
        times_lay.addStretch()
        times_lay.addWidget(QLabel("End Time:"))
        times_lay.addWidget(self.en_in)
        t_lay.addLayout(times_lay)
        editor_lay.addWidget(trim_card)

        # --- Action Bar ---
        action_lay = QHBoxLayout()
        
        self.f_lbl = QLabel(f"Save to: {self.settings.get_output_folder()}")
        self.f_lbl.setObjectName("subtitle")
        f_btn = QPushButton("Change Folder")
        f_btn.setObjectName("secondaryBtn")
        f_btn.clicked.connect(self.change_folder)
        
        action_lay.addWidget(f_btn)
        action_lay.addWidget(self.f_lbl)
        action_lay.addStretch()
        
        self.trim_btn = QPushButton("Trim & Download")
        self.trim_btn.setObjectName("trimButton")
        self.trim_btn.setMinimumWidth(200)
        self.trim_btn.clicked.connect(self.start_trim)
        action_lay.addWidget(self.trim_btn)
        
        editor_lay.addLayout(action_lay)
        
        # Progress Area
        self.prog = QProgressBar()
        self.prog.hide()
        editor_lay.addWidget(self.prog)
        
        self.proc_lbl = QLabel("")
        self.proc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.proc_lbl.hide()
        editor_lay.addWidget(self.proc_lbl)

        self.editor_stack.addWidget(editor_state)
        
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def set_feedback(self, text, state="info"):
        self.status_lbl.setText(text)
        if state == "error": self.status_lbl.setObjectName("errorText")
        elif state == "success": self.status_lbl.setObjectName("successText")
        else: self.status_lbl.setObjectName("subtitle")
        
        self.status_lbl.style().unpolish(self.status_lbl)
        self.status_lbl.style().polish(self.status_lbl)
        self.status_lbl.show()

    def check_url(self):
        try:
            url = self.url_input.text().strip()
            if not url: 
                self.set_feedback("✗ Please enter a valid YouTube URL.", "error")
                return
            
            self.set_ui_en(False)
            self.editor_stack.setCurrentIndex(0) # Hide editor
            self.set_feedback("Verifying license...", "info")
            
            self._pending_url = url
            
            current_key = self.settings.get_saved_key()
            self.reverify_thread = LicenseCheckerThread(current_key)
            self.reverify_thread.result_signal.connect(self.on_reverify_result)
            self.reverify_thread.start()
        except Exception:
            logging.exception("Error starting check_url verification")
            self.set_feedback("✗ An unexpected error occurred starting verification.", "error")
            self.set_ui_en(True)

    def on_reverify_result(self, success: bool, msg: str, exp_date: str, is_network_error: bool):
        try:
            if success:
                self.set_feedback("Checking video metadata...", "info")
                self.chk_t = YouTubeCheckerThread(self._pending_url)
                self.chk_t.success_signal.connect(self.on_chk_ok)
                self.chk_t.error_signal.connect(lambda m: (self.set_feedback(f"✗ {m}", "error"), self.set_ui_en(True)))
                self.chk_t.start()
            else:
                if is_network_error:
                    self.set_feedback(f"✗ {msg}", "error")
                    self.set_ui_en(True)
                else:
                    self.settings.set_saved_key("") 
                    self.status_lbl.hide()
                    self.prog.hide()
                    self.proc_lbl.hide()
                    self.url_input.setText("")
                    self.set_ui_en(True)
                    self.editor_stack.setCurrentIndex(0)
                    
                    self.auth_ui.key_input.setText("")
                    self.auth_ui.key_input.setEnabled(True)
                    self.auth_ui.activate_btn.setEnabled(True)
                    self.auth_ui.status_label.setText("Your license is no longer valid. Please activate a valid license.")
                    self.auth_ui.status_label.setObjectName("errorText")
                    self.auth_ui.status_label.style().unpolish(self.auth_ui.status_label)
                    self.auth_ui.status_label.style().polish(self.auth_ui.status_label)
                    self.auth_ui.status_label.show()
                    
                    self.stack.setCurrentWidget(self.auth_ui)
        except Exception:
            logging.exception("Error processing re-verification result")
            self.set_feedback("✗ An unexpected error occurred processing verification.", "error")
            self.set_ui_en(True)

    def on_chk_ok(self, info):
        self.video_data = info
        d = info['duration']
        self.force_hours = d >= 3600
        
        self.status_lbl.hide()
        self.set_ui_en(True)
        self.editor_stack.setCurrentIndex(1) # Show editor
        
        self.video_title_lbl.setText(info.get('title', 'Unknown Title'))
        self.video_dur_lbl.setText(f"Total Duration: {format_duration(d, self.force_hours)}")
        
        # Load thumbnail asynchronously
        thumb_url = info.get('thumbnail')
        self.thumb_lbl.setText("No Image")
        if thumb_url:
            self.thumb_t = ThumbnailFetcherThread(thumb_url)
            self.thumb_t.finished_signal.connect(self.on_thumb_loaded)
            self.thumb_t.start()
        
        self.slider.setMaximum(d)
        self.slider.setRangeValues(0, d)
        self.upd_ts(0, d)
        self.prog.hide()
        self.proc_lbl.hide()
        self.trim_btn.show()

    def on_thumb_loaded(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # Scale beautifully to the label
            scaled = pixmap.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.thumb_lbl.setPixmap(scaled)

    def set_ui_en(self, state): 
        self.url_input.setEnabled(state)
        self.check_btn.setEnabled(state)
        self.editor_stack.setEnabled(state)

    def on_slider_moved(self, s, e): 
        self.upd_ts(s, e)

    def on_ts_edited(self):
        if not self.video_data: return
        md = self.video_data['duration']
        s = max(0, min(parse_duration(self.st_in.text()), md - 1))
        e = parse_duration(self.en_in.text())
        if e <= s: e = min(s + 1, md)
        e = max(s + 1, min(e, md))
        self.slider.setRangeValues(s, e)
        self.upd_ts(s, e)

    def upd_ts(self, s, e):
        self.st_in.setText(format_duration(s, self.force_hours))
        self.en_in.setText(format_duration(e, self.force_hours))
        # Update dynamic output duration
        self.out_dur_lbl.setText(f"Output: {format_duration(e - s, self.force_hours)}")

    def change_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Output", self.settings.get_output_folder())
        if f: 
            self.settings.set_output_folder(f)
            self.f_lbl.setText(f"Save to: {f[-35:]}...")

    def start_trim(self):
        s, e = self.slider.start_val, self.slider.end_val
        out_f = self.settings.get_output_folder()
        if not os.path.exists(out_f): return
        f_name = f"{sanitize_filename(self.video_data['title'])}_{s}-{e}.mp4"
        out_p = os.path.join(out_f, f_name)
        
        self.set_ui_en(False)
        self.trim_btn.hide()
        self.prog.setValue(0)
        self.prog.show()
        
        self.proc_lbl.setText("Starting engine...")
        self.proc_lbl.setObjectName("subtitle")
        self.proc_lbl.style().unpolish(self.proc_lbl)
        self.proc_lbl.style().polish(self.proc_lbl)
        self.proc_lbl.show()
        
        self.trim_t = TrimServiceThread(self.video_data['url'], s, e, out_p)
        self.trim_t.progress_signal.connect(lambda p, m: (self.prog.setValue(p), self.proc_lbl.setText(m)))
        self.trim_t.finished_signal.connect(self.on_trim_done)
        self.trim_t.start()

    def on_trim_done(self, ok, msg):
        self.set_ui_en(True)
        self.trim_btn.show()
        self.prog.hide()
        
        self.proc_lbl.setText(f"✓ {msg}" if ok else f"✗ {msg}")
        self.proc_lbl.setObjectName("successText" if ok else "errorText")
        self.proc_lbl.style().unpolish(self.proc_lbl)
        self.proc_lbl.style().polish(self.proc_lbl)