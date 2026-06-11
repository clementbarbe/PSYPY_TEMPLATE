"""
QSS Stylesheet for the experiment launcher.

Dark theme optimised for laboratory conditions.
"""

DARK_STYLESHEET = """

/* ═══════════════════════════════════════════
   MAIN WINDOW
   ═══════════════════════════════════════════ */

QMainWindow {
    background-color: #13141f;
}

QWidget#centralWidget {
    background-color: #13141f;
}

/* ═══════════════════════════════════════════
   HEADER
   ═══════════════════════════════════════════ */

QLabel#titleLabel {
    color: #e8e8f0;
    font-size: 18px;
    font-weight: bold;
    padding: 4px 0;
}

QLabel#subtitleLabel {
    color: #7878a0;
    font-size: 12px;
    padding-bottom: 8px;
}

/* ═══════════════════════════════════════════
   GROUP BOXES
   ═══════════════════════════════════════════ */

QGroupBox {
    font-weight: bold;
    font-size: 12px;
    border: 1px solid #2d2e42;
    border-radius: 10px;
    margin-top: 14px;
    padding: 18px 14px 14px 14px;
    background-color: #1a1b2e;
    color: #9090b0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: #8080b0;
    background-color: #1a1b2e;
}

/* ═══════════════════════════════════════════
   LABELS
   ═══════════════════════════════════════════ */

QLabel {
    color: #b0b0c8;
    font-size: 12px;
}

QLabel#infoLabel {
    color: #6868a0;
    font-size: 11px;
    padding: 6px 0;
}

QLabel#designInfo {
    color: #7c7caa;
    font-size: 11px;
    background-color: #14152a;
    border: 1px solid #2d2e42;
    border-radius: 6px;
    padding: 10px 12px;
}

/* ═══════════════════════════════════════════
   INPUT FIELDS
   ═══════════════════════════════════════════ */

QLineEdit {
    background-color: #22233a;
    border: 1px solid #2d2e42;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e0e0f0;
    font-size: 12px;
    selection-background-color: #6366f1;
}

QLineEdit:focus {
    border-color: #6366f1;
    background-color: #282840;
}

QLineEdit:hover {
    border-color: #3d3e56;
}

/* ═══════════════════════════════════════════
   COMBO BOXES
   ═══════════════════════════════════════════ */

QComboBox {
    background-color: #22233a;
    border: 1px solid #2d2e42;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e0e0f0;
    font-size: 12px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #3d3e56;
}

QComboBox:focus {
    border-color: #6366f1;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #2d2e42;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #282840;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #7070a0;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #1e1f34;
    border: 1px solid #2d2e42;
    border-radius: 4px;
    selection-background-color: #6366f1;
    color: #e0e0f0;
    padding: 4px;
}

/* ═══════════════════════════════════════════
   SPIN BOXES
   ═══════════════════════════════════════════ */

QDoubleSpinBox, QSpinBox {
    background-color: #22233a;
    border: 1px solid #2d2e42;
    border-radius: 6px;
    padding: 7px 10px;
    color: #e0e0f0;
    font-size: 12px;
}

QDoubleSpinBox:focus, QSpinBox:focus {
    border-color: #6366f1;
}

QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    background-color: #282840;
    border: none;
    width: 20px;
}

/* ═══════════════════════════════════════════
   CHECKBOXES
   ═══════════════════════════════════════════ */

QCheckBox {
    color: #b0b0c8;
    spacing: 8px;
    font-size: 12px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #3d3e56;
    border-radius: 4px;
    background-color: #22233a;
}

QCheckBox::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
}

QCheckBox::indicator:hover {
    border-color: #6366f1;
}

/* ═══════════════════════════════════════════
   TABS
   ═══════════════════════════════════════════ */

QTabWidget::pane {
    border: 1px solid #2d2e42;
    border-radius: 0 0 10px 10px;
    background-color: #1a1b2e;
    top: -1px;
}

QTabBar {
    background-color: transparent;
}

QTabBar::tab {
    background-color: #13141f;
    color: #6868a0;
    padding: 10px 24px;
    border: 1px solid #2d2e42;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 3px;
    font-size: 12px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #1a1b2e;
    color: #e0e0f0;
    border-bottom: 2px solid #6366f1;
}

QTabBar::tab:hover:!selected {
    background-color: #1a1b30;
    color: #a0a0c0;
}

/* ═══════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════ */

QPushButton#launchBtn {
    background-color: #6366f1;
    border: none;
    border-radius: 8px;
    padding: 12px 32px;
    color: white;
    font-weight: bold;
    font-size: 14px;
    min-width: 160px;
}

QPushButton#launchBtn:hover {
    background-color: #5558e6;
}

QPushButton#launchBtn:pressed {
    background-color: #4f46e5;
}

QPushButton#quitBtn {
    background-color: #2a2b40;
    border: 1px solid #3d3e56;
    border-radius: 8px;
    padding: 12px 24px;
    color: #a0a0b8;
    font-weight: bold;
    font-size: 13px;
    min-width: 100px;
}

QPushButton#quitBtn:hover {
    background-color: #34354a;
    border-color: #4d4e66;
}

/* ═══════════════════════════════════════════
   SEPARATOR
   ═══════════════════════════════════════════ */

QFrame#separator {
    background-color: #2d2e42;
    max-height: 1px;
    margin: 4px 0;
}

/* ═══════════════════════════════════════════
   STATUS BAR
   ═══════════════════════════════════════════ */

QStatusBar {
    background-color: #0e0f1a;
    color: #505070;
    font-size: 11px;
    padding: 4px 8px;
    border-top: 1px solid #1e1f30;
}

/* ═══════════════════════════════════════════
   SCROLL AREA
   ═══════════════════════════════════════════ */

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background-color: #13141f;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2d2e42;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3d3e56;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""