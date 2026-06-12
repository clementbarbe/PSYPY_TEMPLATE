"""
Minimal sober stylesheet.
"""

STYLESHEET = """
* {
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 12px;
}

QMainWindow {
    background-color: #f0f0f0;
}

QGroupBox {
    font-weight: bold;
    font-size: 12px;
    border: 1px solid #b0b0b0;
    border-radius: 4px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
    background-color: #fafafa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    background-color: #fafafa;
}

QLineEdit, QSpinBox, QComboBox {
    padding: 4px 8px;
    border: 1px solid #b0b0b0;
    border-radius: 3px;
    background-color: white;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #4a90d9;
}

QPushButton {
    padding: 6px 16px;
    border: 1px solid #a0a0a0;
    border-radius: 3px;
    background-color: #e8e8e8;
}

QPushButton:hover {
    background-color: #d8d8d8;
    border-color: #808080;
}

QPushButton:pressed {
    background-color: #c8c8c8;
}

QPushButton#designBtn {
    min-height: 36px;
    font-weight: bold;
    font-size: 12px;
    background-color: #e0e8f0;
    border-color: #80a0c0;
}

QPushButton#designBtn:hover {
    background-color: #c8d8e8;
}

QPushButton#trainBtn {
    min-height: 32px;
    background-color: #e8f0e0;
    border-color: #80a080;
}

QPushButton#trainBtn:hover {
    background-color: #d8e8d0;
}

QPushButton#resetBtn {
    font-size: 11px;
    padding: 3px 10px;
    background-color: #f0e0e0;
    border-color: #c0a0a0;
}

QPushButton#resetBtn:hover {
    background-color: #e8d0d0;
}

QTabWidget::pane {
    border: 1px solid #b0b0b0;
    border-radius: 0 0 4px 4px;
    background-color: #fafafa;
    top: -1px;
}

QTabBar::tab {
    padding: 8px 20px;
    border: 1px solid #b0b0b0;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background-color: #e8e8e8;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #fafafa;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background-color: #e0e0e0;
}

QCheckBox {
    spacing: 6px;
}

QLabel#infoLabel {
    color: #606060;
    font-style: italic;
    font-size: 11px;
}
"""