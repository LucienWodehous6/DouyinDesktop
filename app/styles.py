"""现代暗色主题 v3 — 侧边栏导航 + 终端日志 + 主从视图"""

MODERN_THEME = """
/* ══════════════════════════════════════════
   全局
   ══════════════════════════════════════════ */
QMainWindow {
    background: #0d1117;
}
QDialog {
    background: #161b22;
}
QWidget {
    color: #c9d1d9;
    background: transparent;
    font-size: 13px;
}
QLabel {
    color: #c9d1d9;
    background: transparent;
}

/* ══════════════════════════════════════════
   侧边栏
   ══════════════════════════════════════════ */
QFrame#sidebar {
    background: #0d1117;
    border-right: 1px solid #21262d;
}
QLabel#sidebarLogo {
    color: #f0f6fc;
    font-size: 15px;
    font-weight: 700;
    padding: 6px 4px;
}
QLabel#sidebarVersion {
    color: #484f58;
    font-size: 11px;
}
QFrame#sidebarSep {
    background: #21262d;
    max-width: 1px;
}

/* 导航按钮 */
QPushButton#navBtn {
    background: transparent;
    color: #8b949e;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}
QPushButton#navBtn:hover {
    background: #161b22;
    color: #c9d1d9;
}
QPushButton#navBtn:checked {
    background: #1f2937;
    color: #ff6b81;
    font-weight: 600;
    border-left: 3px solid #ff6b81;
}

/* 主工作区 */
QStackedWidget#mainStack {
    background: #0d1117;
}

/* ══════════════════════════════════════════
   菜单栏
   ══════════════════════════════════════════ */
QMenuBar#appMenuBar {
    background: #0d1117;
    color: #8b949e;
    border-bottom: 1px solid #21262d;
    padding: 2px 8px;
    font-size: 13px;
}
QMenuBar#appMenuBar::item:selected {
    background: #1f2937;
    border-radius: 6px;
    color: #f0f6fc;
}
QMenu {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 32px 8px 14px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #1f2937;
    color: #ff6b81;
}
QMenu::separator {
    height: 1px;
    background: #21262d;
    margin: 4px 8px;
}

/* ══════════════════════════════════════════
   状态栏
   ══════════════════════════════════════════ */
QStatusBar#appStatusBar {
    background: #0d1117;
    color: #8b949e;
    border-top: 1px solid #21262d;
    font-size: 12px;
    padding: 2px;
}
QLabel#statusText {
    color: #8b949e;
    font-size: 12px;
    padding: 0 10px;
}
QLabel#statusInfo {
    color: #484f58;
    font-size: 11px;
    padding: 0 10px;
}

/* ══════════════════════════════════════════
   GroupBox 卡片
   ══════════════════════════════════════════ */
QGroupBox {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    margin-top: 20px;
    padding: 24px 16px 14px 16px;
    font-size: 12px;
    font-weight: 600;
    color: #ff6b81;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
}

/* ══════════════════════════════════════════
   输入框
   ══════════════════════════════════════════ */
QLineEdit {
    background: #0d1117;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: rgba(255,107,129,0.3);
}
QLineEdit:focus {
    border: 1px solid #ff6b81;
    background: #161b22;
}
QLineEdit::placeholder {
    color: #484f58;
}

/* SpinBox */
QSpinBox {
    background: #0d1117;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    min-height: 36px;
}
QSpinBox:focus {
    border: 1px solid #ff6b81;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #21262d;
    border-bottom: 1px solid #21262d;
    border-top-right-radius: 7px;
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 26px;
    border-left: 1px solid #21262d;
    border-bottom-right-radius: 7px;
}
QSpinBox::up-arrow {
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #8b949e;
}
QSpinBox::down-arrow {
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #8b949e;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #1f2937;
}

/* ComboBox */
QComboBox {
    background: #0d1117;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    min-height: 36px;
}
QComboBox:hover {
    border: 1px solid #484f58;
}
QComboBox:focus {
    border: 1px solid #ff6b81;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #21262d;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}
QComboBox::down-arrow {
    image: none;
    width: 0; height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background: #161b22;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    selection-background-color: rgba(255,107,129,0.2);
}
QComboBox QAbstractItemView::item {
    padding: 8px 14px;
    min-height: 30px;
}
QComboBox QAbstractItemView::item:selected {
    background: rgba(255,107,129,0.2);
    color: #ff6b81;
}

/* ══════════════════════════════════════════
   CheckBox
   ══════════════════════════════════════════ */
QCheckBox {
    color: #8b949e;
    spacing: 10px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #30363d;
    border-radius: 4px;
    background: #0d1117;
}
QCheckBox::indicator:hover {
    border: 2px solid #484f58;
}
QCheckBox::indicator:checked {
    background: #2ed573;
    border: 2px solid #2ed573;
    image: none;
}
QCheckBox::indicator:checked:hover {
    background: #3be080;
    border: 2px solid #3be080;
}
QCheckBox::indicator:disabled {
    border: 2px solid #21262d;
    background: #161b22;
}

/* ══════════════════════════════════════════
   按钮
   ══════════════════════════════════════════ */
QPushButton {
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 9px 22px;
    font-size: 13px;
}
QPushButton:hover {
    background: #30363d;
    border: 1px solid #484f58;
}
QPushButton:pressed {
    background: #161b22;
}

/* 主操作按钮 */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f85149, stop:1 #ff6b81);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 12px 36px;
    font-size: 15px;
    font-weight: 700;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff6b81, stop:1 #ff8a9e);
}
QPushButton#primaryBtn:pressed {
    background: #d63850;
}
QPushButton#primaryBtn:disabled {
    background: #21262d;
    color: #484f58;
}

/* 危险按钮 */
QPushButton#dangerBtn {
    background: rgba(248, 81, 73, 0.12);
    color: #f85149;
    border: 1px solid rgba(248, 81, 73, 0.25);
    border-radius: 10px;
    padding: 12px 36px;
    font-size: 15px;
    font-weight: 700;
}
QPushButton#dangerBtn:hover {
    background: rgba(248, 81, 73, 0.22);
}

/* 小型按钮 */
QPushButton#smallBtn {
    padding: 6px 14px;
    font-size: 12px;
    border-radius: 6px;
    min-width: 28px;
}

/* 标签按钮 (chips) */
QPushButton#tagBtn {
    background: #1f2937;
    color: #ff6b81;
    border: 1px solid rgba(255,107,129,0.3);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
QPushButton#tagBtn:hover {
    background: rgba(255,107,129,0.12);
    border: 1px solid rgba(255,107,129,0.5);
}

/* ==========================================
   标签
   ========================================== */
QLabel#pageTitle {
    color: #f0f6fc;
    font-size: 20px;
    font-weight: 700;
}
QLabel#sectionLabel {
    color: #8b949e;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 4px;
}
QLabel#hintLabel {
    color: #484f58;
    font-size: 12px;
}

/* ==========================================
   日志 / 终端
   ========================================== */
QPlainTextEdit#logView {
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #21262d;
    border-radius: 8px;
    font-family: "JetBrains Mono", "SF Mono", "Menlo", monospace;
    font-size: 12px;
    padding: 12px;
    selection-background-color: rgba(255,107,129,0.25);
}

/* ==========================================
   JSON 查看器
   ========================================== */
QPlainTextEdit#jsonView {
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #21262d;
    border-radius: 8px;
    font-family: "JetBrains Mono", "SF Mono", "Menlo", monospace;
    font-size: 12px;
    padding: 14px;
    selection-background-color: rgba(255,107,129,0.25);
}

/* ==========================================
   QTextEdit 暗色
   ========================================== */
QTextEdit {
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    selection-background-color: rgba(255,107,129,0.25);
}
QTextEdit:focus {
    border: 1px solid #ff6b81;
    background: #161b22;
}

/* ==========================================
   表格 / 树
   ========================================== */
QTreeWidget {
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #21262d;
    border-radius: 8px;
    font-size: 13px;
    outline: none;
    alternate-background-color: rgba(255,255,255,0.01);
}
QTreeWidget::item {
    padding: 5px 6px;
    min-height: 26px;
}
QTreeWidget::item:selected {
    background: #1f2937;
    color: #ff6b81;
}
QTreeWidget::item:hover:!selected {
    background: rgba(255,255,255,0.02);
}
QHeaderView::section {
    background: #0d1117;
    color: #8b949e;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #21262d;
    font-size: 11px;
    font-weight: 700;
}

/* ==========================================
   进度条
   ========================================== */
QProgressBar {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
    font-size: 0;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f85149, stop:1 #ff6b81);
    border-radius: 5px;
}

/* ==========================================
   滚动条
   ========================================== */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 8px; }
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ==========================================
   分隔条
   ========================================== */
QSplitter::handle {
    background: #21262d;
    margin: 2px 0;
}

/* ==========================================
   对话框按钮
   ========================================== */
QDialogButtonBox QPushButton {
    min-width: 80px;
    padding: 8px 18px;
}

/* ==========================================
   分隔线
   ========================================== */
QFrame#sectionDivider {
    background: #21262d;
    max-height: 1px;
}
"""
