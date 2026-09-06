"""桌面宠物主窗口：透明、置顶、动画、点击弹出审查面板、自动监控新项目"""
import sys
import json
import threading
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QSystemTrayIcon, QMenu, QListWidget, QSpinBox, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, QTransform, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QAction, QColor, QImage

from ..config import Config
from ..core.orchestrator import Orchestrator
from ..core.report_generator import ReportGenerator
from ..models import Report
from .tts import get_tts


class ReviewSignal(QObject):
    new_report = pyqtSignal(object)


class PetWindow(QWidget):
    def __init__(self, config: Optional[Config] = None):
        super().__init__()
        self.config = config or Config()
        self.orchestrator = Orchestrator(self.config)
        self.review_panel = None
        self._frames: List[QPixmap] = []
        self._current_frame = 0
        self._file_watcher = None
        self._signal = ReviewSignal()
        self._signal.new_report.connect(self._on_auto_review)
        self._speaking = False
        self._idle_frames: List[QPixmap] = []
        self._talk_frames: List[QPixmap] = []
        self._blink_counter = 0
        self._next_blink = 150
        self._blink_phase = 0
        self._breath_phase = 0.0
        self._tilt_angle = 0.0
        self._tilt_target = 0.0
        self._hover = False
        self._excited = 0
        self._action_timer = 0
        tts_voice = self.config.get("triggers.desktop_pet.tts_voice", "xiaoyi")
        tts_enabled = self.config.get("triggers.desktop_pet.tts_enabled", True)
        self.tts = get_tts(voice=tts_voice, enabled=tts_enabled)
        self._setup_window()
        self._setup_pet()
        self._setup_tray()
        self._start_swing_animation()
        self._start_file_watcher()

    def _setup_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(200, 220)

    def _setup_pet(self):
        self.pet_label = QLabel(self)
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pet_label.setGeometry(0, 0, 200, 220)
        frames_dir = self.config.get("triggers.desktop_pet.frames_dir", "")
        if not frames_dir:
            frames_dir = str(Path(__file__).parent.parent.parent / "assets" / "pets" / "custom")
        self._load_multi_frames(Path(frames_dir))
        if not self._frames and not self._idle_frames:
            image_path = self.config.get("triggers.desktop_pet.image_path", "")
            if image_path and Path(image_path).exists():
                pixmap = QPixmap(image_path).scaled(170, 190, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._frames = [pixmap]
        if not self._frames and not self._idle_frames:
            self._frames = [self._create_default_pet()]
        if self._idle_frames:
            self.pet_label.setPixmap(self._idle_frames[0])
        elif self._frames:
            self.pet_label.setPixmap(self._frames[0])

    def _load_multi_frames(self, frames_dir: Path):
        if not frames_dir.exists():
            return
        target_w, target_h = 170, 190
        def load_frame(name):
            p = frames_dir / name
            if p.exists():
                return QPixmap(str(p)).scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return None
        idle = load_frame("idle.png")
        blink = load_frame("blink.png")
        talk1 = load_frame("talk1.png")
        talk2 = load_frame("talk2.png")
        if idle:
            self._idle_frames = [idle]
            if blink:
                self._idle_frames.append(blink)
            self._frames = [idle]
        if talk1 and talk2:
            self._talk_frames = [talk1, talk2]

    def _create_default_pet(self) -> QPixmap:
        pixmap = QPixmap(100, 120)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 165, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(15, 30, 70, 80, 20, 20)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(28, 50, 15, 20)
        painter.drawEllipse(57, 50, 15, 20)
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawEllipse(33, 57, 6, 8)
        painter.drawEllipse(62, 57, 6, 8)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawArc(35, 75, 30, 15, 0, -180 * 16)
        painter.setPen(QColor(255, 165, 0))
        painter.drawLine(50, 30, 50, 15)
        painter.setBrush(Qt.GlobalColor.red)
        painter.drawEllipse(45, 8, 10, 10)
        painter.end()
        return pixmap

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        if self._frames:
            self.tray.setIcon(QIcon(self._frames[0]))
        self.tray.setToolTip("idea-checker 选题审查")
        menu = QMenu()
        show_action = QAction("显示宠物", self)
        show_action.triggered.connect(self.show)
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._show_settings)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _start_swing_animation(self):
        self.swing_timer = QTimer(self)
        self.swing_timer.timeout.connect(self._swing)
        speed = self.config.get("triggers.desktop_pet.swing_speed", 50)
        self.swing_timer.start(speed)

    def _swing(self):
        import math, random
        self._breath_phase += 0.03
        breath_y = math.sin(self._breath_phase) * 3
        breath_scale = 1.0 + math.sin(self._breath_phase) * 0.01
        self._action_timer += 1
        if self._action_timer > 200:
            self._action_timer = 0
            if random.random() < 0.4:
                self._tilt_target = random.uniform(-8, 8)
            else:
                self._tilt_target = 0
            if random.random() < 0.2:
                self._excited = 30
        self._tilt_angle += (self._tilt_target - self._tilt_angle) * 0.05
        if self._excited > 0:
            self._excited -= 1
            fast_swing = math.sin(self._breath_phase * 5) * 5
        else:
            fast_swing = 0
        total_angle = self._tilt_angle + fast_swing
        current_frame = None
        if self._idle_frames and not self._speaking:
            self._blink_counter += 1
            if self._blink_phase == 0:
                if self._blink_counter >= self._next_blink:
                    self._blink_phase = 1
                    self._blink_counter = 0
            elif self._blink_phase == 1:
                if self._blink_counter >= 3:
                    self._blink_phase = 2
                    self._blink_counter = 0
            elif self._blink_phase == 2:
                if self._blink_counter >= 2:
                    self._blink_phase = 0
                    self._blink_counter = 0
                    self._next_blink = random.randint(80, 250)
            if self._blink_phase == 1 and len(self._idle_frames) > 1:
                current_frame = self._idle_frames[1]
            else:
                current_frame = self._idle_frames[0]
        if self._speaking and self._talk_frames:
            self._frame_counter = getattr(self, '_frame_counter', 0) + 1
            if self._frame_counter >= 3:
                self._frame_counter = 0
                self._current_frame = (self._current_frame + 1) % len(self._talk_frames)
            current_frame = self._talk_frames[self._current_frame]
        if current_frame is None and self._frames:
            self._frame_counter = getattr(self, '_frame_counter', 0) + 1
            if self._frame_counter >= 5 and len(self._frames) > 1:
                self._frame_counter = 0
                self._current_frame = (self._current_frame + 1) % len(self._frames)
            current_frame = self._frames[self._current_frame]
        if current_frame is None:
            return
        if self._hover:
            breath_scale *= 1.1
        cx = current_frame.width() / 2
        cy = current_frame.height() / 2
        transform = QTransform()
        transform.translate(cx, cy + breath_y)
        transform.rotate(total_angle)
        transform.scale(breath_scale, breath_scale)
        transform.translate(-cx, -cy)
        transformed = current_frame.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.pet_label.setPixmap(transformed)

    def enterEvent(self, event):
        self._hover = True
        self._excited = 15

    def leaveEvent(self, event):
        self._hover = False

    def start_speaking(self):
        self._speaking = True
        self._current_frame = 0

    def stop_speaking(self):
        self._speaking = False
        self._current_frame = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._show_review_panel()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if hasattr(self, '_drag_position'):
                self.move(event.globalPosition().toPoint() - self._drag_position)

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'review_panel') and self.review_panel and self.review_panel.isVisible():
            self._position_review_panel()

    def _position_review_panel(self):
        if not self.review_panel:
            return
        pet_pos = self.pos()
        panel_width = self.review_panel.width()
        pet_width = self.width()
        x = pet_pos.x() + (pet_width - panel_width) // 2
        y = pet_pos.y() + self.height()
        self.review_panel.move(x, y)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        review_action = QAction("审查选题", self)
        review_action.triggered.connect(self._show_review_panel)
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(review_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.exec(pos)

    def _show_review_panel(self):
        if self.review_panel and self.review_panel.isVisible():
            self.review_panel.raise_()
            self.review_panel.activateWindow()
            return
        self.review_panel = ReviewPanel(self.orchestrator, self.config, pet=self, parent=self)
        self._position_review_panel()
        self.review_panel.show()

    def _show_settings(self):
        if hasattr(self, '_settings_dialog') and self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        self._settings_dialog = SettingsDialog(self.config, pet=self, parent=self)
        pet_pos = self.pos()
        panel_width = 420
        x = pet_pos.x() + (self.width() - panel_width) // 2
        y = pet_pos.y() + self.height() + 10
        self._settings_dialog.move(x, y)
        self._settings_dialog.show()

    def _restart_file_watcher(self):
        if self._file_watcher:
            self._file_watcher.stop()
            self._file_watcher = None
        self._start_file_watcher(skip_llm_discover=True)

    def _start_file_watcher(self, skip_llm_discover: bool = False):
        enabled = self.config.get("triggers.file_watcher.enabled", True)
        if not enabled:
            return
        try:
            from ..triggers.file_watcher import FileWatcherTrigger
            def on_review(report: Report):
                self._signal.new_report.emit(report)
            self._file_watcher = FileWatcherTrigger(self.config, on_review=on_review, skip_llm_discover=skip_llm_discover)
            if self._file_watcher.watch_dirs:
                interval = self.config.get("triggers.file_watcher.scan_interval", 5)
                watch_thread = threading.Thread(target=self._file_watcher.start, args=(interval,), daemon=True)
                watch_thread.start()
        except Exception as e:
            print(f"文件监控启动失败: {e}")

    def _on_auto_review(self, report: Report):
        self._show_review_panel()
        if self.review_panel:
            self.review_panel.input_edit.setText(report.idea)
            self.review_panel.result_edit.setText(ReportGenerator.to_text(report))
        if hasattr(self, 'tray') and self.tray:
            self.tray.showMessage("检测到新项目！", f"自动审查完成：{report.rating.value}", QSystemTrayIcon.MessageIcon.Information, 5000)
        rating_text = report.rating.value if hasattr(report.rating, 'value') else str(report.rating)
        self.tts.speak(f"检测到新项目，自动审查完成。评级：{rating_text}。{report.conclusion[:80]}")


class ReviewPanel(QWidget):
    def __init__(self, orchestrator: Orchestrator, config: Config, pet=None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.config = config
        self.pet = pet
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 500)
        container = QWidget(self)
        container.setGeometry(0, 0, 400, 500)
        container.setStyleSheet("QWidget{background-color:rgba(40,40,50,240);border-radius:15px;color:white;font-size:14px}QTextEdit{background-color:rgba(60,60,70,200);border:1px solid rgba(100,100,120,150);border-radius:8px;padding:8px}QPushButton{background-color:#00bcd4;border:none;border-radius:8px;padding:10px;font-weight:bold;color:white}QPushButton:hover{background-color:#00acc1}QLabel{color:#b0bec5}")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("选题审查")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:white")
        layout.addWidget(title)
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入你的想法/项目描述...")
        self.input_edit.setFixedHeight(80)
        layout.addWidget(self.input_edit)
        btn_layout = QHBoxLayout()
        self.review_btn = QPushButton("开始审查")
        self.review_btn.clicked.connect(self._do_review)
        btn_layout.addWidget(self.review_btn)
        self.close_btn = QPushButton("X")
        self.close_btn.setFixedWidth(40)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("审查结果会显示在这里...")
        layout.addWidget(self.result_edit)

    def _do_review(self):
        idea = self.input_edit.toPlainText().strip()
        if not idea:
            self.result_edit.setText("请输入想法！")
            return
        self.review_btn.setEnabled(False)
        self.review_btn.setText("审查中...")
        self.result_edit.setText("正在联网搜索和分析，请稍候...")
        if self.pet:
            self.pet.start_speaking()
            self.pet.tts.speak("开始审查")
        QApplication.processEvents()
        try:
            persona = self.config.get("persona", "default")
            report = self.orchestrator.check_idea(idea, persona)
            self.result_edit.setText(ReportGenerator.to_text(report))
            if self.pet:
                rating_text = report.rating.value if hasattr(report.rating, 'value') else str(report.rating)
                self.pet.tts.speak(f"审查完成。评级：{rating_text}。{report.conclusion[:100]}")
        except Exception as e:
            self.result_edit.setText(f"审查失败: {str(e)}")
        finally:
            self.review_btn.setEnabled(True)
            self.review_btn.setText("开始审查")
            if self.pet:
                self.pet.stop_speaking()


class SettingsDialog(QWidget):
    def __init__(self, config: Config, pet=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.pet = pet
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 400)
        container = QWidget(self)
        container.setGeometry(0, 0, 420, 400)
        container.setStyleSheet("QWidget{background-color:rgba(40,40,50,245);border-radius:15px;color:white;font-size:13px}QLabel{background:transparent}QListWidget{background-color:rgba(60,60,70,200);border:1px solid rgba(100,100,120,150);border-radius:8px;padding:5px}QPushButton{background-color:rgba(80,120,200,220);border:none;border-radius:6px;padding:6px 14px;color:white;font-weight:bold}QPushButton:hover{background-color:rgba(100,140,220,240)}QSpinBox{background-color:rgba(60,60,70,200);border:1px solid rgba(100,100,120,150);border-radius:6px;padding:4px;color:white}")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel("设置")
        title.setStyleSheet("font-size:18px;font-weight:bold")
        layout.addWidget(title)
        layout.addWidget(QLabel("监控目录："))
        self.dir_list = QListWidget()
        self.dir_list.setFixedHeight(150)
        layout.addWidget(self.dir_list)
        dir_btns = QHBoxLayout()
        add_btn = QPushButton("添加目录")
        add_btn.clicked.connect(self._add_dir)
        remove_btn = QPushButton("删除选中")
        remove_btn.clicked.connect(self._remove_dir)
        dir_btns.addWidget(add_btn)
        dir_btns.addWidget(remove_btn)
        dir_btns.addStretch()
        layout.addLayout(dir_btns)
        scan_layout = QHBoxLayout()
        scan_layout.addWidget(QLabel("扫描间隔（秒）："))
        self.scan_spin = QSpinBox()
        self.scan_spin.setRange(1, 300)
        self.scan_spin.setValue(5)
        scan_layout.addWidget(self.scan_spin)
        scan_layout.addStretch()
        layout.addLayout(scan_layout)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _load_settings(self):
        watch_dirs = self.config.get("triggers.file_watcher.watch_dirs", [])
        for d in watch_dirs:
            self.dir_list.addItem(d)
        interval = self.config.get("triggers.file_watcher.scan_interval", 5)
        self.scan_spin.setValue(interval)

    def _add_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择要监控的目录")
        if dir_path:
            for i in range(self.dir_list.count()):
                if self.dir_list.item(i).text() == dir_path:
                    return
            self.dir_list.addItem(dir_path)

    def _remove_dir(self):
        for item in self.dir_list.selectedItems():
            self.dir_list.takeItem(self.dir_list.row(item))

    def _save(self):
        watch_dirs = [self.dir_list.item(i).text() for i in range(self.dir_list.count())]
        interval = self.scan_spin.value()
        self.config.set("triggers.file_watcher.watch_dirs", watch_dirs)
        self.config.set("triggers.file_watcher.scan_interval", interval)
        self.config.save()
        if self.pet and hasattr(self.pet, '_restart_file_watcher'):
            self.pet._restart_file_watcher()
        if hasattr(self.pet, 'tray') and self.pet.tray:
            self.pet.tray.showMessage("设置已保存", f"监控{len(watch_dirs)}个目录，间隔{interval}秒", QSystemTrayIcon.MessageIcon.Information, 3000)
        self.close()


def run_desktop_pet(config_path: Optional[str] = None):
    try:
        import ctypes
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    config = Config(config_path)
    pet = PetWindow(config)
    screen = app.primaryScreen().geometry()
    pet.move(screen.width() // 2 - 100, screen.height() // 2 - 110)
    pet.show()
    pet.raise_()
    pet.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_desktop_pet()
