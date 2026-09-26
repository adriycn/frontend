import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal

class YouTubeCheckerThread(QThread):
    success_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    self.error_signal.emit("Could not extract video information.")
                    return
                
                self.success_signal.emit({
                    'title': info.get('title', 'Unknown Title'),
                    'duration': info.get('duration', 0),
                    'url': self.url,
                    'thumbnail': info.get('thumbnail', '')
                })
        except Exception as e:
            err = str(e).lower()
            if "private" in err: self.error_signal.emit("Video is private.")
            elif "unavailable" in err: self.error_signal.emit("Video is unavailable.")
            else: self.error_signal.emit("Network or extraction error.")