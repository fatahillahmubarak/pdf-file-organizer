#!/usr/bin/env python3
"""
i18n.py
=======
Teks UI dalam Bahasa Indonesia & English untuk app.py. Supaya tool ini bisa
dipakai orang dari mana saja, bukan cuma yang mengerti Bahasa Indonesia.

Cara pakai di app.py:
    from katalog_pdf.i18n import TRANSLATIONS, LANGUAGES
    T = TRANSLATIONS[lang]          # lang = "id" atau "en"
    st.write(T["build"]["subheader"])

Nambah bahasa baru: tinggal tambah satu key baru (misal "es") berisi dict
dengan struktur SAMA PERSIS seperti "id"/"en" di bawah.
"""

LANGUAGES = {
    "id": "🇮🇩 Bahasa Indonesia",
    "en": "🇬🇧 English",
}

TRANSLATIONS = {
    "id": {
        "common": {
            "page_title": "Katalog PDF",
            "app_title": "📚 Katalog PDF",
            "app_caption": (
                "Kelola koleksi PDF-mu: bangun katalog otomatis, cari isi ratusan dokumen "
                "dalam sekejap, dan temukan file duplikat -- semua berjalan lokal di "
                "komputermu sendiri, tidak ada file yang di-upload ke mana pun."
            ),
            "tab_build": "📂 Bangun Katalog",
            "tab_search": "🔍 Cari",
            "tab_dup": "🧹 Cari Duplikat",
            "tab_help": "ℹ️ Panduan",
            "lang_label": "Bahasa",
            "export_format_label": "Pilih format export:",
            "export_format_names": {
                "xlsx": "Excel (.xlsx)",
                "csv": "CSV (.csv)",
                "json": "JSON (.json)",
                "ods": "OpenDocument / LibreOffice (.ods)",
                "tsv": "Tab-separated (.tsv)",
                "md": "Tabel Markdown (.md)",
            },
            "export_download_button": "⬇️ Download ({format})",
        },
        "build": {
            "subheader": "Scan folder PDF & bangun katalog",
            "description": (
                "Proses ini membaca setiap PDF di dalam folder (termasuk semua subfolder), "
                "mengambil judul/penulis/tahun, menyimpan cuplikan teks untuk pencarian, dan "
                "menghasilkan file Excel yang bisa dibuka & difilter manual."
            ),
            "folder_label": "Path folder PDF",
            "folder_placeholder": r"C:\Users\NamaKamu\Documents\PDF",
            "output_label": "Nama file Excel output",
            "db_label": "Nama file index (database)",
            "fresh_label": "Mulai dari nol (abaikan database lama)",
            "fresh_help": "Kalau dicentang, database lama dihapus dan semua PDF diproses ulang dari awal.",
            "advanced_expander": "Opsi lanjutan",
            "max_pages_label": "Maks halaman dibaca per PDF (untuk teks)",
            "ocr_checkbox_label": "Aktifkan OCR untuk PDF hasil scan (tanpa text layer)",
            "ocr_unavailable_caption": (
                "⚠️ OCR belum aktif di lingkungan ini. Install dulu: "
                "`pip install pytesseract pdf2image`, dan pastikan `tesseract-ocr` "
                "terinstall di sistem operasimu (lihat tab Panduan)."
            ),
            "ocr_lang_label": "Bahasa OCR",
            "ocr_lang_help": (
                "Pilih satu atau lebih bahasa. Untuk manuskrip Belanda-Indonesia lama, "
                "pilih Nederlands + Bahasa Indonesia sekaligus."
            ),
            "ocr_lang_custom_label": "Kode Tesseract kustom (opsional)",
            "ocr_lang_custom_help": (
                "Isi kalau bahasa yang kamu perlukan tidak ada di daftar dropdown di atas -- "
                "isian ini akan menggantikan pilihan dropdown. Jalankan 'tesseract --list-langs' "
                "di terminal untuk melihat semua kode bahasa yang terinstall di komputermu."
            ),
            "ocr_max_pages_label": "Maks halaman di-OCR per file",
            "ocr_dpi_label": "Resolusi render sebelum OCR (DPI)",
            "start_button": "🚀 Mulai Scan",
            "error_empty_folder": "Isi dulu path foldernya.",
            "progress_processing": "Memproses {done}/{total}: {name}",
            "spinner_text": "Menscan folder...",
            "success_text": "Selesai!",
            "metric_total_found": "Total PDF ditemukan",
            "metric_skipped": "Sudah pernah diproses",
            "metric_processed": "Baru diproses run ini",
            "metric_total_rows": "Total baris di katalog",
            "errors_expander": "⚠️ {count} file gagal dibaca",
            "resume_caption": (
                "Index pencarian tersimpan di `{db_path}` -- kalau proses ini kamu ulang lagi "
                "nanti (misal ada PDF baru ditambahkan ke folder), file yang sudah pernah "
                "diproses otomatis dilewati."
            ),
        },
        "search": {
            "subheader": "Cari di katalog",
            "description": "Cari berdasarkan judul, penulis, kata kunci, ATAU isi teks lengkap dokumen.",
            "db_label": "File index (database)",
            "limit_label": "Jumlah hasil maks",
            "query_label": "Kata kunci / frasa",
            "query_placeholder": 'contoh: machine learning   |   "supply chain"   |   ekonomi AND makro',
            "tips_caption": (
                'Tips: pakai tanda kutip untuk frasa persis (`"kata kunci"`), atau operator '
                "`AND` / `OR` / `NOT` (huruf besar) untuk pencarian gabungan."
            ),
            "search_button": "🔍 Cari",
            "error_empty_query": "Isi dulu kata kuncinya.",
            "no_results": 'Tidak ada hasil untuk: "{query}"',
            "found_count": "Ditemukan **{count}** hasil:",
        },
        "dup": {
            "subheader": "Cari file PDF duplikat",
            "description": (
                "Setiap file dibandingkan berdasarkan isi (hash SHA-256), bukan nama file -- jadi "
                "file dengan nama berbeda tapi isi identik tetap terdeteksi. Script ini **hanya "
                "melaporkan**, tidak menghapus apa pun -- keputusan hapus tetap di tanganmu."
            ),
            "folder_label": "Path folder PDF",
            "button": "🧹 Cari Duplikat",
            "error_empty_folder": "Isi dulu path foldernya.",
            "progress_checking": "Memeriksa {done}/{total} file...",
            "spinner_text": "Menghitung sidik jari tiap file...",
            "metric_total_checked": "Total PDF diperiksa",
            "metric_groups_found": "Grup duplikat ditemukan",
            "metric_wasted_space": "Perkiraan ruang dihemat",
            "no_duplicates": "Tidak ditemukan file duplikat. Koleksi kamu bersih!",
            "errors_expander": "⚠️ {count} file gagal dibaca",
        },
        "help": {
            "subheader": "Panduan singkat",
            "body": """
Cara pakai paling umum:

1. Buka tab **Bangun Katalog**, isi path folder PDF-mu, lalu klik *Mulai Scan*.
   Proses ini **bisa dilanjutkan** kalau berhenti di tengah jalan (komputer restart,
   ditutup tidak sengaja, dll) -- jalankan ulang dengan folder & nama database yang
   sama, file yang sudah selesai diproses otomatis dilewati.
2. Setelah katalog jadi, buka tab **Cari** untuk mencari dokumen berdasarkan judul,
   penulis, kata kunci, atau isi teks lengkapnya.
3. Buka tab **Cari Duplikat** kapan saja untuk melihat file PDF yang isinya sama
   persis (walau nama filenya beda) dan berapa ruang disk yang bisa dihemat.

## Soal OCR (untuk PDF hasil scan yang tidak punya teks yang bisa di-copy)

OCR cocok untuk teks **cetak** yang di-scan. Untuk manuskrip **tulisan
tangan**, hasilnya biasanya kurang bisa dipakai.

Kalau kamu pakai versi **`.exe`**: kamu HANYA perlu install 2 program di
bawah ini. Tidak perlu buka terminal atau ketik command `pip` apa pun --
tinggal download & install seperti install aplikasi Windows biasa.

**Langkah 1 -- Install Tesseract (mesin OCR-nya)**

1. Buka https://github.com/UB-Mannheim/tesseract/wiki
2. Download installer Windows-nya (file `.exe`, nama filenya biasanya
   `tesseract-ocr-w64-setup-x.x.x.exe`)
3. Jalankan file itu, lalu klik Next/Install seperti install program biasa
4. Saat instalasi, biarkan opsi **"Add to PATH"** tetap tercentang (biasanya
   sudah tercentang secara default -- jangan dihilangkan)
5. Kalau butuh OCR bahasa selain Inggris (misal Bahasa Indonesia), centang
   juga bahasanya di bagian **"Additional language data"** saat instalasi

**Langkah 2 -- Install Poppler**

1. Buka https://github.com/oschwartz10612/poppler-windows/releases
2. Di rilis paling atas, download file `.zip` di bagian "Assets"
3. Extract file `.zip` itu ke folder mana saja, misalnya `C:\\poppler`
4. Tambahkan folder `Library\\bin` di dalamnya ke PATH Windows:
   - Klik Start, ketik **"environment variables"**, buka
     **"Edit the system environment variables"**
   - Klik tombol **"Environment Variables..."**
   - Di bagian **"User variables"**, cari baris **"Path"**, klik **"Edit"**
   - Klik **"New"**, lalu tempel path lengkap ke folder `Library\\bin` tadi
     (misal `C:\\poppler\\Library\\bin`)
   - Klik **OK** di semua jendela yang terbuka

**Langkah 3 -- Restart aplikasi**

Tutup `KatalogPDF.exe` (kalau lagi jalan), lalu buka lagi -- supaya
perubahan PATH tadi terbaca oleh aplikasinya.

**Langkah 4 -- Cek apakah sudah berhasil (opsional)**

Buka Command Prompt (cari "cmd" di Start Menu), lalu ketik:

```
tesseract --version
pdftoppm -v
```

Kalau keduanya menampilkan nomor versi (bukan pesan error "not
recognized"), berarti sudah siap. Checkbox **"Aktifkan OCR"** di tab
Bangun Katalog sekarang akan bisa dicentang.

---

Kalau kamu pakai versi **pip / dari source code** (bukan `.exe`): ada satu
langkah tambahan paling awal, install dulu library Python-nya:

```
pip install "katalog-pdf[ocr]"
```

baru lanjut ke Langkah 1 & 2 di atas (install Tesseract & Poppler-nya sama
saja untuk macOS/Linux, tinggal ganti dengan package manager masing-masing:
`brew install tesseract tesseract-lang poppler` untuk macOS, atau
`sudo apt-get install tesseract-ocr tesseract-ocr-ind poppler-utils` untuk
Ubuntu/Debian).

**Privasi**: semua proses berjalan di komputermu sendiri. Tidak ada file PDF atau
isinya yang dikirim ke internet atau server mana pun.
""",
        },
        "credits": {
            "title": "Credit",
            "footer": (
                "Dibuat oleh Muhammad Fatahillah Mubarak, dibantu oleh Claude (Anthropic) · "
                "[GitHub](https://github.com/fatahillahmubarak) · "
                "[Email](mailto:fatahillah.mubarak@gmail.com)"
            ),
            "body": (
                "Tool ini dibuat oleh **Muhammad Fatahillah Mubarak**, awalnya untuk kebutuhan "
                "pribadi mengkatalogkan koleksi PDF, lalu dikembangkan lebih lanjut menjadi "
                "versi yang bisa dipakai siapa saja.\n\n"
                "Tampilan UI, penerjemahan dua bahasa, dan proses packaging jadi `.exe` pada "
                "tool ini dikembangkan dengan bantuan **Claude** (Anthropic) sebagai AI "
                "pairing assistant.\n\n"
                "📧 Email: [fatahillah.mubarak@gmail.com](mailto:fatahillah.mubarak@gmail.com)  \n"
                "🔗 GitHub: [github.com/fatahillahmubarak](https://github.com/fatahillahmubarak)"
            ),
        },
    },
    "en": {
        "common": {
            "page_title": "PDF Catalog",
            "app_title": "📚 PDF Catalog",
            "app_caption": (
                "Manage your PDF collection: build an automatic catalog, search the contents "
                "of hundreds of documents instantly, and find duplicate files -- everything "
                "runs locally on your own computer, nothing is uploaded anywhere."
            ),
            "tab_build": "📂 Build Catalog",
            "tab_search": "🔍 Search",
            "tab_dup": "🧹 Find Duplicates",
            "tab_help": "ℹ️ Guide",
            "lang_label": "Language",
            "export_format_label": "Choose export format:",
            "export_format_names": {
                "xlsx": "Excel (.xlsx)",
                "csv": "CSV (.csv)",
                "json": "JSON (.json)",
                "ods": "OpenDocument / LibreOffice (.ods)",
                "tsv": "Tab-separated (.tsv)",
                "md": "Markdown table (.md)",
            },
            "export_download_button": "⬇️ Download ({format})",
        },
        "build": {
            "subheader": "Scan a PDF folder & build the catalog",
            "description": (
                "This scans every PDF inside the folder (including all subfolders), extracts "
                "title/author/year, saves a text snippet for searching, and produces an Excel "
                "file you can open and filter manually."
            ),
            "folder_label": "PDF folder path",
            "folder_placeholder": r"C:\Users\YourName\Documents\PDF",
            "output_label": "Output Excel file name",
            "db_label": "Index (database) file name",
            "fresh_label": "Start from scratch (ignore old database)",
            "fresh_help": "If checked, the old database is deleted and every PDF is reprocessed from the start.",
            "advanced_expander": "Advanced options",
            "max_pages_label": "Max pages read per PDF (for text)",
            "ocr_checkbox_label": "Enable OCR for scanned PDFs (no text layer)",
            "ocr_unavailable_caption": (
                "⚠️ OCR isn't enabled in this environment yet. Install it first: "
                "`pip install pytesseract pdf2image`, and make sure `tesseract-ocr` is "
                "installed on your system (see the Guide tab)."
            ),
            "ocr_lang_label": "OCR language",
            "ocr_lang_help": (
                "Pick one or more languages. For old Dutch-Indonesian manuscripts, "
                "pick Nederlands + Bahasa Indonesia together."
            ),
            "ocr_lang_custom_label": "Custom Tesseract code (optional)",
            "ocr_lang_custom_help": (
                "Fill this in if the language you need isn't in the dropdown list above -- "
                "it will override the dropdown selection. Run 'tesseract --list-langs' in a "
                "terminal to see every language code installed on your computer."
            ),
            "ocr_max_pages_label": "Max pages OCR'd per file",
            "ocr_dpi_label": "Render resolution before OCR (DPI)",
            "start_button": "🚀 Start Scan",
            "error_empty_folder": "Please enter the folder path first.",
            "progress_processing": "Processing {done}/{total}: {name}",
            "spinner_text": "Scanning folder...",
            "success_text": "Done!",
            "metric_total_found": "Total PDFs found",
            "metric_skipped": "Already processed",
            "metric_processed": "Newly processed this run",
            "metric_total_rows": "Total rows in catalog",
            "errors_expander": "⚠️ {count} file(s) failed to read",
            "resume_caption": (
                "The search index is saved at `{db_path}` -- if you run this again later "
                "(e.g. new PDFs added to the folder), files already processed are "
                "automatically skipped."
            ),
        },
        "search": {
            "subheader": "Search the catalog",
            "description": "Search by title, author, keyword, OR the full text content of the documents.",
            "db_label": "Index (database) file",
            "limit_label": "Max results",
            "query_label": "Keyword / phrase",
            "query_placeholder": 'e.g.: machine learning   |   "supply chain"   |   economy AND policy',
            "tips_caption": (
                'Tip: use quotes for an exact phrase (`"keyword"`), or the '
                "`AND` / `OR` / `NOT` operators (uppercase) to combine terms."
            ),
            "search_button": "🔍 Search",
            "error_empty_query": "Please enter a keyword first.",
            "no_results": 'No results found for: "{query}"',
            "found_count": "Found **{count}** result(s):",
        },
        "dup": {
            "subheader": "Find duplicate PDFs",
            "description": (
                "Each file is compared by its content (SHA-256 hash), not its file name -- so "
                "files with different names but identical content are still detected. This "
                "tool **only reports**, it never deletes anything -- the decision is entirely yours."
            ),
            "folder_label": "PDF folder path",
            "button": "🧹 Find Duplicates",
            "error_empty_folder": "Please enter the folder path first.",
            "progress_checking": "Checking {done}/{total} files...",
            "spinner_text": "Fingerprinting each file...",
            "metric_total_checked": "Total PDFs checked",
            "metric_groups_found": "Duplicate groups found",
            "metric_wasted_space": "Estimated space to reclaim",
            "no_duplicates": "No duplicate files found. Your collection is clean!",
            "errors_expander": "⚠️ {count} file(s) failed to read",
        },
        "help": {
            "subheader": "Quick guide",
            "body": """
Typical workflow:

1. Open the **Build Catalog** tab, enter your PDF folder path, then click *Start Scan*.
   This process **can be resumed** if it stops partway through (computer restarts,
   accidentally closed, etc.) -- just run it again with the same folder and database
   name, and files already finished are automatically skipped.
2. Once the catalog is built, open the **Search** tab to find documents by title,
   author, keyword, or full text content.
3. Open the **Find Duplicates** tab any time to see PDF files with exactly identical
   content (even if the file names differ) and how much disk space you could reclaim.

## About OCR (for scanned PDFs that have no copyable text)

OCR works well for **printed** text that's been scanned. For **handwritten**
manuscripts, results are usually not very usable.

If you're using the **`.exe`** version: you ONLY need to install the 2
programs below. No terminal, no `pip` commands -- just download & install
like any ordinary Windows application.

**Step 1 -- Install Tesseract (the OCR engine)**

1. Go to https://github.com/UB-Mannheim/tesseract/wiki
2. Download the Windows installer (a `.exe` file, usually named
   `tesseract-ocr-w64-setup-x.x.x.exe`)
3. Run it and click Next/Install like any normal program installation
4. During setup, leave the **"Add to PATH"** option checked (it's usually
   checked by default -- don't uncheck it)
5. If you need OCR in a language other than English (e.g. Bahasa Indonesia),
   also check that language under **"Additional language data"** during
   installation

**Step 2 -- Install Poppler**

1. Go to https://github.com/oschwartz10612/poppler-windows/releases
2. On the latest release, download the `.zip` file under "Assets"
3. Extract the `.zip` file anywhere, e.g. `C:\poppler`
4. Add the `Library\bin` subfolder inside it to your Windows PATH:
   - Click Start, type **"environment variables"**, open
     **"Edit the system environment variables"**
   - Click the **"Environment Variables..."** button
   - Under **"User variables"**, find the **"Path"** row, click **"Edit"**
   - Click **"New"**, then paste the full path to that `Library\bin` folder
     (e.g. `C:\poppler\Library\bin`)
   - Click **OK** on every open window

**Step 3 -- Restart the app**

Close `KatalogPDF.exe` (if it's running), then open it again -- so the PATH
change above is picked up by the app.

**Step 4 -- Check that it worked (optional)**

Open Command Prompt (search "cmd" in the Start Menu), then type:

```
tesseract --version
pdftoppm -v
```

If both show a version number (not a "not recognized" error message), you're
all set. The **"Enable OCR"** checkbox in the Build Catalog tab will now be
checkable.

---

If you're using the **pip / source code** version (not the `.exe`): there's
one extra step first, install the Python library:

```
pip install "katalog-pdf[ocr]"
```

then continue with Steps 1 & 2 above (installing Tesseract & Poppler works
the same way on macOS/Linux, just use your package manager instead:
`brew install tesseract tesseract-lang poppler` on macOS, or
`sudo apt-get install tesseract-ocr tesseract-ocr-ind poppler-utils` on
Ubuntu/Debian).

**Privacy**: everything runs on your own computer. No PDF file or its contents is
ever sent to the internet or to any server.
""",
        },
        "credits": {
            "title": "Credits",
            "footer": (
                "Built by Muhammad Fatahillah Mubarak, with help from Claude (Anthropic) · "
                "[GitHub](https://github.com/fatahillahmubarak) · "
                "[Email](mailto:fatahillah.mubarak@gmail.com)"
            ),
            "body": (
                "This tool was built by **Muhammad Fatahillah Mubarak**, originally for "
                "personal PDF cataloging needs, then developed further into a version "
                "anyone can use.\n\n"
                "The UI, bilingual translations, and packaging into a standalone `.exe` for "
                "this tool were developed with the help of **Claude** (Anthropic) as an AI "
                "pairing assistant.\n\n"
                "📧 Email: [fatahillah.mubarak@gmail.com](mailto:fatahillah.mubarak@gmail.com)  \n"
                "🔗 GitHub: [github.com/fatahillahmubarak](https://github.com/fatahillahmubarak)"
            ),
        },
    },
}
