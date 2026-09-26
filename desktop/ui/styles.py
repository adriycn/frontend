# Modern 2026 Desktop Aesthetic - Deep Zinc Dark Mode
MAIN_STYLE = """
QWidget {
    background-color: #09090B;
    color: #FAFAFA;
    font-family: 'Segoe UI Variable', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 14px;
}

/* FIX: Ensure all labels have transparent backgrounds so they sit naturally on cards */
QLabel {
    background: transparent;
}

/* Base Inputs */
QLineEdit {
    background-color: #18181B;
    border: 1px solid #27272A;
    padding: 10px 14px;
    border-radius: 8px;
    color: #FAFAFA;
    font-size: 14px;
    selection-background-color: #3B82F6;
}
QLineEdit:focus {
    border: 1px solid #3B82F6;
    background-color: #1F1F22;
}
QLineEdit:disabled {
    background-color: #121214;
    color: #52525B;
    border: 1px solid #27272A;
}

/* Primary Buttons */
QPushButton {
    background-color: #3B82F6;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #2563EB;
}
QPushButton:pressed {
    background-color: #1D4ED8;
}
QPushButton:disabled {
    background-color: #27272A;
    color: #52525B;
}

/* Secondary/Ghost Buttons */
QPushButton#secondaryBtn {
    background-color: transparent;
    border: 1px solid #3F3F46;
    color: #D4D4D8;
}
QPushButton#secondaryBtn:hover {
    background-color: #27272A;
    color: #FAFAFA;
}

/* Hero Trim Button */
QPushButton#trimButton {
    background-color: #10B981;
    font-size: 16px;
    padding: 14px;
    border-radius: 10px;
    font-weight: bold;
}
QPushButton#trimButton:hover {
    background-color: #059669;
}
QPushButton#trimButton:disabled {
    background-color: #27272A;
    color: #52525B;
}

/* Typography */
QLabel#appTitle {
    font-size: 22px;
    font-weight: 800;
    color: #FAFAFA;
    letter-spacing: -0.5px;
}
QLabel#appWatermark {
    font-size: 12px;
    font-weight: 700;
    color: #3B82F6;
    background-color: rgba(59, 130, 246, 0.15); /* Soft blue background for the tag */
    padding: 4px 8px;
    border-radius: 6px;
}
QLabel#h1 {
    font-size: 24px;
    font-weight: bold;
    color: #FAFAFA;
    letter-spacing: -0.5px;
}
QLabel#h2 {
    font-size: 16px;
    font-weight: 600;
    color: #FAFAFA;
}
QLabel#subtitle {
    font-size: 13px;
    color: #A1A1AA;
}
QLabel#errorText {
    color: #EF4444;
    font-weight: 500;
}
QLabel#successText {
    color: #10B981;
    font-weight: 500;
}

/* Structural Cards */
QFrame#card {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 12px;
}
QFrame#mediaCard {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 12px;
}

/* Progress Bar */
QProgressBar {
    background-color: #27272A;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: transparent;
    height: 12px;
}
QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 6px;
}
"""