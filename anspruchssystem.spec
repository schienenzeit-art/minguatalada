# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Spec fuer Anspruchssystem
# Ausfuehren: pyinstaller anspruchssystem.spec

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
PROJECT_ROOT = Path(SPECPATH)

# bcrypt: C-Extension vollstaendig einsammeln (Binaries + Data + hiddenimports)
bcrypt_binaries, bcrypt_datas, bcrypt_hiddenimports = collect_all('bcrypt')

# reportlab: interne Module sicherstellen
reportlab_hiddenimports = collect_submodules('reportlab')

# openpyxl: interne Module sicherstellen
openpyxl_datas = collect_data_files('openpyxl')
openpyxl_hiddenimports = collect_submodules('openpyxl')

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[] + bcrypt_binaries,
    datas=[
        # QSS Stylesheet - wird zur Laufzeit ueber RESOURCE_DIR gefunden
        ('ui/styles/theme.qss', 'ui/styles'),
    ] + bcrypt_datas + openpyxl_datas,
    hiddenimports=[
        # PyQt6
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.sip',
        # Alle App-Module explizit - sichert dynamisch geladene Seiten ab
        'app.bootstrap',
        'app.config',
        'app.container',
        'app.ports',
        'core.claim_status',
        'core.card_status',
        'core.document_status',
        'core.task_status',
        'core.task_priority',
        'core.task_type',
        'core.session',
        'database.db',
        'services.auth_service',
        'services.claim_service',
        'services.card_service',
        'services.case_service',
        'services.person_service',
        'services.document_service',
        'services.location_service',
        'services.user_service',
        'services.role_service',
        'services.task_service',
        'services.pdf_service',
        'services.report_service',
        'services.excel_service',
        'services.search_service',
        'services.filter_preset_service',
        'services.dashboard_service',
        'services.settings_service',
        'services.pruefung_service',
        'services.password_service',
    ] + bcrypt_hiddenimports + reportlab_hiddenimports + openpyxl_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # FastAPI/Uvicorn werden in der GUI-App nicht benoetigt
        'uvicorn',
        'fastapi',
        'PyJWT',
        # Test-Dependencies
        'pytest',
        # Unnoetige stdlib-Module
        'tkinter',
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
    [],
    exclude_binaries=True,
    name='Anspruchssystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Kein Konsolenfenster
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # .ico-Datei im Projektstamm ablegen fuer App-Icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Anspruchssystem',
)
