# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Hostinger VPS Manager.

One unified spec that builds:
  Windows -> dist/HostingerVPSManager.exe
  Linux   -> dist/HostingerVPSManager (single-file binary)
  macOS   -> dist/HostingerVPSManager.app (proper .app bundle)
"""

import sys

IS_WINDOWS = sys.platform.startswith('win')
IS_MAC = sys.platform == 'darwin'

# Windows-only hidden imports. On Linux/macOS these modules don't exist
# and including them generates a harmless warning, but it's cleaner to
# scope them to the platform that needs them.
hiddenimports = []
if IS_WINDOWS:
    hiddenimports = ['keyring.backends.Windows', 'win32timezone']

# Icon: PyInstaller accepts .ico on Windows and .png/.icns on macOS.
# We ship a .png in assets/ that PyInstaller converts on macOS.
icon = 'assets/hostinger.ico' if IS_WINDOWS else 'assets/hostinger.png'

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=hiddenimports,
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
    name='HostingerVPSManager',
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
    icon=icon,
)

# On macOS wrap the binary in a proper .app bundle so users get a
# double-clickable, dock-friendly artefact instead of a CLI binary.
if IS_MAC:
    app = BUNDLE(
        exe,
        name='HostingerVPSManager.app',
        icon=icon,
        bundle_identifier='com.geva.hostinger-vps-manager',
        info_plist={
            'CFBundleDisplayName': 'Hostinger VPS Manager',
            'CFBundleShortVersionString': '1.3.1',
            'CFBundleVersion': '1.3.1',
            'NSHighResolutionCapable': True,
            # Keep the app Gatekeeper-tolerant when unsigned: users will
            # still need right-click -> Open the first time.
            'LSApplicationCategoryType': 'public.app-category.developer-tools',
            'NSHumanReadableCopyright': 'Copyright (c) Amos Geva. GPLv3.',
        },
    )
