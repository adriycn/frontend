
import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal


class TrimServiceThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str, start_sec: int, end_sec: int, output_path: str):
        super().__init__()
        self.url = url
        self.start_sec = start_sec
        self.end_sec = end_sec
        self.output_path = output_path

    def progress_hook(self, d):
        if d["status"] == "downloading":
            p_str = "".join(
                c for c in d.get("_percent_str", "0")
                if c.isdigit() or c == "."
            )

            try:
                progress = int(float(p_str or 0))
            except (ValueError, TypeError):
                progress = 0

            self.progress_signal.emit(
                progress,
                "Downloading & Processing streams..."
            )

        elif d["status"] == "finished":
            self.progress_signal.emit(100, "Merging streams...")

    def run(self):
        ydl_opts = {
            # Maximum 1080p, while keeping the best available
            # MP4 video and M4A audio.
            "format": (
                "bestvideo[height<=1080][ext=mp4]+"
                "bestaudio[ext=m4a]/"
                "best[height<=1080][ext=mp4]/"
                "best"
            ),

            "outtmpl": self.output_path,

            # Only download the requested section.
            "download_ranges": lambda info, ydl: [
                {
                    "start_time": self.start_sec,
                    "end_time": self.end_sec
                }
            ],

            # Required for accurate cuts.
            "force_keyframes_at_cuts": True,

            # Always produce MP4 after merging.
            "merge_output_format": "mp4",

            # Download multiple video/audio fragments simultaneously.
            "concurrent_fragment_downloads": 8,

            # Retry failed fragments/downloads.
            "retries": 3,
            "fragment_retries": 3,

            "progress_hooks": [self.progress_hook],

            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            self.finished_signal.emit(
                True,
                "Completed successfully!"
            )

        except Exception as e:
            error = str(e).lower()

            if "ffmpeg" in error:
                self.finished_signal.emit(
                    False,
                    "FFmpeg is missing! Install and add to PATH."
                )
            else:
                self.finished_signal.emit(
                    False,
                    "Download error occurred."
                )