#!/usr/bin/env python3
"""
PySSH Manager - SecureCRT 스타일 SSH 클라이언트
의존성: pip install PyQt5 paramiko pyte
"""

import sys
import re
import json
import os
import threading
import time
import socket
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QTabWidget, QTabBar,
    QTextEdit, QLineEdit, QLabel, QPushButton, QDialog, QFormLayout,
    QSpinBox, QComboBox, QFileDialog, QMessageBox, QMenu, QAction,
    QToolBar, QStatusBar, QProgressDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QFrame, QCheckBox, QGroupBox,
    QDialogButtonBox, QAbstractItemView, QStyle, QScrollArea
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QMimeData, QEvent
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QTextCursor, QKeySequence,
    QIcon, QTextCharFormat, QBrush
)

import paramiko
import pyte

# ── 설정 파일 경로 ──────────────────────────────────────────
CONFIG_DIR   = Path.home() / ".pyssh_manager"
SESSION_FILE = CONFIG_DIR / "sessions.json"
PREFS_FILE   = CONFIG_DIR / "prefs.json"
CONFIG_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  테마 정의
# ══════════════════════════════════════════════════════════════
THEMES = {
    "Default Dark": {
        "bg_color": "#0d1117", "fg_color": "#c9d1d9", "cursor_color": "#5a9fd4",
        "sel_bg": "#264f78", "sel_fg": "#ffffff",
    },
    "Monokai": {
        "bg_color": "#272822", "fg_color": "#f8f8f2", "cursor_color": "#f92672",
        "sel_bg": "#49483e", "sel_fg": "#f8f8f2",
    },
    "Solarized Dark": {
        "bg_color": "#002b36", "fg_color": "#839496", "cursor_color": "#268bd2",
        "sel_bg": "#073642", "sel_fg": "#93a1a1",
    },
    "Dracula": {
        "bg_color": "#282a36", "fg_color": "#f8f8f2", "cursor_color": "#bd93f9",
        "sel_bg": "#44475a", "sel_fg": "#f8f8f2",
    },
    "Tomorrow Night": {
        "bg_color": "#1d1f21", "fg_color": "#c5c8c6", "cursor_color": "#81a2be",
        "sel_bg": "#282a2e", "sel_fg": "#e0e0e0",
    },
    "Green Terminal": {
        "bg_color": "#001100", "fg_color": "#00ff41", "cursor_color": "#00cc33",
        "sel_bg": "#003300", "sel_fg": "#00ff41",
    },
    "Amber Terminal": {
        "bg_color": "#110800", "fg_color": "#ffb000", "cursor_color": "#ffd050",
        "sel_bg": "#2a1800", "sel_fg": "#ffb000",
    },
    "Ocean Dark": {
        "bg_color": "#0a1628", "fg_color": "#a8c8e8", "cursor_color": "#4aa8d8",
        "sel_bg": "#1a3050", "sel_fg": "#d0e8f8",
    },
    "Nord": {
        "bg_color": "#2e3440", "fg_color": "#d8dee9", "cursor_color": "#88c0d0",
        "sel_bg": "#3b4252", "sel_fg": "#eceff4",
    },
    "Gruvbox Dark": {
        "bg_color": "#282828", "fg_color": "#ebdbb2", "cursor_color": "#fabd2f",
        "sel_bg": "#3c3836", "sel_fg": "#ebdbb2",
    },
    "Light": {
        "bg_color": "#fafafa", "fg_color": "#1a1a1a", "cursor_color": "#0066cc",
        "sel_bg": "#cce5ff", "sel_fg": "#003366",
    },
    "Solarized Light": {
        "bg_color": "#fdf6e3", "fg_color": "#657b83", "cursor_color": "#268bd2",
        "sel_bg": "#eee8d5", "sel_fg": "#586e75",
    },
}

# ── 기본 환경 설정 ──────────────────────────────────────────
DEFAULT_PREFS = {
    "font_family":        "Consolas",
    "font_size":          12,
    "theme":              "Default Dark",
    "bg_color":           "#0d1117",
    "fg_color":           "#c9d1d9",
    "cursor_color":       "#5a9fd4",
    "charset":            "UTF-8",
    "history_size":       500,
    "show_local_input":   True ,   # 보기 메뉴로 켜고 끄기
    "keepalive_enabled":  False,
    "keepalive_interval": 60,      # 초
}

def load_prefs() -> dict:
    if PREFS_FILE.exists():
        try:
            data = json.loads(PREFS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_PREFS, **data}
        except Exception:
            pass
    return dict(DEFAULT_PREFS)

def save_prefs(prefs: dict):
    PREFS_FILE.write_text(
        json.dumps(prefs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

PREFS = load_prefs()


# ══════════════════════════════════════════════════════════════
#  다크 테마 팔레트 (UI 프레임)
# ══════════════════════════════════════════════════════════════
def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,          QColor(30, 33, 40))
    p.setColor(QPalette.WindowText,      QColor(200, 200, 200))
    p.setColor(QPalette.Base,            QColor(22, 24, 29))
    p.setColor(QPalette.AlternateBase,   QColor(35, 38, 47))
    p.setColor(QPalette.ToolTipBase,     QColor(50, 54, 65))
    p.setColor(QPalette.ToolTipText,     QColor(200, 200, 200))
    p.setColor(QPalette.Text,            QColor(200, 200, 200))
    p.setColor(QPalette.Button,          QColor(45, 48, 58))
    p.setColor(QPalette.ButtonText,      QColor(200, 200, 200))
    p.setColor(QPalette.BrightText,      Qt.red)
    p.setColor(QPalette.Link,            QColor(90, 159, 212))
    p.setColor(QPalette.Highlight,       QColor(60, 100, 160))
    p.setColor(QPalette.HighlightedText, QColor(240, 240, 240))
    p.setColor(QPalette.Disabled, QPalette.Text,       QColor(100, 100, 100))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(100, 100, 100))
    app.setPalette(p)

    app.setStyleSheet("""
        QMainWindow, QDialog { background: #1a1d21; }
        QMenuBar { background: #252830; color: #bbb; border-bottom: 1px solid #333; }
        QMenuBar::item:selected { background: #3a3f4a; color: #fff; }
        QMenu { background: #252830; color: #bbb; border: 1px solid #444; }
        QMenu::item:selected { background: #3a4060; color: #fff; }
        QMenu::item:disabled { color: #555; }
        QToolBar { background: #252830; border-bottom: 1px solid #333; spacing: 2px; padding: 2px; }
        QToolButton {
            background: #333842; border: 1px solid #444; color: #bbb;
            border-radius: 3px; padding: 3px 8px; font-size: 12px;
        }
        QToolButton:hover { background: #4a5060; color: #fff; border-color: #666; }
        QToolButton:pressed { background: #3a4555; }
        QTreeWidget { background: #1e2128; color: #aaa; border: none; font-size: 12px; }
        QTreeWidget::item:hover { background: #2d3240; color: #ddd; }
        QTreeWidget::item:selected { background: #2d3240; color: #7ec8e3; }
        QTreeWidget::branch { background: #1e2128; }
        QTabWidget::pane { border: none; background: #1a1d21; }
        QTabBar::tab {
            background: #1e2128; color: #888; border: none;
            border-right: 1px solid #333; border-top: 2px solid transparent;
            padding: 6px 14px; font-size: 12px;
        }
        QTabBar::tab:selected { background: #1a1d21; color: #7ec8e3; border-top-color: #5a9fd4; }
        QTabBar::tab:hover { background: #252830; color: #ccc; }
        QLineEdit {
            background: #1e2128; color: #ddd; border: 1px solid #444;
            border-radius: 3px; padding: 4px 8px; font-size: 12px;
        }
        QLineEdit:focus { border-color: #5a9fd4; }
        QPushButton {
            background: #333842; border: 1px solid #444; color: #bbb;
            border-radius: 3px; padding: 5px 14px; font-size: 12px;
        }
        QPushButton:hover { background: #4a5060; color: #fff; border-color: #666; }
        QPushButton:pressed { background: #3a4555; }
        QSplitter::handle { background: #333; width: 1px; }
        QStatusBar { background: #252830; color: #666; border-top: 1px solid #333; font-size: 11px; }
        QHeaderView::section {
            background: #252830; color: #888; border: none;
            border-right: 1px solid #333; border-bottom: 1px solid #333;
            padding: 4px 8px; font-size: 11px;
        }
        QTableWidget {
            background: #1a1d21; color: #bbb; border: none;
            gridline-color: #2a2d35; font-size: 12px;
        }
        QTableWidget::item:selected { background: #2d4060; color: #ddd; }
        QScrollBar:vertical { background: #1a1d21; width: 8px; border: none; }
        QScrollBar::handle:vertical { background: #444; border-radius: 4px; min-height: 20px; }
        QScrollBar::handle:vertical:hover { background: #666; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { background: #1a1d21; height: 8px; border: none; }
        QScrollBar::handle:horizontal { background: #444; border-radius: 4px; }
        QGroupBox {
            color: #888; border: 1px solid #333; border-radius: 4px;
            margin-top: 8px; padding-top: 8px; font-size: 11px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #888; }
        QComboBox {
            background: #1e2128; color: #ddd; border: 1px solid #444;
            border-radius: 3px; padding: 4px 8px; font-size: 12px;
        }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #252830; color: #ddd; border: 1px solid #444; }
        QSpinBox {
            background: #1e2128; color: #ddd; border: 1px solid #444;
            border-radius: 3px; padding: 4px; font-size: 12px;
        }
        QCheckBox { color: #bbb; font-size: 12px; }
        QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #555; border-radius: 2px; background: #1e2128; }
        QCheckBox::indicator:checked { background: #5a9fd4; border-color: #5a9fd4; }
        QLabel { color: #bbb; font-size: 12px; }
        QProgressDialog { background: #252830; }
    """)


# ══════════════════════════════════════════════════════════════
#  세션 데이터 모델
# ══════════════════════════════════════════════════════════════
class SessionManager:
    def __init__(self):
        self.sessions = self._load()

    def _load(self):
        if SESSION_FILE.exists():
            try:
                return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "groups": [
                {
                    "name": "Production",
                    "sessions": [
                        {"name": "web-server-01", "host": "192.168.1.10", "port": 22,
                         "username": "admin", "auth": "password", "key_file": ""},
                    ]
                },
                {
                    "name": "Development",
                    "sessions": [
                        {"name": "dev-db-01", "host": "10.0.0.5", "port": 22,
                         "username": "dev", "auth": "password", "key_file": ""},
                    ]
                }
            ]
        }

    def save(self):
        SESSION_FILE.write_text(
            json.dumps(self.sessions, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add_session(self, group_name: str, session: dict):
        for g in self.sessions["groups"]:
            if g["name"] == group_name:
                g["sessions"].append(session)
                self.save()
                return
        self.sessions["groups"].append({"name": group_name, "sessions": [session]})
        self.save()

    def delete_session(self, group_name: str, session_name: str):
        for g in self.sessions["groups"]:
            if g["name"] == group_name:
                g["sessions"] = [s for s in g["sessions"] if s["name"] != session_name]
        self.save()

    def get_groups(self):
        return self.sessions.get("groups", [])


# ══════════════════════════════════════════════════════════════
#  SSH 워커 스레드  (Keep-Alive 포함)
# ══════════════════════════════════════════════════════════════
class SSHWorker(QThread):
    output_received = pyqtSignal(str)
    connected       = pyqtSignal()
    disconnected    = pyqtSignal(str)
    error_occurred  = pyqtSignal(str)

    def __init__(self, session_info: dict):
        super().__init__()
        self.info        = session_info
        self.client      = None
        self.channel     = None
        self._running    = False
        self._cmd_queue  = []
        self._lock       = threading.Lock()
        self._ka_timer   = None   # keep-alive
        self.cols        = 80
        self.rows        = 24

    def resize_pty(self, cols, rows):
        """동적 PTY 사이즈 변경 요청"""
        self.cols = cols
        self.rows = rows
        if self.channel and not self.channel.closed:
            try:
                self.channel.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def run(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            kwargs = dict(
                hostname=self.info["host"],
                port=self.info["port"],
                username=self.info["username"],
                timeout=15,
                allow_agent=False,
                look_for_keys=False,
            )
            if self.info.get("auth") == "key" and self.info.get("key_file"):
                kwargs["key_filename"] = self.info["key_file"]
            else:
                kwargs["password"] = self.info.get("password", "")

            # ── Paramiko Transport 레벨 Keep-Alive ──
            if PREFS.get("keepalive_enabled", False):
                interval = int(PREFS.get("keepalive_interval", 60))
                self.client.connect(**kwargs)
                transport = self.client.get_transport()
                if transport:
                    transport.set_keepalive(interval)
            else:
                self.client.connect(**kwargs)

            # 창 크기에 맞춘 터미널 쉘 요청
            self.channel = self.client.invoke_shell(
                term="xterm-256color", width=self.cols, height=self.rows
            )
            self.channel.settimeout(0.1)
            self._running = True
            self.connected.emit()

            while self._running:
                with self._lock:
                    cmds = self._cmd_queue[:]
                    self._cmd_queue.clear()
                for cmd in cmds:
                    if isinstance(cmd, bytes):
                        self.channel.send(cmd)
                    else:
                        # 제어 문자(\x00~\x1f, \x7f)가 포함된 경우 latin-1로 바이트 보존
                        # 일반 텍스트는 설정된 charset으로 인코딩
                        try:
                            raw = cmd.encode("latin-1")  # 제어문자/ASCII 1:1 보존
                            self.channel.send(raw)
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            charset = PREFS.get("charset", "UTF-8")
                            try:
                                self.channel.send(cmd.encode(charset, errors="replace"))
                            except (LookupError, UnicodeEncodeError):
                                self.channel.send(cmd.encode("utf-8", errors="replace"))

                try:
                    data = self.channel.recv(4096)
                    if data:
                        charset = PREFS.get("charset", "UTF-8")
                        try:
                            decoded = data.decode(charset, errors="replace")
                        except (LookupError, UnicodeDecodeError):
                            decoded = data.decode("utf-8", errors="replace")
                        self.output_received.emit(decoded)
                except socket.timeout:
                    pass
                except Exception:
                    break

                if self.channel.closed:
                    break

        except paramiko.AuthenticationException:
            self.error_occurred.emit("인증 실패: 아이디/비밀번호 또는 키를 확인하세요.")
        except paramiko.SSHException as e:
            self.error_occurred.emit(f"SSH 오류: {e}")
        except socket.timeout:
            self.error_occurred.emit("접속 시간 초과")
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._running = False
            self.disconnected.emit("연결 종료")

    def send(self, data):
        """문자열 또는 bytes 전송"""
        with self._lock:
            self._cmd_queue.append(data)

    def stop(self):
        self._running = False
        if self.channel:
            try: self.channel.close()
            except: pass
        if self.client:
            try: self.client.close()
            except: pass


# ══════════════════════════════════════════════════════════════
#  TerminalScreen
#  - 일반 모드: QTextEdit append 방식 (스크롤 지원)
#  - vi 모드  : pyte 버퍼를 paintEvent 로 직접 그림
# ══════════════════════════════════════════════════════════════
class TerminalScreen(QWidget):
    send_data = pyqtSignal(str)
    resized   = pyqtSignal(int, int)  # cols, rows 창 크기 변경 시그널

    # ESC > / ESC = 같은 단일 문자 시퀀스가 plain 모드에서 '>'만 남는 문제를 막기 위해 포함
    _ANSI = re.compile(r'\x1b(?:\[[0-9;?>=!]*[A-Za-z@`]|[@-_]|[=><])')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setMouseTracking(True)

        # ── 폰트 / 색상 ─────────────────────────────────────
        self._setup_font()

        # ── 일반 모드 텍스트 (QTextEdit 대신 문자열 리스트) ─
        self._plain_lines = ['']      # 일반 쉘 출력 행 목록
        self._scroll_offset = 0       # 상단부터 몇 행 스크롤됐는지
        self._plain_col = 0           # 현재 줄 커서 컬럼(일반 모드)

        # ── 선택(복사용) ────────────────────────────────────
        self._sel_active = False      # 선택 범위가 존재함(고정 포함)
        self._sel_dragging = False    # 드래그로 선택 범위 갱신 중
        self._sel_mode = 'linear'     # 'linear' | 'rect' (Ctrl+드래그 컬럼 선택)
        self._sel_start = None  # (line_idx, col)
        self._sel_end = None    # (line_idx, col)

        # ── pyte 터미널 에뮬레이터 ──────────────────────────
        self._pty_cols = 80
        self._pty_rows = 24
        self._pyte_screen = pyte.Screen(self._pty_cols, self._pty_rows)
        self._pyte_stream = pyte.ByteStream(self._pyte_screen)

        # ── 모드 ────────────────────────────────────────────
        self._vi_mode    = False   # True: pyte 렌더, False: plain 렌더
        self._appkeypad  = False   # vi ?1h → True, 화살표 ESC O 시리즈

        # ── 히스토리 ────────────────────────────────────────
        self._history    = []
        self._hist_idx   = -1
        self._saved_input = ''
        self._local_buf  = ''
        self.local_input_label = None

        # ── 커서 깜박임 ─────────────────────────────────────
        self._cursor_on  = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(500)

    def _setup_font(self):
        fn  = PREFS.get('font_family', 'Consolas')
        fs  = PREFS.get('font_size', 12)
        self._font = QFont(fn, fs)
        self._font.setStyleHint(QFont.Monospace)
        from PyQt5.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        self._cw      = fm.averageCharWidth()
        self._ch      = fm.height()
        self._descent = fm.descent()
        self._fg  = QColor(PREFS.get('fg_color',     '#c9d1d9'))
        self._bg  = QColor(PREFS.get('bg_color',     '#0d1117'))
        self._cc  = QColor(PREFS.get('cursor_color', '#5a9fd4'))

    def _apply_prefs(self):
        self._setup_font()
        self.update()

    def _blink(self):
        self._cursor_on = not self._cursor_on
        self.update()

    # 창 크기 변경 시 터미널 크기 계산하여 서버에 전송
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_cw') and self._cw > 0 and self._ch > 0:
            cols = max(1, int(self.width() // self._cw))
            rows = max(1, int(self.height() // self._ch))
            
            if cols != self._pty_cols or rows != self._pty_rows:
                self._pty_cols = cols
                self._pty_rows = rows
                try:
                    self._pyte_screen.resize(lines=rows, columns=cols)
                except Exception:
                    pass
                self.resized.emit(cols, rows)

    # 클릭 시 포커스 획득 (커서 및 키보드 입력 활성화 보장)
    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.RightButton:
            # 우클릭: 컨텍스트 메뉴 대신 바로 붙여넣기
            self._paste()
            return
        if not self._vi_mode and event.button() == Qt.LeftButton:
            self._sel_active = True
            self._sel_dragging = True
            self._sel_mode = 'rect' if (event.modifiers() & Qt.ControlModifier) else 'linear'
            self._sel_start = self._plain_pos_from_point(event.x(), event.y())
            self._sel_end = self._sel_start
            self.update()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._vi_mode and self._sel_dragging and (event.buttons() & Qt.LeftButton):
            self._sel_end = self._plain_pos_from_point(event.x(), event.y())
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self._vi_mode and event.button() == Qt.LeftButton and self._sel_active:
            self._sel_end = self._plain_pos_from_point(event.x(), event.y())
            self._sel_dragging = False
            # 좌클릭 드래그 선택 완료 시 자동 복사
            sel = self._get_selected_text_plain()
            if sel:
                QApplication.clipboard().setText(sel)
            self.update()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self._vi_mode and event.button() == Qt.LeftButton:
            pos = self._plain_pos_from_point(event.x(), event.y())
            if pos:
                li, col = pos
                line = self._plain_lines[li] if 0 <= li < len(self._plain_lines) else ''
                if line:
                    col = max(0, min(col, len(line)))
                    # 단어 경계(공백 기준)로 확장
                    l = col
                    while l > 0 and not line[l-1].isspace():
                        l -= 1
                    r = col
                    while r < len(line) and not line[r].isspace():
                        r += 1
                    self._sel_active = True
                    self._sel_start = (li, l)
                    self._sel_end = (li, r)
                    self.update()
                    return
        super().mouseDoubleClickEvent(event)

    def focusNextPrevChild(self, next: bool) -> bool:
        # Tab / Shift+Tab 기본 동작(포커스 이동)을 막아야 서버로 Tab을 보낼 수 있다.
        # 여기서 처리했다고 알려주면(Qt가) 포커스를 다른 위젯으로 넘기지 않는다.
        self.setFocus()
        return True

    def event(self, event):
        # Qt는 Tab/Shift+Tab을 keyPressEvent까지 보내지 않고,
        # focusNextPrevChild로 포커스 이동을 시도하면서 소비해버릴 수 있다.
        # event 단계에서 먼저 가로채서 서버로 Tab을 확실히 전송한다.
        if event.type() == QEvent.KeyPress:
            k = event.key()
            if k in (Qt.Key_Tab, Qt.Key_Backtab):
                self.send_data.emit('\t')
                return True
        return super().event(event)

    # ── 화면 그리기 ──────────────────────────────────────────
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg)
        p.setFont(self._font)
        if self._vi_mode:
            self._paint_vi(p)
        else:
            self._paint_plain(p)
        p.end()

    def _paint_vi(self, p):
        """pyte 버퍼를 셀 단위로 그린다."""
        ps = self._pyte_screen
        cw, ch = self._cw, self._ch
        for y in range(ps.lines):
            row = ps.buffer[y]
            for x in range(ps.columns):
                cell = row[x] if x in row else None
                if not cell: continue
                ch_char = cell.data
                if not ch_char or ch_char == '\x00': continue
                px, py = x * cw, y * ch
                if cell.reverse:
                    p.fillRect(int(px), int(py), int(cw), int(ch), self._fg)
                    p.setPen(self._bg)
                else:
                    p.setPen(self._fg)
                p.drawText(int(px), int(py + ch - self._descent), ch_char)
        # 커서
        if self._cursor_on and self.hasFocus():
            cy, cx = ps.cursor.y, ps.cursor.x
            px, py = cx * cw, cy * ch
            p.fillRect(int(px), int(py), int(cw), int(ch), self._cc)
            row  = ps.buffer[cy]
            cell = row[cx] if cx in row else None
            if cell and cell.data and cell.data != '\x00':
                p.setPen(self._bg)
                p.drawText(int(px), int(py + ch - self._descent), cell.data)

    def _paint_plain(self, p):
        """일반 쉘 출력을 행 단위로 그린다."""
        cw, ch = self._cw, self._ch
        visible_rows = self.height() // ch
        total = len(self._plain_lines)
        start = max(0, total - visible_rows - self._scroll_offset)
        p.setPen(self._fg)
        
        last_line_idx = total - 1
        for i, line in enumerate(self._plain_lines[start:start+visible_rows]):
            actual_line_idx = start + i
            px = 0
            py = (i+1) * ch - self._descent
            seg = self._get_selection_segment_for_line(actual_line_idx, line)
            if seg:
                a, b = seg
                left = line[:a]
                mid = line[a:b]
                right = line[b:]

                p.setPen(self._fg)
                if left:
                    p.drawText(px, py, left)

                sel_bg = QColor(PREFS.get('sel_bg', '#264f78'))
                sel_fg = QColor(PREFS.get('sel_fg', '#ffffff'))
                y0 = i * ch
                p.fillRect(int(a * cw), int(y0), int((b - a) * cw), int(ch), sel_bg)
                p.setPen(sel_fg)
                if mid:
                    p.drawText(int(a * cw), py, mid)

                p.setPen(self._fg)
                if right:
                    p.drawText(int(b * cw), py, right)
            else:
                p.setPen(self._fg)
                p.drawText(px, py, line)
            
            # 마지막 줄 끝에 커서 그리기
            if self._cursor_on and self.hasFocus() and actual_line_idx == last_line_idx and self._scroll_offset == 0:
                cursor_x = int(self._plain_col) * cw
                cursor_y = i * ch
                p.fillRect(int(cursor_x), int(cursor_y), int(cw), int(ch), self._cc)

    def _plain_pos_from_point(self, x: int, y: int):
        """화면 좌표를 plain 모드 (line_idx, col)로 변환."""
        cw, ch = self._cw, self._ch
        if cw <= 0 or ch <= 0:
            return None
        visible_rows = max(1, self.height() // ch)
        total = len(self._plain_lines)
        start = max(0, total - visible_rows - self._scroll_offset)
        row = int(y // ch)
        if row < 0:
            row = 0
        if row >= visible_rows:
            row = visible_rows - 1
        line_idx = start + row
        line_idx = max(0, min(line_idx, total - 1))
        col = int(x // cw)
        if col < 0:
            col = 0
        return (line_idx, col)

    def _get_selection_norm(self):
        if not self._sel_active or not self._sel_start or not self._sel_end:
            return None
        a = self._sel_start
        b = self._sel_end
        if a == b:
            return None
        return (a, b) if a < b else (b, a)

    def _get_selection_segment_for_line(self, line_idx: int, line: str):
        """현재 선택 모드에 따라, 해당 line_idx에서 하이라이트할 (a,b) 컬럼을 반환."""
        sel = self._get_selection_norm()
        if not sel:
            return None
        (sl, sc), (el, ec) = sel

        if self._sel_mode == 'rect':
            if not (sl <= line_idx <= el):
                return None
            a = min(sc, ec)
            b = max(sc, ec)
            a = max(0, min(a, len(line)))
            b = max(0, min(b, len(line)))
            return (a, b) if b > a else None

        # linear
        if not (sl <= line_idx <= el):
            return None
        a = sc if line_idx == sl else 0
        b = ec if line_idx == el else len(line)
        a = max(0, min(a, len(line)))
        b = max(0, min(b, len(line)))
        return (a, b) if b > a else None

    def _get_selected_text_plain(self):
        sel = self._get_selection_norm()
        if not sel:
            return ''
        (sl, sc), (el, ec) = sel
        sl = max(0, min(sl, len(self._plain_lines) - 1))
        el = max(0, min(el, len(self._plain_lines) - 1))
        out = []
        if self._sel_mode == 'rect':
            a0 = min(sc, ec)
            b0 = max(sc, ec)
            for li in range(sl, el + 1):
                line = self._plain_lines[li]
                a = max(0, min(a0, len(line)))
                b = max(0, min(b0, len(line)))
                out.append(line[a:b])
        else:
            for li in range(sl, el + 1):
                line = self._plain_lines[li]
                a = sc if li == sl else 0
                b = ec if li == el else len(line)
                a = max(0, min(a, len(line)))
                b = max(0, min(b, len(line)))
                out.append(line[a:b])
        return '\n'.join(out).rstrip('\n')

    # ── 일반 모드 텍스트 추가 ────────────────────────────────
    def append_text(self, raw: str):
        clean = self._ANSI.sub('', raw)
        # \r(캐리지리턴)을 줄바꿈으로 바꾸면 readline/장비 CLI의 라인 편집이 깨진다.
        # 일반 모드에서도 최소한의 "한 줄 덮어쓰기 + 커서 이동"을 구현한다.
        clean = clean.replace('\r\n', '\n')
        if not clean:
            return

        for ch in clean:
            if ch == '\r':
                self._plain_col = 0
                continue

            if ch == '\n':
                self._plain_lines.append('')
                self._plain_col = 0
                continue

            if ch in ('\x08', '\x7f'):
                # 백스페이스: 커서 왼쪽 한 글자 삭제
                if self._plain_col > 0:
                    self._plain_col -= 1
                    line = self._plain_lines[-1]
                    if self._plain_col < len(line):
                        self._plain_lines[-1] = line[:self._plain_col] + line[self._plain_col + 1:]
                continue

            # 탭은 화면에서는 공백으로 확장(서버로는 원본 \t 가 이미 전달됨)
            if ch == '\t':
                spaces = 8 - (self._plain_col % 8)
                for _ in range(spaces):
                    self._put_plain_char(' ')
                continue

            if ord(ch) >= 0x20:
                self._put_plain_char(ch)

        self._scroll_offset = 0
        self.update()

    def _put_plain_char(self, ch: str):
        """일반 모드 현재 줄에 커서 위치 기준으로 문자 출력(덮어쓰기)."""
        line = self._plain_lines[-1]
        col = int(self._plain_col)
        if col >= len(line):
            line = line + (' ' * (col - len(line))) + ch
        else:
            line = line[:col] + ch + line[col + 1:]
        self._plain_lines[-1] = line
        self._plain_col = col + 1

    def append_system(self, text: str):
        for ch in (text + '\n'):
            if ch == '\n':
                self._plain_lines.append('')
            else:
                self._plain_lines[-1] += ch
        self._scroll_offset = 0
        self.update()

    # ── vi 모드 진입/종료 ────────────────────────────────────
    def enter_vi_mode(self):
        self._vi_mode   = True
        self._appkeypad = False
        self._pyte_screen = pyte.Screen(self._pty_cols, self._pty_rows)
        self._pyte_stream = pyte.ByteStream(self._pyte_screen)
        self.update()

    def exit_vi_mode(self):
        self._vi_mode   = False
        self._appkeypad = False
        self.update()

    def feed_vi(self, raw: str):
        """vi 출력을 pyte에 공급."""
        # 애플리케이션 키패드 모드(App Keypad Mode) 설정 및 해제 감지 강화
        if re.search(r'\x1b\[\?.*1h', raw) or '\x1b=' in raw:
            self._appkeypad = True
        if re.search(r'\x1b\[\?.*1l', raw) or '\x1b>' in raw:
            self._appkeypad = False
            
        try:
            self._pyte_stream.feed(raw.encode('utf-8', errors='replace'))
        except Exception:
            pass
        self.update()

    # ── 스크롤 ───────────────────────────────────────────────
    def wheelEvent(self, event):
        if not self._vi_mode:
            delta = event.angleDelta().y()
            if delta > 0:
                self._scroll_offset = min(self._scroll_offset + 3,
                                          max(0, len(self._plain_lines) - 1))
            else:
                self._scroll_offset = max(self._scroll_offset - 3, 0)
            self.update()

    # ── 새 명령어 입력으로 기존 입력 교체 로직 ────────────────
    def _replace_current_input(self, new_text: str):
        # 서버 프롬프트 라인에 "붙어서" 보이지 않게, 서버 입력 라인을 먼저 비우고 교체한다.
        # readline 계열에 가장 보편적으로 동작하는 조합: Ctrl+A(줄 처음) + Ctrl+K(커서 뒤 삭제)
        self.send_data.emit('\x01')  # Ctrl+A
        self.send_data.emit('\x0b')  # Ctrl+K

        self._local_buf = new_text
        self._update_local_label()

        if new_text:
            self.send_data.emit(new_text)

    # ── 키 입력 ──────────────────────────────────────────────
    def keyPressEvent(self, event):
        key  = event.key()
        mods = event.modifiers()
        text = event.text()

        # Ctrl 조합
        if mods & Qt.ControlModifier:
            tbl = {Qt.Key_C:'\x03', Qt.Key_D:'\x04', Qt.Key_Z:'\x1a',
                   Qt.Key_L:'\x0c', Qt.Key_A:'\x01', Qt.Key_E:'\x05',
                   Qt.Key_U:'\x15', Qt.Key_K:'\x0b', Qt.Key_W:'\x17'}
            if key in tbl:
                self.send_data.emit(tbl[key]); return

        if key == Qt.Key_Escape:
            self.send_data.emit('\x1b'); return

        # ── 화살표 ───────────────────────────────────────────
        if key == Qt.Key_Up:
            seq = '\x1bOA' if (self._vi_mode and self._appkeypad) else '\x1b[A'
            self.send_data.emit(seq); return

        if key == Qt.Key_Down:
            seq = '\x1bOB' if (self._vi_mode and self._appkeypad) else '\x1b[B'
            self.send_data.emit(seq); return

        if key == Qt.Key_Left:
            if self._vi_mode:
                seq = '\x1bOD' if self._appkeypad else '\x1b[D'
                self.send_data.emit(seq)
            else:
                # ← / → 를 서버 히스토리 탐색으로 매핑 (readline: ↑/↓)
                # 로컬에서 문자열을 재전송(교체)하면 장비에 따라 "붙어서" 보일 수 있어
                # 서버의 기본 히스토리 기능을 사용한다.
                self.send_data.emit('\x1b[A')
            return

        if key == Qt.Key_Right:
            if self._vi_mode:
                seq = '\x1bOC' if self._appkeypad else '\x1b[C'
                self.send_data.emit(seq)
            else:
                self.send_data.emit('\x1b[B')
            return

        # 기능키
        fkeys = {Qt.Key_F1:'\x1bOP',  Qt.Key_F2:'\x1bOQ',
                 Qt.Key_F3:'\x1bOR',  Qt.Key_F4:'\x1bOS',
                 Qt.Key_F5:'\x1b[15~',Qt.Key_F6:'\x1b[17~',
                 Qt.Key_F7:'\x1b[18~',Qt.Key_F8:'\x1b[19~',
                 Qt.Key_F9:'\x1b[20~',Qt.Key_F10:'\x1b[21~',
                 Qt.Key_F11:'\x1b[23~',Qt.Key_F12:'\x1b[24~',
                 Qt.Key_Delete:'\x1b[3~',Qt.Key_Insert:'\x1b[2~',
                 Qt.Key_Home:'\x1b[H', Qt.Key_End:'\x1b[F',
                 Qt.Key_PageUp:'\x1b[5~',Qt.Key_PageDown:'\x1b[6~'}
        if key in fkeys:
            self.send_data.emit(fkeys[key]); return

        if key in (Qt.Key_Return, Qt.Key_Enter):
            if not self._vi_mode:
                cmd = self._local_buf
                self.send_data.emit('\r')
                self._local_buf = ''
                self._update_local_label()
                return
            self.send_data.emit('\r'); return

        if key == Qt.Key_Backspace:
            if not self._vi_mode and self._local_buf:
                self._local_buf = self._local_buf[:-1]
                self._update_local_label()
            # 장비/서버마다 BS(0x08) 또는 DEL(0x7f)로 지움.
            # 사용자가 "안 먹는다"고 한 케이스가 있어 우선 BS를 보낸다.
            self.send_data.emit('\x08'); return

        if key == Qt.Key_Tab:
            self.send_data.emit('\t'); return

        if text and ord(text[0]) >= 0x20:
            if not self._vi_mode:
                self._local_buf += text
                self._update_local_label()
            self.send_data.emit(text); return

    def _update_local_label(self):
        if self.local_input_label:
            self.local_input_label.setText(f'❯ {self._local_buf}▌')

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('복사',      self._copy)
        menu.addAction('붙여넣기', self._paste)
        menu.addSeparator()
        menu.addAction('화면 지우기', self._clear)
        menu.exec_(event.globalPos())

    def _copy(self):
        if self._vi_mode:
            ps    = self._pyte_screen
            lines = []
            for y in range(ps.lines):
                row  = ps.buffer[y]
                line = ''.join(
                    (row[x].data if x in row and row[x].data and row[x].data != '\x00' else ' ')
                    for x in range(ps.columns)
                ).rstrip()
                lines.append(line)
            while lines and not lines[-1]: lines.pop()
            QApplication.clipboard().setText('\n'.join(lines))
        else:
            sel = self._get_selected_text_plain()
            QApplication.clipboard().setText(sel if sel else '\n'.join(self._plain_lines))

    def _paste(self):
        clip = QApplication.clipboard().text()
        if clip:
            self.send_data.emit(clip)

    def _clear(self):
        self._plain_lines = ['']
        self._scroll_offset = 0
        self.update()


# ══════════════════════════════════════════════════════════════
#  TerminalWidget
# ══════════════════════════════════════════════════════════════
class TerminalWidget(QWidget):
    status_changed = pyqtSignal(str, str)

    def __init__(self, session_info: dict, parent=None):
        super().__init__(parent)
        self.info   = session_info
        self.worker = None
        self._build_ui()
        self._connect_session()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.screen = TerminalScreen(self)
        self.screen.send_data.connect(self._on_send_data)
        self.screen.resized.connect(self._on_resized)  # 리사이즈 시그널 연결
        layout.addWidget(self.screen)

        # 로컬 입력 표시줄
        self.local_input_bar = QWidget()
        self.local_input_bar.setFixedHeight(26)
        bg = PREFS.get('bg_color', '#0d1117')
        cc = PREFS.get('cursor_color', '#5a9fd4')
        fn = PREFS.get('font_family', 'Consolas')
        fs = PREFS.get('font_size', 12)
        self.local_input_bar.setStyleSheet(f'background:{bg};border-top:1px solid #2a2d35;')
        lib = QHBoxLayout(self.local_input_bar)
        lib.setContentsMargins(8, 0, 8, 0)
        self.local_input_label = QLabel('❯ ▌')
        self.local_input_label.setStyleSheet(
            f'color:{cc};font-family:{fn};font-size:{fs}px;background:transparent;')
        lib.addWidget(self.local_input_label)
        lib.addStretch()
        tip = QLabel('← 이전  → 이후  Enter 전송')
        tip.setStyleSheet('color:#444;font-size:10px;background:transparent;')
        lib.addWidget(tip)
        layout.addWidget(self.local_input_bar)

        self.screen.local_input_label = self.local_input_label
        self.local_input_bar.setVisible(PREFS.get('show_local_input', False))

    def _on_resized(self, cols, rows):
        if self.worker:
            self.worker.resize_pty(cols, rows)

    def _on_send_data(self, text: str):
        if self.worker and self.worker._running:
            self.worker.send(text)

    def _connect_session(self):
        charset = PREFS.get('charset', 'UTF-8')
        self.screen.append_system(
            f"접속 중: {self.info['username']}@{self.info['host']}:{self.info['port']}  [{charset}]")
        self.worker = SSHWorker(self.info)
        
        # 워커 시작 전 현재 터미널 창 크기 할당
        self.worker.cols = self.screen._pty_cols
        self.worker.rows = self.screen._pty_rows
        
        self.worker.output_received.connect(self._on_output)
        self.worker.connected.connect(self._on_connected)
        self.worker.disconnected.connect(self._on_disconnected)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def apply_prefs(self):
        self.screen._apply_prefs()
        bg = PREFS.get('bg_color', '#0d1117')
        cc = PREFS.get('cursor_color', '#5a9fd4')
        fn = PREFS.get('font_family', 'Consolas')
        fs = PREFS.get('font_size', 12)
        self.local_input_bar.setStyleSheet(f'background:{bg};border-top:1px solid #2a2d35;')
        self.local_input_label.setStyleSheet(
            f'color:{cc};font-family:{fn};font-size:{fs}px;background:transparent;')
        self.local_input_bar.setVisible(PREFS.get('show_local_input', False))

    def _on_output(self, text: str):
        scr = self.screen

        # [6n 커서위치 질의 응답
        if '\x1b[6n' in text:
            self.worker.send('\x1b[1;1R')

        # vi 진입 감지 확장 (1049, 1047, 47 등 대체 버퍼)
        if re.search(r'\x1b\[\?(?:1049|1047|47)h', text):
            if not scr._vi_mode:
                scr.enter_vi_mode()

        # vi 종료 감지 확장
        if re.search(r'\x1b\[\?(?:1049|1047|47)l', text):
            if scr._vi_mode:
                scr.exit_vi_mode()

        # 출력 라우팅
        if scr._vi_mode:
            scr.feed_vi(text)
        else:
            scr.append_text(text)

    def _on_connected(self):
        self.screen.append_system(f'✓ 연결됨: {self.info["host"]}')
        self.status_changed.emit(f'연결됨: {self.info["host"]}', '#28c840')
        self.screen.setFocus()

    def _on_disconnected(self, msg: str):
        self.screen.append_system(f'[{msg}]')
        self.status_changed.emit('연결 없음', '#888')

    def _on_error(self, msg: str):
        self.screen.append_system(f'[오류] {msg}')
        self.status_changed.emit(f'오류: {msg}', '#ff5f57')

    def _append_system(self, text: str):
        self.screen.append_system(text)

    def disconnect(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(2000)

    def get_sftp(self):
        if self.worker and self.worker.client and self.worker._running:
            return self.worker.client.open_sftp()
        return None

    def get_host(self):
        return self.info['host']

    def get_terminal_screen(self):
        return self.screen

class SFTPDialog(QDialog):
    def __init__(self, sftp, host: str, parent=None):
        super().__init__(parent)
        self.sftp = sftp
        self.host = host
        self.current_path = "/"
        self.setWindowTitle(f"SFTP 파일 관리 — {host}")
        self.resize(820, 560)
        self._build_ui()
        self._list_dir(self.current_path)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        path_bar = QHBoxLayout()
        path_bar.addWidget(QLabel("경로:"))
        self.path_edit = QLineEdit(self.current_path)
        self.path_edit.returnPressed.connect(lambda: self._list_dir(self.path_edit.text()))
        path_bar.addWidget(self.path_edit)
        btn_go   = QPushButton("이동");  btn_go.setFixedWidth(70)
        btn_up   = QPushButton("↑ 상위"); btn_up.setFixedWidth(70)
        btn_home = QPushButton("⌂ 홈");  btn_home.setFixedWidth(70)
        btn_go.clicked.connect(lambda: self._list_dir(self.path_edit.text()))
        btn_up.clicked.connect(self._go_up)
        btn_home.clicked.connect(lambda: self._list_dir("/"))
        for b in [btn_go, btn_up, btn_home]:
            path_bar.addWidget(b)
        layout.addLayout(path_bar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["이름", "크기", "권한", "수정일"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table)

        btn_bar = QHBoxLayout()
        for lbl, fn in [("⬆ 업로드", self._upload), ("⬇ 다운로드", self._download),
                        ("📁 폴더 생성", self._mkdir), ("🗑 삭제", self._delete)]:
            b = QPushButton(lbl); b.clicked.connect(fn); btn_bar.addWidget(b)
        btn_bar.addStretch()
        btn_close = QPushButton("닫기"); btn_close.clicked.connect(self.close)
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

        self.status = QLabel("준비")
        self.status.setStyleSheet("color:#888; font-size:11px;")
        layout.addWidget(self.status)

    def _list_dir(self, path: str):
        try:
            import stat, datetime
            attrs = self.sftp.listdir_attr(path)
            self.current_path = path
            self.path_edit.setText(path)
            self.table.setRowCount(0)
            if path != "/":
                self.table.insertRow(0)
                self.table.setItem(0, 0, QTableWidgetItem("📁 .."))
                for c in [1,2,3]: self.table.setItem(0, c, QTableWidgetItem(""))
            for a in sorted(attrs, key=lambda x: (not stat.S_ISDIR(x.st_mode), x.filename)):
                r = self.table.rowCount(); self.table.insertRow(r)
                is_dir = stat.S_ISDIR(a.st_mode)
                name   = ("📁 " if is_dir else "📄 ") + a.filename
                size   = "" if is_dir else self._fmt_size(a.st_size)
                perms  = oct(a.st_mode)[-4:]
                mtime  = datetime.datetime.fromtimestamp(a.st_mtime).strftime("%Y-%m-%d %H:%M")
                for c, v in enumerate([name, size, perms, mtime]):
                    item = QTableWidgetItem(v)
                    if is_dir: item.setForeground(QColor("#7ec8e3"))
                    self.table.setItem(r, c, item)
            self.status.setText(f"{self.table.rowCount()}개 항목  |  {path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"디렉토리 읽기 실패:\n{e}")

    def _fmt_size(self, size):
        for unit in ["B","KB","MB","GB"]:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _on_double_click(self, index):
        name = self.table.item(index.row(), 0).text().lstrip("📁📄 ")
        if name == "..": self._go_up(); return
        new_path = self.current_path.rstrip("/") + "/" + name
        try:
            import stat
            if stat.S_ISDIR(self.sftp.stat(new_path).st_mode):
                self._list_dir(new_path)
        except Exception: pass

    def _go_up(self):
        p = str(Path(self.current_path).parent)
        self._list_dir(p if p else "/")

    def _context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("⬇ 다운로드", self._download)
        menu.addAction("🗑 삭제",     self._delete)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _upload(self):
        files, _ = QFileDialog.getOpenFileNames(self, "업로드할 파일 선택")
        if not files: return
        prog = QProgressDialog("업로드 중...", "취소", 0, len(files), self)
        prog.setWindowModality(Qt.WindowModal)
        for i, local_path in enumerate(files):
            if prog.wasCanceled(): break
            fname    = Path(local_path).name
            rem_path = self.current_path.rstrip("/") + "/" + fname
            prog.setLabelText(f"업로드: {fname}"); prog.setValue(i)
            QApplication.processEvents()
            try: self.sftp.put(local_path, rem_path)
            except Exception as e: QMessageBox.warning(self, "업로드 실패", str(e))
        prog.setValue(len(files)); self._list_dir(self.current_path)

    def _download(self):
        row = self.table.currentRow()
        if row < 0: return
        name = self.table.item(row, 0).text().lstrip("📁📄 ")
        if name == "..": return
        save_path, _ = QFileDialog.getSaveFileName(self, "저장 위치", name)
        if not save_path: return
        rem_path = self.current_path.rstrip("/") + "/" + name
        try:
            self.sftp.get(rem_path, save_path)
            QMessageBox.information(self, "완료", f"다운로드 완료:\n{save_path}")
        except Exception as e: QMessageBox.critical(self, "오류", str(e))

    def _mkdir(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "폴더 생성", "폴더 이름:")
        if ok and name:
            try:
                self.sftp.mkdir(self.current_path.rstrip("/") + "/" + name)
                self._list_dir(self.current_path)
            except Exception as e: QMessageBox.critical(self, "오류", str(e))

    def _delete(self):
        row = self.table.currentRow()
        if row < 0: return
        name = self.table.item(row, 0).text().lstrip("📁📄 ")
        if name == "..": return
        if QMessageBox.question(self, "삭제 확인", f"'{name}' 을(를) 삭제하시겠습니까?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        rem_path = self.current_path.rstrip("/") + "/" + name
        try:
            try: self.sftp.remove(rem_path)
            except IOError: self.sftp.rmdir(rem_path)
            self._list_dir(self.current_path)
        except Exception as e: QMessageBox.critical(self, "오류", str(e))


# ══════════════════════════════════════════════════════════════
#  환경 설정 다이얼로그
# ══════════════════════════════════════════════════════════════
class PreferencesDialog(QDialog):
    prefs_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("환경 설정")
        self.resize(560, 520)
        self._prefs = dict(PREFS)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        tabs = QTabWidget()

        # ═══ 탭 1: 폰트 ═══════════════════════════════════════
        font_tab = QWidget()
        ft = QFormLayout(font_tab)
        ft.setSpacing(10); ft.setContentsMargins(16, 16, 16, 8)

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Consolas", "Courier New", "Lucida Console", "Monaco",
            "DejaVu Sans Mono", "Liberation Mono", "Fira Code",
            "JetBrains Mono", "Cascadia Code", "Source Code Pro",
            "D2Coding", "Nanum Gothic Coding", "Malgun Gothic",
        ])
        self.font_family_combo.setEditable(True)
        idx = self.font_family_combo.findText(self._prefs["font_family"])
        if idx >= 0: self.font_family_combo.setCurrentIndex(idx)
        ft.addRow("글꼴:", self.font_family_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(7, 32)
        self.font_size_spin.setValue(self._prefs["font_size"])
        ft.addRow("크기:", self.font_size_spin)

        self.font_preview = QLabel(
            "Hello 안녕 ABC abc 0O1lI|\n"
            "ls -la /usr/local/bin\n"
            "ssh user@192.168.1.1 -p 22\n"
            "grep -rn 'pattern' *.log"
        )
        self._refresh_font_preview()
        self.font_preview.setMinimumHeight(90)
        self.font_family_combo.currentTextChanged.connect(self._refresh_font_preview)
        self.font_size_spin.valueChanged.connect(self._refresh_font_preview)
        ft.addRow("미리보기:", self.font_preview)
        tabs.addTab(font_tab, "🔤 폰트")

        # ═══ 탭 2: 색상 / 테마 ════════════════════════════════
        color_tab = QWidget()
        cv = QVBoxLayout(color_tab)
        cv.setContentsMargins(14, 14, 14, 8); cv.setSpacing(10)

        # 테마 프리셋
        theme_group = QGroupBox("테마 프리셋 (클릭하면 즉시 미리보기)")
        tg = QVBoxLayout(theme_group)
        tg.setSpacing(5); tg.setContentsMargins(10, 10, 10, 8)
        row_w = None; row_l = None
        for i, (name, theme) in enumerate(THEMES.items()):
            if i % 3 == 0:
                row_w = QWidget()
                row_l = QHBoxLayout(row_w)
                row_l.setContentsMargins(0,0,0,0); row_l.setSpacing(6)
                tg.addWidget(row_w)
            btn = QPushButton(name)
            btn.setFixedHeight(28)
            # 테마 배경색으로 버튼 채색
            tbg = theme.get("bg_color","#1a1a1a")
            tfg = theme.get("fg_color","#ffffff")
            btn.setStyleSheet(
                f"background:{tbg}; color:{tfg}; border:1px solid #555;"
                f"border-radius:3px; font-size:11px; padding:2px 4px;"
            )
            btn.clicked.connect(lambda checked, n=name: self._apply_theme_preset(n))
            row_l.addWidget(btn)
        if row_l and row_l.count() % 3 != 0:
            row_l.addStretch()
        cv.addWidget(theme_group)

        # 개별 색상 직접 선택
        color_group = QGroupBox("색상 직접 설정")
        cf_layout = QVBoxLayout(color_group)
        cf_layout.setSpacing(8); cf_layout.setContentsMargins(10,10,10,8)

        self._color_btns = {}
        color_defs = [
            ("bg_color",     "배경색",      "터미널 배경"),
            ("fg_color",     "글자색",      "기본 텍스트 색"),
            ("cursor_color", "커서/강조색", "커서 및 포커스 강조"),
        ]
        for key, label, desc in color_defs:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}  ({desc})")
            lbl.setFixedWidth(200)
            lbl.setStyleSheet("color:#aaa; font-size:12px;")
            row.addWidget(lbl)

            btn = QPushButton()
            btn.setFixedSize(140, 28)
            self._set_color_btn(btn, self._prefs[key])
            btn.clicked.connect(lambda checked, k=key, b=btn: self._pick_color(k, b))
            self._color_btns[key] = btn
            row.addWidget(btn)
            row.addStretch()
            cf_layout.addLayout(row)

        cv.addWidget(color_group)

        # 컬러 미리보기 패널
        preview_group = QGroupBox("미리보기")
        pl = QVBoxLayout(preview_group)
        pl.setContentsMargins(10,8,10,8)
        self._color_preview = QLabel(
            "user@server:~$ ls -la /etc\n"
            "drwxr-xr-x  128 root root  4096 May  7 09:12 .\n"
            "drwxr-xr-x   20 root root  4096 May  7 09:00 ..\n"
            "-rw-r--r--    1 root root  3028 May  7 08:55 passwd\n"
            "user@server:~$ █"
        )
        self._color_preview.setMinimumHeight(100)
        self._refresh_color_preview()
        pl.addWidget(self._color_preview)
        cv.addWidget(preview_group)
        cv.addStretch()
        tabs.addTab(color_tab, "🎨 색상/테마")

        # ═══ 탭 3: 터미널 ══════════════════════════════════════
        term_tab = QWidget()
        tt = QFormLayout(term_tab)
        tt.setSpacing(10); tt.setContentsMargins(16, 16, 16, 8)

        self.charset_combo = QComboBox()
        self.charset_combo.addItems([
            "UTF-8", "EUC-KR", "CP949", "EUC-JP", "Shift_JIS",
            "GB2312", "Big5", "ISO-8859-1", "CP1252", "ASCII"
        ])
        idx = self.charset_combo.findText(self._prefs["charset"])
        if idx >= 0: self.charset_combo.setCurrentIndex(idx)
        tt.addRow("문자 인코딩:", self.charset_combo)

        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 5000)
        self.history_spin.setValue(self._prefs.get("history_size", 500))
        self.history_spin.setSuffix(" 개")
        tt.addRow("히스토리 크기:", self.history_spin)

        # Keep-Alive
        ka_group = QGroupBox("세션 유지 (Keep-Alive)")
        kal = QFormLayout(ka_group)
        kal.setSpacing(8); kal.setContentsMargins(12, 12, 12, 8)

        self.ka_enable_cb = QCheckBox("Keep-Alive 활성화")
        self.ka_enable_cb.setChecked(self._prefs.get("keepalive_enabled", False))
        kal.addRow(self.ka_enable_cb)

        self.ka_interval_spin = QSpinBox()
        self.ka_interval_spin.setRange(5, 3600)
        self.ka_interval_spin.setValue(self._prefs.get("keepalive_interval", 60))
        self.ka_interval_spin.setSuffix(" 초")
        self.ka_interval_spin.setEnabled(self._prefs.get("keepalive_enabled", False))
        self.ka_enable_cb.toggled.connect(self.ka_interval_spin.setEnabled)
        kal.addRow("전송 간격:", self.ka_interval_spin)

        ka_info = QLabel("• SSH Transport 레벨에서 주기적으로 keepalive 패킷을 전송합니다.\n"
                         "• 비활성 세션이 서버/방화벽에 의해 끊기는 것을 방지합니다.")
        ka_info.setStyleSheet("color:#666; font-size:11px;")
        kal.addRow(ka_info)
        tt.addRow(ka_group)

        hint = QLabel(
            "• ← / → 화살표: 이전 / 이후 명령어 히스토리 탐색\n"
            "• ↑ / ↓ 화살표: 서버로 그대로 전달 (vi, less 등)\n"
            "• Enter: 명령어 전송  |  ESC: 입력 취소\n"
            "• Ctrl+C/D/Z: 제어 문자 전송  |  백스페이스: 삭제"
        )
        hint.setStyleSheet("color:#555; font-size:11px;")
        tt.addRow(hint)
        tabs.addTab(term_tab, "⚙ 터미널")

        layout.addWidget(tabs)

        # 버튼
        btn_box    = QDialogButtonBox()
        btn_apply  = btn_box.addButton("적용",   QDialogButtonBox.ApplyRole)
        btn_ok     = btn_box.addButton("확인",   QDialogButtonBox.AcceptRole)
        btn_cancel = btn_box.addButton("취소",   QDialogButtonBox.RejectRole)
        btn_reset  = btn_box.addButton("기본값", QDialogButtonBox.ResetRole)
        btn_apply.clicked.connect(self._apply)
        btn_ok.clicked.connect(lambda: (self._apply(), self.accept()))
        btn_cancel.clicked.connect(self.reject)
        btn_reset.clicked.connect(self._reset)
        layout.addWidget(btn_box)

    # ── 헬퍼 ─────────────────────────────────────────────────
    def _refresh_font_preview(self):
        ff = self.font_family_combo.currentText()
        fs = self.font_size_spin.value()
        bg = self._prefs.get("bg_color", "#0d1117")
        fg = self._prefs.get("fg_color", "#c9d1d9")
        self.font_preview.setStyleSheet(
            f"background:{bg}; color:{fg}; padding:10px; border:1px solid #333;"
            f"font-family:'{ff}'; font-size:{fs}px;"
        )

    def _refresh_color_preview(self):
        """색상 미리보기 패널 갱신"""
        bg = self._prefs.get("bg_color", "#0d1117")
        fg = self._prefs.get("fg_color", "#c9d1d9")
        ff = self._prefs.get("font_family", "Consolas")
        fs = self._prefs.get("font_size", 12)
        self._color_preview.setStyleSheet(
            f"background:{bg}; color:{fg}; padding:10px; border:1px solid #333;"
            f"font-family:'{ff}'; font-size:{fs}px;"
        )
        # 폰트 미리보기도 함께 갱신
        if hasattr(self, "font_preview"):
            self._refresh_font_preview()

    def _set_color_btn(self, btn: QPushButton, color: str):
        btn.setText(color)
        c = QColor(color)
        lum = 0.299*c.red() + 0.587*c.green() + 0.114*c.blue()
        txt = "#000" if lum > 128 else "#fff"
        btn.setStyleSheet(f"background:{color}; color:{txt}; border:1px solid #555; border-radius:3px;")

    def _pick_color(self, key: str, btn: QPushButton):
        from PyQt5.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self._prefs[key]), self)
        if c.isValid():
            self._prefs[key] = c.name()
            self._set_color_btn(btn, c.name())
            self._refresh_color_preview()

    def _apply_theme_preset(self, name: str):
        theme = THEMES.get(name, {})
        for k in ("bg_color", "fg_color", "cursor_color"):
            if k in theme:
                self._prefs[k] = theme[k]
                if k in self._color_btns:
                    self._set_color_btn(self._color_btns[k], theme[k])
        self._prefs["theme"] = name
        self._refresh_color_preview()

    def _apply(self):
        global PREFS
        self._prefs["font_family"]        = self.font_family_combo.currentText()
        self._prefs["font_size"]          = self.font_size_spin.value()
        self._prefs["charset"]            = self.charset_combo.currentText()
        self._prefs["history_size"]       = self.history_spin.value()
        self._prefs["keepalive_enabled"]  = self.ka_enable_cb.isChecked()
        self._prefs["keepalive_interval"] = self.ka_interval_spin.value()
        PREFS.update(self._prefs)
        save_prefs(PREFS)
        self.prefs_applied.emit()

    def _reset(self):
        global PREFS
        PREFS = dict(DEFAULT_PREFS)
        save_prefs(PREFS)
        self.prefs_applied.emit()
        self.accept()
        QMessageBox.information(self.parent(), "초기화", "환경 설정이 기본값으로 초기화되었습니다.")


# ══════════════════════════════════════════════════════════════
#  세션 추가/편집 다이얼로그
# ══════════════════════════════════════════════════════════════
class SessionDialog(QDialog):
    def __init__(self, parent=None, session=None, groups=None):
        super().__init__(parent)
        self.session = session or {}
        self.groups  = groups or ["Default"]
        self.setWindowTitle("세션 편집" if session else "새 세션")
        self.resize(420, 340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout(); form.setSpacing(8)

        self.name_edit  = QLineEdit(self.session.get("name", ""))
        self.host_edit  = QLineEdit(self.session.get("host", ""))
        self.port_spin  = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.session.get("port", 22))
        self.user_edit  = QLineEdit(self.session.get("username", ""))
        self.pass_edit  = QLineEdit(self.session.get("password", ""))
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.auth_combo = QComboBox()
        self.auth_combo.addItems(["password", "key"])
        self.auth_combo.setCurrentText(self.session.get("auth", "password"))
        self.auth_combo.currentTextChanged.connect(self._on_auth_change)
        self.key_edit   = QLineEdit(self.session.get("key_file", ""))
        btn_browse      = QPushButton("찾아보기")
        btn_browse.clicked.connect(self._browse_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit); key_row.addWidget(btn_browse)
        self.group_combo = QComboBox()
        self.group_combo.addItems(self.groups)
        self.group_combo.setEditable(True)

        form.addRow("세션 이름:", self.name_edit)
        form.addRow("호스트:",   self.host_edit)
        form.addRow("포트:",     self.port_spin)
        form.addRow("사용자명:", self.user_edit)
        form.addRow("인증 방식:", self.auth_combo)
        form.addRow("비밀번호:", self.pass_edit)
        form.addRow("개인키 파일:", key_row)
        form.addRow("그룹:",     self.group_combo)
        layout.addLayout(form)
        self._on_auth_change(self.auth_combo.currentText())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_auth_change(self, auth: str):
        is_key = (auth == "key")
        self.pass_edit.setEnabled(not is_key)
        self.key_edit.setEnabled(is_key)

    def _browse_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "개인키 파일 선택",
                                               str(Path.home() / ".ssh"))
        if path: self.key_edit.setText(path)

    def get_data(self):
        return {
            "name":     self.name_edit.text().strip(),
            "host":     self.host_edit.text().strip(),
            "port":     self.port_spin.value(),
            "username": self.user_edit.text().strip(),
            "password": self.pass_edit.text(),
            "auth":     self.auth_combo.currentText(),
            "key_file": self.key_edit.text().strip(),
        }, self.group_combo.currentText()


# ══════════════════════════════════════════════════════════════
#  메인 윈도우
# ══════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_mgr = SessionManager()
        self.setWindowTitle("PySSH Manager")
        self.resize(1280, 800)
        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._load_session_tree()

    # ── 메뉴 바 ─────────────────────────────────────────────
    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("파일(&F)")
        file_menu.addAction("새 세션(&N)",    self._new_session,    QKeySequence("Ctrl+N"))
        file_menu.addAction("빠른 접속(&Q)",  self._quick_connect,  QKeySequence("Ctrl+Q"))
        file_menu.addSeparator()
        file_menu.addAction("종료(&X)",       self.close,           QKeySequence("Alt+F4"))

        view_menu = mb.addMenu("보기(&V)")
        view_menu.addAction("세션 패널 토글", self._toggle_sidebar, QKeySequence("Ctrl+B"))

        # 로컬 입력줄 표시 토글 (체크 메뉴)
        self._local_input_action = QAction("로컬 입력줄 표시", self)
        self._local_input_action.setCheckable(True)
        self._local_input_action.setChecked(PREFS.get("show_local_input", False))
        self._local_input_action.toggled.connect(self._toggle_local_input)
        view_menu.addAction(self._local_input_action)

        tools_menu = mb.addMenu("도구(&T)")
        tools_menu.addAction("SFTP 파일 관리자", self._open_sftp)
        tools_menu.addSeparator()
        tools_menu.addAction("⚙ 환경 설정...",   self._show_preferences, QKeySequence("Ctrl+,"))

        help_menu = mb.addMenu("도움말(&H)")
        help_menu.addAction("단축키 안내",  self._show_shortcuts)
        help_menu.addAction("정보",         self._show_about)

    # ── 툴바 ────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = QToolBar("메인 툴바")
        tb.setIconSize(QSize(16, 16))
        tb.setMovable(False)
        self.addToolBar(tb)
        for text, slot in [
            ("⊕ 새 세션",   self._new_session),
            ("⚡ 빠른 접속", self._quick_connect),
            ("✕ 탭 닫기",   self._close_current_tab),
            ("⇌ 재연결",    self._reconnect),
            ("📂 SFTP",     self._open_sftp),
            ("⎙ 로그 저장", self._save_log),
            ("⚙ 환경설정",  self._show_preferences),
        ]:
            act = tb.addAction(text)
            act.triggered.connect(slot)

    # ── 중앙 위젯 ───────────────────────────────────────────
    def _build_central(self):
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # 좌측: 세션 패널
        sidebar = QWidget(); sidebar.setFixedWidth(220)
        sb = QVBoxLayout(sidebar); sb.setContentsMargins(0,0,0,0); sb.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background:#252830; border-bottom:1px solid #333;")
        header.setFixedHeight(30)
        hl = QHBoxLayout(header); hl.setContentsMargins(8,0,8,0)
        lbl = QLabel("SESSION MANAGER")
        lbl.setStyleSheet("color:#888; font-size:10px; font-weight:bold; letter-spacing:1px;")
        hl.addWidget(lbl); hl.addStretch()
        add_btn = QPushButton("+"); add_btn.setFixedSize(20,20)
        add_btn.setStyleSheet("background:#3a4060; border:none; color:#7ec8e3; font-size:15px; border-radius:10px;")
        add_btn.clicked.connect(self._new_session); hl.addWidget(add_btn)
        sb.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True); self.tree.setIndentation(14)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_session_double_click)
        sb.addWidget(self.tree)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 세션 검색...")
        self.search_edit.textChanged.connect(self._filter_sessions)
        self.search_edit.setStyleSheet(
            "background:#1a1d21; border:none; border-top:1px solid #333;"
            "color:#bbb; padding:5px 8px; font-size:12px;"
        )
        sb.addWidget(self.search_edit)
        self.splitter.addWidget(sidebar)

        # 우측: 탭
        right = QWidget()
        rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.setDocumentMode(True)

        self.welcome = QLabel(
            "세션을 더블클릭하거나 Ctrl+Q 로 빠른 접속\n\n"
            "PySSH Manager  —  SecureCRT 스타일 SSH 클라이언트\n\n"
            "터미널 화면을 클릭하면 바로 키보드 입력이 가능합니다.\n"
            "← / → 화살표로 이전/이후 명령어 히스토리를 탐색하세요."
        )
        self.welcome.setAlignment(Qt.AlignCenter)
        self.welcome.setStyleSheet("color:#444; font-size:14px;")
        self.tab_widget.addTab(self.welcome, "환영합니다")
        self.tab_widget.tabBar().setTabButton(0, QTabBar.RightSide, None)

        rl.addWidget(self.tab_widget)
        self.splitter.addWidget(right)
        self.splitter.setSizes([220, 1060])

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("준비")
        self.status_bar.addWidget(self.status_label)
        ka_str = "  [Keep-Alive ON]" if PREFS.get("keepalive_enabled") else ""
        self.status_bar.addPermanentWidget(QLabel(f"PySSH Manager v2.0{ka_str}"))

    # ── 세션 트리 ───────────────────────────────────────────
    def _load_session_tree(self):
        self.tree.clear()
        for group in self.session_mgr.get_groups():
            g_item = QTreeWidgetItem([group["name"]])
            g_item.setForeground(0, QColor("#7ec8e3"))
            g_item.setFont(0, QFont("Consolas", 11, QFont.Bold))
            g_item.setData(0, Qt.UserRole, {"type": "group", "name": group["name"]})
            for s in group["sessions"]:
                s_item = QTreeWidgetItem([f"  {s['name']}"])
                s_item.setForeground(0, QColor("#aaa"))
                s_item.setData(0, Qt.UserRole, {"type": "session", "group": group["name"], **s})
                g_item.addChild(s_item)
            self.tree.addTopLevelItem(g_item)
        self.tree.expandAll()

    def _filter_sessions(self, text: str):
        text = text.lower()
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            any_vis = False
            for j in range(g.childCount()):
                s = g.child(j)
                vis = text in s.text(0).lower()
                s.setHidden(not vis)
                if vis: any_vis = True
            g.setHidden(not any_vis and text != "")

    def _tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        data = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        if data and data.get("type") == "session":
            menu.addAction("🔗 접속",  lambda: self._open_session(data))
            menu.addAction("✏ 편집",   lambda: self._edit_session(data))
            menu.addAction("📋 복제",  lambda: self._clone_session(data))
            menu.addSeparator()
            menu.addAction("🗑 삭제",   lambda: self._delete_session(data))
        elif data and data.get("type") == "group":
            menu.addAction("⊕ 세션 추가", self._new_session)
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def _on_session_double_click(self, item, col):
        data = item.data(0, Qt.UserRole)
        if data and data.get("type") == "session":
            self._open_session(data)

    def _open_session(self, info: dict):
        if info.get("auth") == "password" and not info.get("password"):
            from PyQt5.QtWidgets import QInputDialog
            pw, ok = QInputDialog.getText(
                self, "비밀번호 입력",
                f"{info['username']}@{info['host']} 비밀번호:",
                QLineEdit.Password
            )
            if not ok: return
            info = {**info, "password": pw}
        term = TerminalWidget(info)
        term.status_changed.connect(self._on_status_change)
        idx  = self.tab_widget.addTab(term, f"🖥 {info['name']}")
        self.tab_widget.setCurrentIndex(idx)
        w_idx = self.tab_widget.indexOf(self.welcome)
        if w_idx >= 0:
            self.tab_widget.removeTab(w_idx)

    def _new_session(self):
        groups = [g["name"] for g in self.session_mgr.get_groups()]
        dlg = SessionDialog(self, groups=groups or ["Default"])
        if dlg.exec_() == QDialog.Accepted:
            data, group = dlg.get_data()
            if not data["name"] or not data["host"]:
                QMessageBox.warning(self, "입력 오류", "세션 이름과 호스트를 입력하세요.")
                return
            self.session_mgr.add_session(group, data)
            self._load_session_tree()

    def _edit_session(self, info: dict):
        groups = [g["name"] for g in self.session_mgr.get_groups()]
        dlg = SessionDialog(self, session=info, groups=groups)
        if dlg.exec_() == QDialog.Accepted:
            data, group = dlg.get_data()
            self.session_mgr.delete_session(info["group"], info["name"])
            self.session_mgr.add_session(group, data)
            self._load_session_tree()

    def _clone_session(self, info: dict):
        self.session_mgr.add_session(info["group"], {**info, "name": info["name"] + "_copy"})
        self._load_session_tree()

    def _delete_session(self, info: dict):
        if QMessageBox.question(
            self, "삭제", f"'{info['name']}' 세션을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.session_mgr.delete_session(info["group"], info["name"])
            self._load_session_tree()

    def _quick_connect(self):
        dlg = SessionDialog(self, groups=["Quick Connect"])
        dlg.setWindowTitle("빠른 접속")
        if dlg.exec_() == QDialog.Accepted:
            data, _ = dlg.get_data()
            if data["host"]: self._open_session(data)

    def _close_tab(self, idx: int):
        w = self.tab_widget.widget(idx)
        if isinstance(w, TerminalWidget): w.disconnect()
        self.tab_widget.removeTab(idx)
        if self.tab_widget.count() == 0:
            self.tab_widget.addTab(self.welcome, "환영합니다")
            self.tab_widget.tabBar().setTabButton(0, QTabBar.RightSide, None)

    def _close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0: self._close_tab(idx)

    def _reconnect(self):
        w = self.tab_widget.currentWidget()
        if isinstance(w, TerminalWidget):
            w.disconnect()
            info = w.info; idx = self.tab_widget.currentIndex()
            new_term = TerminalWidget(info)
            new_term.status_changed.connect(self._on_status_change)
            self.tab_widget.removeTab(idx)
            self.tab_widget.insertTab(idx, new_term, f"🖥 {info['name']}")
            self.tab_widget.setCurrentIndex(idx)

    def _open_sftp(self):
        w = self.tab_widget.currentWidget()
        if not isinstance(w, TerminalWidget):
            QMessageBox.information(self, "안내", "먼저 SSH 세션에 접속하세요.")
            return
        sftp = w.get_sftp()
        if sftp is None:
            QMessageBox.warning(self, "안내", "SSH 연결이 활성화된 세션에서만 SFTP를 사용할 수 있습니다.")
            return
        dlg = SFTPDialog(sftp, w.get_host(), self)
        dlg.exec_(); sftp.close()

    def _save_log(self):
        w = self.tab_widget.currentWidget()
        if not isinstance(w, TerminalWidget): return
        path, _ = QFileDialog.getSaveFileName(self, "로그 저장", "session.log",
                                               "텍스트 파일 (*.log *.txt)")
        if path:
            Path(path).write_text(w.output.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "완료", f"로그 저장 완료:\n{path}")

    def _toggle_sidebar(self):
        sidebar = self.splitter.widget(0)
        sidebar.setVisible(not sidebar.isVisible())

    def _toggle_local_input(self, checked: bool):
        global PREFS
        PREFS["show_local_input"] = checked
        save_prefs(PREFS)
        self._apply_prefs_to_all_tabs()

    def _on_status_change(self, msg: str, color: str):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color:{color};")

    def _show_preferences(self):
        dlg = PreferencesDialog(self)
        dlg.prefs_applied.connect(self._apply_prefs_to_all_tabs)
        dlg.exec_()

    def _apply_prefs_to_all_tabs(self):
        # 로컬 입력줄 메뉴 체크 상태 동기화
        self._local_input_action.setChecked(PREFS.get("show_local_input", False))
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, TerminalWidget):
                w.apply_prefs()

    def _show_shortcuts(self):
        QMessageBox.information(self, "단축키 안내",
            "터미널 키보드 조작\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "← / →      이전/이후 명령어 히스토리 (일반 쉘)\n"
            "← / →      커서 이동 서버 전달 (vi/less/top 등)\n"
            "↑ / ↓      서버로 전달 (vi, less, top 등)\n"
            "Enter       명령어 전송\n"
            "ESC         입력 취소 / 서버로 ESC 전송\n"
            "Backspace   한 글자 삭제\n"
            "Tab         자동완성 (서버로 전달)\n"
            "Ctrl+C      인터럽트 (SIGINT)\n"
            "Ctrl+D      EOF 전송\n"
            "Ctrl+Z      프로세스 중단 (SIGTSTP)\n"
            "Ctrl+L      화면 지우기\n"
            "Ctrl+A      줄 맨 앞으로\n"
            "Ctrl+E      줄 맨 뒤로\n"
            "Ctrl+K      커서 이후 삭제\n"
            "Ctrl+U      줄 전체 삭제\n"
            "Ctrl+W      단어 단위 삭제\n"
            "Ctrl+Shift+C  텍스트 복사\n"
            "Ctrl+Shift+V  텍스트 붙여넣기\n"
            "Page Up/Down  화면 스크롤 (로컬)\n\n"
            "메뉴 단축키\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Ctrl+N   새 세션\n"
            "Ctrl+Q   빠른 접속\n"
            "Ctrl+B   세션 패널 토글\n"
            "Ctrl+,   환경 설정"
        )

    def _show_about(self):
        QMessageBox.about(self, "PySSH Manager",
            "PySSH Manager v2.0\n\n"
            "SecureCRT 스타일 Python SSH 클라이언트\n"
            "PyQt5 + paramiko 기반\n\n"
            "• 터미널 직접 입력 (하단 입력창 없음)\n"
            "• ← / → 화살표 히스토리 탐색\n"
            "• Keep-Alive 세션 유지\n"
            "• 12가지 테마 (Monokai, Dracula 등)\n"
            "• 로컬 입력줄 옵션 (보기 메뉴)\n"
            "• SFTP 파일 관리자")

    def closeEvent(self, event):
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, TerminalWidget): w.disconnect()
        event.accept()


# ══════════════════════════════════════════════════════════════
#  엔트리 포인트
# ══════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()