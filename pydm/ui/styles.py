"""Modern dark theme QSS styles for PyDM."""

# Color palette
COLORS = {
    "bg_dark": "#0d1117",
    "bg_primary": "#161b22",
    "bg_secondary": "#21262d",
    "bg_tertiary": "#30363d",
    "bg_hover": "#363b44",
    "bg_selected": "#1f6feb33",
    "border": "#30363d",
    "border_light": "#484f58",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#6e7681",
    "accent": "#58a6ff",
    "accent_dark": "#1f6feb",
    "accent_hover": "#79c0ff",
    "success": "#3fb950",
    "warning": "#d29922",
    "error": "#f85149",
    "danger": "#da3633",
    "progress_gradient_start": "#58a6ff",
    "progress_gradient_end": "#3fb950",
    "scrollbar_bg": "#161b22",
    "scrollbar_handle": "#30363d",
    "scrollbar_hover": "#484f58",
}


MAIN_STYLESHEET = f"""
/* ========================================
   GLOBAL
   ======================================== */
QMainWindow {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["text_primary"]};
}}

QWidget {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["text_primary"]};
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* ========================================
   MENU BAR
   ======================================== */
QMenuBar {{
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_primary"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 6px;
    margin: 2px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS["bg_tertiary"]};
}}

QMenu {{
    background-color: {COLORS["bg_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 32px 8px 16px;
    border-radius: 4px;
    margin: 2px;
}}

QMenu::item:selected {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["accent"]};
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 4px 8px;
}}

/* ========================================
   TOOLBAR
   ======================================== */
QToolBar {{
    background-color: {COLORS["bg_primary"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 6px 12px;
    spacing: 8px;
}}

QToolBar QToolButton {{
    background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    font-size: 13px;
    min-width: 70px;
}}

QToolBar QToolButton:hover {{
    background-color: {COLORS["bg_tertiary"]};
    border-color: {COLORS["border_light"]};
    color: {COLORS["accent"]};
}}

QToolBar QToolButton:pressed {{
    background-color: {COLORS["bg_hover"]};
}}

QToolBar QToolButton:disabled {{
    color: {COLORS["text_muted"]};
    background-color: {COLORS["bg_primary"]};
    border-color: {COLORS["border"]};
}}

QToolBar::separator {{
    width: 1px;
    background: {COLORS["border"]};
    margin: 4px 8px;
}}

/* ========================================
   TABLE / DOWNLOAD LIST
   ======================================== */
QTableWidget {{
    background-color: {COLORS["bg_primary"]};
    alternate-background-color: {COLORS["bg_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    gridline-color: {COLORS["border"]};
    selection-background-color: {COLORS["bg_selected"]};
    selection-color: {COLORS["text_primary"]};
    outline: none;
}}

QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {COLORS["border"]};
}}

QTableWidget::item:selected {{
    background-color: {COLORS["bg_selected"]};
}}

QHeaderView::section {{
    background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_secondary"]};
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid {COLORS["border"]};
    border-right: 1px solid {COLORS["border"]};
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QHeaderView::section:hover {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
}}

QHeaderView::section:last {{
    border-right: none;
}}

/* ========================================
   PROGRESS BAR
   ======================================== */
QProgressBar {{
    background-color: {COLORS["bg_tertiary"]};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: {COLORS["text_primary"]};
    font-size: 11px;
    font-weight: 600;
    min-height: 18px;
    max-height: 18px;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["progress_gradient_start"]},
        stop:1 {COLORS["progress_gradient_end"]}
    );
    border-radius: 6px;
}}

/* ========================================
   BUTTONS
   ======================================== */
QPushButton {{
    background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {COLORS["bg_tertiary"]};
    border-color: {COLORS["border_light"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["bg_hover"]};
}}

QPushButton:disabled {{
    color: {COLORS["text_muted"]};
    background-color: {COLORS["bg_primary"]};
}}

QPushButton#primaryButton {{
    background-color: {COLORS["accent_dark"]};
    color: #ffffff;
    border: none;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: {COLORS["accent"]};
}}

QPushButton#primaryButton:pressed {{
    background-color: {COLORS["accent_dark"]};
}}

QPushButton#dangerButton {{
    background-color: {COLORS["danger"]};
    color: #ffffff;
    border: none;
}}

QPushButton#dangerButton:hover {{
    background-color: {COLORS["error"]};
}}

/* ========================================
   INPUT FIELDS
   ======================================== */
QLineEdit {{
    background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: {COLORS["accent_dark"]};
}}

QLineEdit:focus {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_primary"]};
}}

QLineEdit::placeholder {{
    color: {COLORS["text_muted"]};
}}

/* ========================================
   SPIN BOX
   ======================================== */
QSpinBox {{
    background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}

QSpinBox:focus {{
    border-color: {COLORS["accent"]};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {COLORS["bg_tertiary"]};
    border: none;
    width: 20px;
    border-radius: 4px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS["bg_hover"]};
}}

/* ========================================
   LABELS
   ======================================== */
QLabel {{
    color: {COLORS["text_primary"]};
    background: transparent;
}}

QLabel#sectionLabel {{
    color: {COLORS["text_secondary"]};
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

QLabel#statusLabel {{
    color: {COLORS["text_secondary"]};
    font-size: 12px;
    padding: 4px 8px;
}}

/* ========================================
   STATUS BAR
   ======================================== */
QStatusBar {{
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_secondary"]};
    border-top: 1px solid {COLORS["border"]};
    font-size: 12px;
    padding: 4px;
}}

QStatusBar::item {{
    border: none;
}}

/* ========================================
   SCROLLBAR
   ======================================== */
QScrollBar:vertical {{
    background-color: {COLORS["scrollbar_bg"]};
    width: 10px;
    border: none;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS["scrollbar_handle"]};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS["scrollbar_hover"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLORS["scrollbar_bg"]};
    height: 10px;
    border: none;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS["scrollbar_handle"]};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS["scrollbar_hover"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ========================================
   DIALOG
   ======================================== */
QDialog {{
    background-color: {COLORS["bg_dark"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
}}

/* ========================================
   GROUP BOX
   ======================================== */
QGroupBox {{
    background-color: {COLORS["bg_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    margin-top: 16px;
    padding: 20px 16px 16px 16px;
    font-weight: 600;
    color: {COLORS["text_secondary"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: {COLORS["bg_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    color: {COLORS["accent"]};
    left: 12px;
}}

/* ========================================
   TOOLTIP
   ======================================== */
QToolTip {{
    background-color: {COLORS["bg_secondary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ========================================
   SYSTEM TRAY MENU
   ======================================== */
QMenu#trayMenu {{
    background-color: {COLORS["bg_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
}}
"""


# Status-specific colors for download states
STATUS_COLORS = {
    "active": COLORS["accent"],
    "waiting": COLORS["warning"],
    "paused": COLORS["text_muted"],
    "error": COLORS["error"],
    "complete": COLORS["success"],
    "removed": COLORS["text_muted"],
}

# Status display text
STATUS_TEXT = {
    "active": "⬇ Downloading",
    "waiting": "⏳ Waiting",
    "paused": "⏸ Paused",
    "error": "❌ Error",
    "complete": "✅ Completed",
    "removed": "🗑 Removed",
}
