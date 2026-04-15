# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Stdytime v04.05.16

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('assets', 'assets'),
        ('data', 'data'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'reportlab',
        'sqlite3',
        'modules.database',
        'modules.student_manager',
        'modules.timer_manager',
        'modules.qr_generator',
        'modules.assistant_manager',
        'modules.reports',
        'modules.utils',
        'routes.dashboard',
        'routes.students',
        'routes.assistants',
        'routes.api',
        'routes.qr',
        'routes.reports',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    name='Stdytime_v04.05.16',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
