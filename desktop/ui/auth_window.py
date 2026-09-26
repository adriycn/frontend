import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt
from services.api_service import LicenseCheckerThread
from utils.settings import AppSettings

class AuthWindow(QWidget):
    def __init__(self, on_success_callback):
        super().__init__()
        self.on_success_callback = on_success_callback
        self.settings = AppSettings()
        self.checker = None
        self.init_ui()

    def init_ui(self):
        # Outer layout to center the card
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Center Card
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(420)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 48, 40, 48)
        card_layout.setSpacing(24)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("License Activation")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = QLabel("Enter your license key to unlock AdTrim.")
        desc.setObjectName("subtitle")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        
        header_layout.addWidget(title)
        header_layout.addWidget(desc)
        card_layout.addLayout(header_layout)

        # Input Area
        input_layout = QVBoxLayout()
        input_layout.setSpacing(12)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_input.setText(self.settings.get_saved_key())
        
        self.activate_btn = QPushButton("Verify License")
        self.activate_btn.clicked.connect(self.verify_license)
        
        input_layout.addWidget(self.key_input)
        input_layout.addWidget(self.activate_btn)
        card_layout.addLayout(input_layout)

        # Status Label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        card_layout.addWidget(self.status_label)
        
        # Center the card in the main window
        row_layout = QHBoxLayout()
        row_layout.addStretch()
        row_layout.addWidget(card)
        row_layout.addStretch()
        
        main_layout.addLayout(row_layout)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def verify_license(self):
        try:
            key = self.key_input.text().strip()
            if not key:
                self.status_label.setText("Please enter a license key.")
                self.status_label.setObjectName("errorText")
                self.status_label.style().unpolish(self.status_label)
                self.status_label.style().polish(self.status_label)
                self.status_label.show()
                return

            self.activate_btn.setEnabled(False)
            self.key_input.setEnabled(False)
            self.status_label.setText("Verifying with server...")
            self.status_label.setObjectName("subtitle")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            self.status_label.show()

            self.checker = LicenseCheckerThread(key)
            self.checker.result_signal.connect(self.on_result)
            self.checker.start()
        except Exception:
            logging.exception("Error initiating license verification")
            self.activate_btn.setEnabled(True)
            self.key_input.setEnabled(True)
            self.status_label.setText("Failed to start verification. Please try again.")
            self.status_label.setObjectName("errorText")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            self.status_label.show()

    def on_result(self, success: bool, msg: str, exp_date: str, is_network_error: bool):
        try:
            self.activate_btn.setEnabled(True)
            self.key_input.setEnabled(True)
            
            if success:
                self.settings.set_saved_key(self.key_input.text().strip())
                self.status_label.setText(f"{msg}\nExpires: {exp_date}")
                self.status_label.setObjectName("successText")
                self.on_success_callback()
            else:
                self.status_label.setText(f"✗ {msg}")
                self.status_label.setObjectName("errorText")
                
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            
        except Exception:
            logging.exception("Error processing verification result")
            self.status_label.setText("✗ An unexpected error occurred. Please try again.")
            self.status_label.setObjectName("errorText")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)