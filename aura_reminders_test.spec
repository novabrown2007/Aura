# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['core\\interface\\desktopInterface\\windows\\runAuraWindows.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\icons\\aura.ico', 'assets\\icons')],
    hiddenimports=['modules.commands', 'modules.reminders'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='aura_reminders_test',
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
    icon=['assets\\icons\\aura.ico'],
)
