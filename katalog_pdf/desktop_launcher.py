#!/usr/bin/env python3
"""
desktop_launcher.py
====================
Entry point khusus untuk dibungkus jadi file .exe standalone lewat PyInstaller
(lihat katalog-pdf.spec di root project). Tujuannya supaya orang yang tidak
punya Python/conda terinstall tetap bisa memakai UI-nya -- tinggal download
dan double-click .exe-nya.

Untuk pemakaian normal sehari-hari (kamu sendiri, sudah ada Python/conda),
TIDAK perlu file ini -- cukup pakai `katalog-pdf ui` atau Buka_Katalog_PDF.bat.
"""

import os
import sys

# Kalau dijalankan langsung sebagai script (python katalog_pdf/desktop_launcher.py,
# bukan lewat PyInstaller), folder project (bukan folder katalog_pdf/ itu sendiri)
# perlu ditambahkan ke sys.path supaya "from katalog_pdf.core import ..." di
# bawah bisa ketemu. Saat sudah di-bundle PyInstaller, _MEIPASS sudah otomatis
# ada di sys.path, jadi langkah ini dilewati.
if not hasattr(sys, "_MEIPASS"):
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)


def _resource_path(relative_path: str) -> str:
    """
    Cari path resource, baik waktu dijalankan biasa sebagai script Python
    (base_path = folder project) maupun setelah di-bundle PyInstaller
    (base_path = folder temp sementara tempat PyInstaller mengekstrak semua
    file yang di-bundle, tersedia lewat sys._MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        # file ini ada di <project_root>/katalog_pdf/desktop_launcher.py
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def main():
    from streamlit.web import cli as stcli
    from katalog_pdf.core import ensure_streamlit_no_prompt

    ensure_streamlit_no_prompt()

    app_path = _resource_path(os.path.join("katalog_pdf", "app.py"))
    if not os.path.exists(app_path):
        sys.exit(f"Tidak menemukan app.py di: {app_path}")

    sys.argv = [
        "streamlit", "run", app_path,
        "--global.developmentMode=false",
        "--server.headless=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
