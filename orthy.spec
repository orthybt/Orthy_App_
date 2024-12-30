# orthy.spec

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules
import PyInstaller.__main__

a = Analysis(
    ['orthy.py'],
    pathex=['.'],
    binaries=[],
    datas=[
    (r"C:\Users\User\OneDrive\Desktop\Orthy_App-GodSpeed", "Orthy_App-GodSpeed"),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='orthy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    append_pkg=False,
    runtime_tmpdir=None,
    
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='orthy'
)
