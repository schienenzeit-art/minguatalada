# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Spec fuer Min Guata Lada
# Ausfuehren: pyinstaller anspruchssystem.spec  (oder build.bat)

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
PROJECT_ROOT = Path(SPECPATH)

# bcrypt: Rust/C-Extension vollstaendig einsammeln
bcrypt_binaries, bcrypt_datas, bcrypt_hiddenimports = collect_all('bcrypt')

# reportlab: interne Modul-Referenzen sicherstellen
reportlab_hiddenimports = collect_submodules('reportlab')
reportlab_datas = collect_data_files('reportlab')

# openpyxl: Templates und Submodule
openpyxl_datas = collect_data_files('openpyxl')
openpyxl_hiddenimports = collect_submodules('openpyxl')

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=bcrypt_binaries,
    datas=[
        ('ui/styles/theme.qss', 'ui/styles'),
        ('assets', 'assets'),
    ] + bcrypt_datas + reportlab_datas + openpyxl_datas,
    hiddenimports=[
        # ── PyQt6 ──────────────────────────────────────────────────────────────
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.sip',
        # ── app/ ───────────────────────────────────────────────────────────────
        'app.bootstrap',
        'app.config',
        'app.container',
        'app.ports',
        'app.session',
        'app.app_registry',
        # ── core/ ──────────────────────────────────────────────────────────────
        'core.session',
        'core.constants',
        'core.claim_status',
        'core.card_status',
        'core.document_status',
        'core.task_status',
        'core.task_priority',
        'core.task_type',
        'core.task_source_type',
        # ── database/ ──────────────────────────────────────────────────────────
        'database.db',
        'database.repositories.category_repository',
        'database.repositories.income_repository',
        'database.repositories.expense_repository',
        'database.repositories.role_repository',
        'database.repositories.location_repository',
        'database.repositories.setting_repository',
        'database.repositories.task_repository',
        'database.repositories.document_type_repository',
        'database.repositories.document_repository',
        'database.repositories.user_repository',
        'database.repositories.case_repository',
        'database.repositories.claim_note_repository',
        'database.repositories.filter_preset_repository',
        'database.repositories.card_repository',
        'database.repositories.claim_repository',
        'database.repositories.person_repository',
        'database.repositories.mandant_repository',
        'database.repositories.notification_repository',
        'database.repositories.appointment_repository',
        'database.repositories.archive_repository',
        'database.repositories.person_note_repository',
        'database.repositories.audit_repository',
        'database.repositories.approval_repository',
        'database.repositories.checklist_repository',
        'database.repositories.document_template_repository',
        # ── services/ ──────────────────────────────────────────────────────────
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
        'services.category_service',
        'services.mandant_service',
        'services.notification_service',
        'services.appointment_service',
        'services.archive_service',
        'services.person_note_service',
        'services.audit_service',
        'services.approval_service',
        'services.checklist_service',
        'services.document_template_service',
        # ── ui/components/ ─────────────────────────────────────────────────────
        'ui.components.page_header',
        'ui.components.topbar',
        'ui.components.sidebar',
        'ui.components.app_card',
        'ui.components.app_tile',
        'ui.components.app_navigation',
        'ui.components.action_button',
        'ui.components.empty_state',
        'ui.components.card_container',
        'ui.components.table_widget',
        'ui.components.stat_card',
        'ui.components.checklist_widget',
        # ── ui/pages/ ──────────────────────────────────────────────────────────
        'ui.pages.dashboard.dashboard_page',
        'ui.pages.dashboard.app_launcher',
        'ui.pages.claims.claims_page',
        'ui.pages.tasks.tasks_page',
        'ui.pages.tasks.task_dialog',
        'ui.pages.users.users_page',
        'ui.pages.documents.documents_page',
        'ui.pages.documents.document_dialog',
        'ui.pages.locations.locations_page',
        'ui.pages.settings.settings_page',
        'ui.pages.apps.anspruchspruefung_app_page',
        'ui.pages.apps.administration_app_page',
        'ui.pages.mandants.mandants_page',
        'ui.pages.appointments.appointments_page',
        'ui.pages.claims_page',
        'ui.pages.case_create_page',
        'ui.pages.claim_detail_page',
        'ui.pages.claim_evaluation_dialog',
        'ui.pages.cards_page',
        'ui.pages.reports_page',
        'ui.pages.user_management',
        'ui.pages.role_management',
        'ui.pages.person_dossier_page',
        'ui.pages.person_dossier_dialog',
        'ui.pages.import_page',
        'ui.pages.archive_rules_page',
        'ui.pages.audit_log_page',
        'ui.pages.approval_page',
        'ui.pages.checklist_templates_page',
        'ui.pages.document_templates_page',
        # ── ui/login + shell ───────────────────────────────────────────────────
        'ui.login.login_window',
        'ui.shell.main_window',
        'ui.shell.workspace_host',
        'ui.navigation.navigation_controller',
        # ── ui/dialogs ─────────────────────────────────────────────────────────
        'ui.dialogs.user_dialog',
        'ui.dialogs.force_password_dialog',
        'ui.dialogs.search_result_dialog',
    ] + bcrypt_hiddenimports + reportlab_hiddenimports + openpyxl_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'uvicorn',
        'fastapi',
        'PyJWT',
        'pytest',
        'tkinter',
        '_tkinter',
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
    name='MinGuataLada',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MinGuataLada',
)
