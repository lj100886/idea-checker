"""图形化配置界面：LLM / 搜索源 key 配置 + 平台申请快链

用法：
  - 独立入口：config-ui.exe  （无黑框，双击即开）
  - 组合入口：idea-checker.exe --config-ui

特点：
  - 自带配置读写，不依赖 src.config，避免冻结包里的相对导入问题
  - 任何启动异常都会弹窗显示，不会“双击没反应”地静默失败
  - LLM 区：base_url / api_key / model（必填 api_key 才能跑）
  - 搜索源区：github token / tavily api_key / aihot endpoint + 启用勾选
  - 每个平台名都是可点击按钮，直接跳转到申请/注册地址
  - 保存写入 ~/.idea-checker/config.json；测试连接验证 key 是否可用
"""
import os
import sys
import json
import webbrowser
import threading
from pathlib import Path
from typing import Optional


# 平台申请 / 注册地址（点击平台名即跳转）
LLM_PLATFORMS = {
    "SiliconFlow 硅基流动": "https://cloud.siliconflow.cn/",
    "智谱 BigModel": "https://bigmodel.cn/",
    "DeepSeek": "https://platform.deepseek.com/",
    "火山方舟 Ark": "https://console.volcengine.com/ark",
}
SEARCH_PLATFORMS = {
    "GitHub Token": "https://github.com/settings/tokens",
    "Tavily": "https://tavily.com/",
    "aihot": "https://aihot.virxact.com/",
}

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen3-8B"
DEFAULT_AIHOT = "https://aihot.virxact.com/api/mcp?aihot_actor=YOUR_AIHOT_ACTOR_TOKEN"


def _default_config_path() -> Path:
    return Path.home() / ".idea-checker" / "config.json"


def _load_raw(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_raw(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _open_link(url: str):
    """打开外链 / 目录（Windows 用 os.startfile，跨平台退回 webbrowser）"""
    try:
        if url.startswith("http://") or url.startswith("https://"):
            webbrowser.open(url)
        else:
            if sys.platform == "win32":
                os.startfile(url)
            else:
                webbrowser.open(Path(url).as_uri())
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass


def _link_button(name: str, url: str):
    from PyQt6.QtWidgets import QPushButton
    b = QPushButton(name)
    b.setStyleSheet("QPushButton{color:#1565c0;text-align:left;border:none;"
                   "text-decoration:underline;background:transparent}"
                   "QPushButton:hover{color:#0d47a1}")
    b.clicked.connect(lambda _=False, u=url: _open_link(u))
    return b


class ConfigWindow:
    def __init__(self, config_path: Optional[str] = None):
        from PyQt6.QtWidgets import (
            QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
            QGroupBox, QCheckBox, QTextEdit,
        )
        from PyQt6.QtCore import Qt, pyqtSignal

        self._sig = pyqtSignal
        self.QWidget = QWidget
        self.QLabel = QLabel
        self.QLineEdit = QLineEdit
        self.QPushButton = QPushButton
        self.QVBoxLayout = QVBoxLayout
        self.QHBoxLayout = QHBoxLayout
        self.QGroupBox = QGroupBox
        self.QCheckBox = QCheckBox
        self.QTextEdit = QTextEdit
        self.Qt = Qt
        self.pyqtSignal = pyqtSignal

        self.config_path = Path(config_path) if config_path else _default_config_path()
        self._config = _load_raw(self.config_path)
        self.test_result = pyqtSignal(str)

        self._setup_ui()
        self._load()

    # ---------- UI ----------
    def _setup_ui(self):
        self.setWindowTitle("idea-checker 配置")
        self.resize(620, 660)
        root = self.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        intro = self.QLabel("配置 LLM（必填）与搜索源（可选）。保存后双击 idea-checker.exe 即可使用。")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#607d8b")
        root.addWidget(intro)

        # ===== LLM 区 =====
        llm = self.QGroupBox("① LLM API（必填，生成报告用）")
        lv = self.QVBoxLayout(llm)
        lv.setSpacing(8)
        lv.addWidget(self._field("API 地址 base_url", "base_url", DEFAULT_BASE_URL))
        lv.addWidget(self._field("API Key", "api_key", "", password=True))
        lv.addWidget(self._field("模型 model", "model", DEFAULT_MODEL))
        link_row = self.QHBoxLayout()
        link_row.addWidget(self.QLabel("申请地址："))
        for name, url in LLM_PLATFORMS.items():
            link_row.addWidget(_link_button(name, url))
        link_row.addStretch()
        lv.addLayout(link_row)
        root.addWidget(llm)

        # ===== 搜索源区 =====
        sbox = self.QGroupBox("② 搜索源（可选，提升搜索质量 / 限额）")
        sv = self.QVBoxLayout(sbox)
        sv.setSpacing(8)

        src_row = self.QHBoxLayout()
        src_row.addWidget(self.QLabel("启用："))
        self.cb_github = self.QCheckBox("GitHub")
        self.cb_aihot = self.QCheckBox("aihot")
        self.cb_tavily = self.QCheckBox("Tavily")
        src_row.addWidget(self.cb_github)
        src_row.addWidget(self.cb_aihot)
        src_row.addWidget(self.cb_tavily)
        src_row.addStretch()
        sv.addLayout(src_row)

        sv.addWidget(self._field("GitHub Token", "github_token", "", password=True))
        sv.addWidget(self._field("Tavily API Key", "tavily_key", "", password=True))
        sv.addWidget(self._field("aihot Endpoint", "aihot_endpoint", DEFAULT_AIHOT))
        slink = self.QHBoxLayout()
        slink.addWidget(self.QLabel("申请地址："))
        for name, url in SEARCH_PLATFORMS.items():
            slink.addWidget(_link_button(name, url))
        slink.addStretch()
        sv.addLayout(slink)
        root.addWidget(sbox)

        # ===== 按钮区 =====
        btn = self.QHBoxLayout()
        self.save_btn = self.QPushButton("保存配置")
        self.test_btn = self.QPushButton("测试连接")
        self.dir_btn = self.QPushButton("打开配置目录")
        self.close_btn = self.QPushButton("关闭")
        for b in (self.save_btn, self.test_btn, self.dir_btn, self.close_btn):
            b.setMinimumHeight(34)
        self.save_btn.setStyleSheet("QPushButton{background:#2e7d32;color:white;border-radius:6px}"
                                    "QPushButton:hover{background:#1b5e20}")
        self.test_btn.setStyleSheet("QPushButton{background:#1565c0;color:white;border-radius:6px}"
                                    "QPushButton:hover{background:#0d47a1}")
        self.save_btn.clicked.connect(self._save)
        self.test_btn.clicked.connect(self._test)
        self.dir_btn.clicked.connect(self._open_dir)
        self.close_btn.clicked.connect(self.close)
        btn.addWidget(self.save_btn)
        btn.addWidget(self.test_btn)
        btn.addWidget(self.dir_btn)
        btn.addStretch()
        btn.addWidget(self.close_btn)
        root.addLayout(btn)

        # ===== 状态区 =====
        self.status = self.QTextEdit()
        self.status.setReadOnly(True)
        self.status.setFixedHeight(90)
        self.status.setPlaceholderText("操作结果会显示在这里…")
        root.addWidget(self.status)

    def _field(self, label: str, attr: str, placeholder: str, password: bool = False):
        from PyQt6.QtWidgets import QLineEdit
        row = self.QHBoxLayout()
        lab = self.QLabel(label)
        lab.setFixedWidth(120)
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        if password:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
        setattr(self, attr, inp)
        row.addWidget(lab)
        row.addWidget(inp)
        return row

    # ---------- 数据 ----------
    def _load(self):
        d = self._config
        llm = d.get("llm", {}).get("api", {})
        self.base_url.setText(llm.get("base_url", DEFAULT_BASE_URL))
        self.api_key.setText(llm.get("api_key", ""))
        self.model.setText(llm.get("model", DEFAULT_MODEL))
        sources = d.get("search", {}).get("sources", [])
        self.cb_github.setChecked("github" in sources)
        self.cb_aihot.setChecked("aihot" in sources)
        self.cb_tavily.setChecked("tavily" in sources)
        s = d.get("search", {})
        self.github_token.setText(s.get("github", {}).get("token", ""))
        self.tavily_key.setText(s.get("tavily", {}).get("api_key", ""))
        self.aihot_endpoint.setText(s.get("aihot", {}).get("endpoint", DEFAULT_AIHOT))
        self._status(f"已加载配置：{self.config_path}")

    def _collect(self) -> dict:
        d = self._config
        d.setdefault("llm", {}).setdefault("api", {})
        d["llm"]["api"]["base_url"] = self.base_url.text().strip() or DEFAULT_BASE_URL
        d["llm"]["api"]["api_key"] = self.api_key.text().strip()
        d["llm"]["api"]["model"] = self.model.text().strip() or DEFAULT_MODEL
        srcs = []
        if self.cb_github.isChecked():
            srcs.append("github")
        if self.cb_aihot.isChecked():
            srcs.append("aihot")
        if self.cb_tavily.isChecked():
            srcs.append("tavily")
        d.setdefault("search", {})["sources"] = srcs
        d["search"].setdefault("github", {})["token"] = self.github_token.text().strip()
        d["search"].setdefault("tavily", {})["api_key"] = self.tavily_key.text().strip()
        d["search"].setdefault("aihot", {})["endpoint"] = self.aihot_endpoint.text().strip() or DEFAULT_AIHOT
        return d

    def _save(self):
        d = self._collect()
        try:
            _save_raw(self.config_path, d)
            self._status(f"✅ 已保存到：{self.config_path}")
        except Exception as e:
            self._status(f"❌ 保存失败：{e}")

    def _open_dir(self):
        d = self.config_path.parent
        try:
            d.mkdir(parents=True, exist_ok=True)
            _open_link(str(d))
            self._status(f"📂 配置目录：{d}")
        except Exception as e:
            self._status(f"❌ 打开目录失败：{e}")

    def _test(self):
        base_url = self.base_url.text().strip()
        api_key = self.api_key.text().strip()
        model = self.model.text().strip() or DEFAULT_MODEL
        if not api_key:
            self._status("⚠️ 请先填写 API Key 再测试")
            return
        self._status("⏳ 正在测试连接…")
        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
        except Exception:
            pass

        def worker():
            try:
                import requests
                url = base_url.rstrip("/") + "/chat/completions"
                resp = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 16},
                    timeout=20,
                )
                if resp.status_code == 200:
                    self.test_result.emit(f"✅ 连接成功（{model} 可用）")
                else:
                    self.test_result.emit(f"⚠️ HTTP {resp.status_code}：{resp.text[:200]}")
            except Exception as e:
                self.test_result.emit(f"❌ 连接失败：{e}")

        threading.Thread(target=worker, daemon=True).start()

    def _status(self, msg: str):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.status.append(f"[{ts}] {msg}")


def run_config_ui(config_path: Optional[str] = None):
    """入口：启动配置窗口。任何异常都弹窗显示，绝不静默失败。"""
    try:
        # 独立 GUI 入口为 GUI 子系统（无控制台）；组合入口是 CONSOLE，这里尽量隐藏黑框
        try:
            import ctypes
            whnd = ctypes.windll.kernel32.GetConsoleWindow()
            if whnd != 0:
                ctypes.windll.user32.ShowWindow(whnd, 0)
        except Exception:
            pass

        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication(sys.argv)
        win = ConfigWindow(config_path)
        win.show()
        win.raise_()
        win.activateWindow()
        # 居中到屏幕可用区域，避免跑到屏外
        try:
            screen = win.screen()
            if screen is not None:
                rect = screen.availableGeometry()
                win.move(rect.center().x() - win.width() // 2,
                         rect.center().y() - win.height() // 2)
        except Exception:
            pass
        win.test_result.connect(win._status)
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "idea-checker 配置启动失败", tb)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    run_config_ui()
