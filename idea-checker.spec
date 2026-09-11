# -*- mode: python ; coding: utf-8 -*-
"""idea-checker 打包配置"""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集数据文件
datas = [
    ('config/personas', 'config/personas'),
    ('config/prompts', 'config/prompts'),
    ('assets/pets', 'assets/pets'),
]

# 收集PyQt6的所有文件（binaries/datas/hiddenimports）
from PyInstaller.utils.hooks import collect_all
pyqt6_datas, pyqt6_binaries, pyqt6_hidden = collect_all('PyQt6')
datas += pyqt6_datas
binaries = pyqt6_binaries

# 隐藏导入（一些动态导入的模块）
hiddenimports = [
    'mcp',
    'mcp.server',
    'mcp.server.fastmcp',
    'edge_tts',
    'watchdog',
    'watchdog.observers',
    'ddgs',
    'yaml',
    'PIL',
    'PIL.Image',
] + pyqt6_hidden

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='idea-checker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 需要控制台：CLI/交互模式依赖 stdin/stdout/stderr（无控制台会导致 lost sys.stderr）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
