"""
Clean Windows-native dark theme.
Minimal overrides — lets the OS do most of the work.
"""

STYLESHEET = """
QMainWindow, QWidget#central {
    background-color: #1e1e1e;
}

QGroupBox {
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 10px;
    padding: 12px 8px 8px 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QLabel {
    color: #cccccc;
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 4px 6px;
    selection-background-color: #264f78;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #0078d4;
}

QCheckBox {
    color: #cccccc;
    spacing: 6px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
}

QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background-color: #1e1e1e;
    top: -1px;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #999999;
    padding: 8px 18px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 1px;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QTabBar::tab:hover:!selected {
    background-color: #252525;
}

QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 5px 14px;
}

QPushButton:hover {
    background-color: #353535;
    border-color: #4c4c4c;
}

QPushButton:pressed {
    background-color: #1a1a1a;
}

QPushButton#run {
    background-color: #0e639c;
    border-color: #1177bb;
    color: white;
    font-weight: bold;
    padding: 6px 18px;
    min-height: 28px;
}

QPushButton#run:hover {
    background-color: #1177bb;
}

QPushButton#run:pressed {
    background-color: #0e639c;
}

QPushButton#resetBtn {
    background-color: #3c2020;
    border-color: #5c3030;
    color: #e0a0a0;
    padding: 3px 10px;
}

QPushButton#resetBtn:hover {
    background-color: #4c2828;
}

QComboBox::drop-down {
    border-left: 1px solid #3c3c3c;
    width: 22px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #999999;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    selection-background-color: #264f78;
}
"""