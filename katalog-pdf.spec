# -*- mode: python ; coding: utf-8 -*-
#
# katalog-pdf.spec
# =================
# Konfigurasi PyInstaller untuk membungkus Katalog PDF jadi satu file .exe
# standalone (tidak butuh Python/conda terinstall di komputer pemakainya).
#
# Cara pakai (jalankan di terminal Windows, di dalam environment pdf-katalog):
#     pip install "katalog-pdf[build,ocr]"
#     pyinstaller katalog-pdf.spec
#
# Hasilnya akan ada di folder dist/KatalogPDF.exe
#
# CATATAN soal OCR & lisensi: pytesseract dan pdf2image (baris di bawah)
# BOLEH dibungkus ke .exe -- keduanya berlisensi permisif (Apache 2.0 / MIT).
# Tapi program Tesseract dan Poppler sendiri SENGAJA TIDAK dibungkus ke .exe
# ini (Poppler berlisensi GPL) -- pemakai .exe tetap harus install Tesseract
# (installer .exe biasa) dan Poppler (extract .zip) secara terpisah di
# komputernya sendiri. Lihat tab Panduan di app untuk instruksinya.
#
# CATATAN LAIN: proses bundling Streamlit+PyInstaller kadang butuh 1-2 kali
# percobaan -- kalau muncul error "PackageNotFoundError" atau semacamnya yang
# menyebut nama library tertentu, biasanya cukup ditambahkan lewat
# copy_metadata('nama-library') di bawah, lalu jalankan ulang.

from PyInstaller.utils.hooks import collect_all, copy_metadata

datas = [('katalog_pdf', 'katalog_pdf')]
binaries = []
hiddenimports = []

for pkg in ('streamlit', 'pypdf', 'openpyxl', 'pandas', 'tabulate', 'odf'):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# Streamlit mengecek versinya sendiri lewat importlib.metadata saat start --
# tanpa ini biasanya muncul error "PackageNotFoundError: streamlit"
datas += copy_metadata('streamlit')

# pytesseract & pdf2image OPSIONAL -- kalau belum diinstall di environment
# yang dipakai untuk build ini (pip install "katalog-pdf[ocr]"), dilewati
# saja tanpa menggagalkan build; hasilnya cuma checkbox OCR nonaktif di .exe.
for pkg in ('pytesseract', 'pdf2image'):
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    except Exception:
        print(f"[katalog-pdf.spec] Lewati '{pkg}' -- belum terinstall di environment build ini.")

a = Analysis(
    ['katalog_pdf/desktop_launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KatalogPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # False -- tanpa jendela konsol hitam. Streamlit tetap jalan normal,
    # cuma tidak ada window terminal yang nongol pas .exe dibuka (lihat
    # penjelasan di desktop_launcher.py soal kenapa stdout/stderr perlu
    # dialihkan ke file log begitu konsolnya disembunyikan).
    console=False,
)
