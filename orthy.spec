block_cipher = None

from PyInstaller.utils.hooks import collect_submodules
all_submodules = collect_submodules(".")

a = Analysis(
    ["orthy.py"],  # Replace with your main script
    pathex=["."],
    binaries=[],
    datas=[(".", ".")],  # Includes all files from the project folder
    hiddenimports=all_submodules,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="orthy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="orthy"
)