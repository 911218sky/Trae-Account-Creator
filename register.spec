# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Exclude unnecessary modules to reduce size
# Removed PIL from excludes as it is used by gui.py
excludes = [
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
    'numpy', 'scipy', 'pandas', 'matplotlib', 'cv2',
    'pytest', 'unittest', 'doctest', 'pdb', 'IPython',
    'sqlite3', 'xml', 'xmlrpc', 'pydoc', 'difflib',
]

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),  # Include src package
        ('assets', 'assets'),  # Include assets
    ],
    hiddenimports=[
        'src',
        'src.mail_client',
        'src.config',
        'src.connection',
        'src.parser',
        'src.exceptions',
        'src.constants',
        'src.logger',
        'PIL',
        'PIL._tkinter_finder',
        'ttkbootstrap',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='TraeAccountCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app.ico',
)
