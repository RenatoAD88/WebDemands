# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

crypt = collect_all('cryptography')
crypt_datas = crypt.datas if hasattr(crypt, 'datas') else crypt[0]
crypt_binaries = crypt.binaries if hasattr(crypt, 'binaries') else crypt[1]
crypt_hiddenimports = crypt.hiddenimports if hasattr(crypt, 'hiddenimports') else crypt[2]

cert = collect_all('certifi')
cert_datas = cert.datas if hasattr(cert, 'datas') else cert[0]
cert_binaries = cert.binaries if hasattr(cert, 'binaries') else cert[1]
cert_hiddenimports = cert.hiddenimports if hasattr(cert, 'hiddenimports') else cert[2]

datas = []
binaries = []
hiddenimports = [
    'huggingface_hub',
    'requests',
    'bcrypt',
    'mydemands.resources_rc',
]

datas += crypt_datas
binaries += crypt_binaries
hiddenimports += crypt_hiddenimports
datas += cert_datas
binaries += cert_binaries
hiddenimports += cert_hiddenimports
hiddenimports += [
    'cryptography.hazmat.primitives.ciphers.aead',
    'cryptography.hazmat.bindings._rust',
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
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
    name='DemandasApp',
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
)
