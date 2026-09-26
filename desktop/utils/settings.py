import os
from PyQt6.QtCore import QSettings

class AppSettings:
    def __init__(self):
        self.settings = QSettings("AdriFx", "YouTubeTrimmer")

    def get_output_folder(self) -> str:
        return self.settings.value("output_folder", os.path.join(os.path.expanduser("~"), "Downloads"))

    def set_output_folder(self, path: str):
        self.settings.setValue("output_folder", path)
        
    def get_saved_key(self) -> str:
        return self.settings.value("license_key", "")
        
    def set_saved_key(self, key: str):
        self.settings.setValue("license_key", key)