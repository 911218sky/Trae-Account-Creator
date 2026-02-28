# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Exclude unnecessary modules to reduce size
excludes = [
    # GUI frameworks
    'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx',
    # Scientific libraries
    'numpy', 'scipy', 'pandas', 'matplotlib', 'PIL', 'cv2',
    # Development tools
    'pytest', 'unittest', 'doctest', 'pdb', 'IPython',
    # Other unused modules
    'sqlite3', 'xml', 'xmlrpc', 'pydoc', 'difflib',
]

a = Analysis(
    ['register.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),  # Include src package
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
