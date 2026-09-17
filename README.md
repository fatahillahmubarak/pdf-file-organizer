# 📚 PDF File Organizer

*(Sebelumnya bernama "Katalog PDF" / "PDF-Catalog" -- nama & repo
diperbarui supaya lebih mencerminkan fiturnya yang sekarang lebih dari
sekadar katalog. Perintah CLI (`katalog-pdf`), nama package Python
(`katalog_pdf`), dan nama file `.exe` (`KatalogPDF.exe`) TIDAK berubah --
link/perintah lama tetap jalan seperti biasa.)*

Tool untuk mengkatalogkan, mencari (full-text search), dan menemukan file
duplikat di koleksi PDF-mu -- lewat UI Streamlit yang enak dipakai, atau
lewat command line kalau kamu suka scripting. Semua proses berjalan **lokal
di komputermu sendiri** -- tidak ada file yang di-upload ke mana pun.

## Fitur

- **Bangun katalog otomatis**: scan folder (termasuk semua subfolder),
  ekstrak judul/penulis/tahun/jumlah halaman, dan hasilkan kata kunci
  otomatis dari isi dokumen.
- **Resumable**: kalau proses scan terhenti di tengah jalan (listrik mati,
  komputer restart, dll), jalankan ulang command yang sama -- file yang
  sudah diproses otomatis dilewati, tidak mulai dari nol.
- **Full-text search instan**: cari di judul, penulis, kata kunci, ATAU isi
  teks lengkap ratusan PDF sekaligus, lewat index SQLite FTS5.
- **Cari duplikat**: temukan file PDF yang isinya identik (berdasarkan hash
  isi file, bukan cuma nama file) dan berapa ruang disk yang bisa dihemat.
- **Cari duplikat MIRIP (near-duplicate)**: selain duplikat identik
  byte-per-byte di atas, fitur ini membandingkan **isi teks** tiap PDF untuk
  menemukan buku yang sama tapi di-scan dua kali, atau cetakan ulang yang
  isinya nyaris sama tapi filenya berbeda secara teknis.
- **Saran rename otomatis (DOI/ISBN)**: deteksi DOI/ISBN tiap PDF, cocokkan
  otomatis ke Crossref (paper) atau Google Books (buku), lalu usulkan nama
  file format `TIPE_(Penulis, Tahun)_Judul` (gaya APA -- 1 penulis apa
  adanya, 2 penulis "A & B", 3+ penulis "A et al."). Tidak ada file yang
  langsung di-rename -- selalu lewat review manual dulu sebelum menjalankan
  script rename-nya.
- **Export multi-format**: hasil katalog & pencarian bisa disimpan sebagai
  Excel (`.xlsx`), CSV, JSON, ODS (LibreOffice), TSV, atau tabel Markdown --
  tinggal pilih dari dropdown format di tiap tombol download.
- **OCR opsional**: untuk PDF hasil scan yang tidak punya text layer
  (cocok untuk teks cetak, bukan tulisan tangan).

## Instalasi

Pilih salah satu, dari yang paling gampang:

**Opsi 1 -- Download `.exe` (paling gampang, tidak perlu install Python sama sekali)**

Download `KatalogPDF.exe` dari halaman [Releases](https://github.com/fatahillahmubarak/pdf-file-organizer/releases),
taruh di folder mana saja, lalu double-click. Fitur Bangun Katalog, Cari, dan
Cari Duplikat langsung bisa dipakai tanpa instalasi tambahan apa pun.
(Fitur OCR butuh 2 program tambahan yang diinstall terpisah, tanpa pip/terminal --
lihat bagian **Prasyarat** di bawah.)

Sejak v0.4.0, `.exe` ini membuka window aplikasi native (bukan tab browser)
lewat WebView2 -- fitur bawaan Windows 10/11 yang biasanya sudah terinstall
otomatis. Kalau WebView2 belum ada di komputer kamu, tidak masalah: app
otomatis jatuh kembali (fallback) buka tab browser seperti versi
sebelumnya, jadi tetap bisa dipakai normal.

**Opsi 2 -- Lewat pip (kalau sudah punya Python)**

```bash
pip install katalog-pdf
katalog-pdf ui
```

**Opsi 3 -- Dari source code (untuk developer / mau modifikasi)**

```bash
git clone https://github.com/fatahillahmubarak/pdf-file-organizer.git
cd pdf-file-organizer
pip install -e .
katalog-pdf ui
```

## Prasyarat

Fitur **Bangun Katalog**, **Cari**, dan **Cari Duplikat** tidak butuh
instalasi tambahan apa pun -- baik lewat `.exe` maupun `pip install`, semuanya
sudah termasuk di dalamnya.

Fitur **OCR** (untuk PDF hasil scan yang tidak punya teks yang bisa di-copy)
butuh 2 program eksternal (Tesseract & Poppler) yang **tidak ikut terbungkus**
ke dalam `.exe` -- keduanya harus diinstall terpisah di komputer pemakainya
(lihat penjelasan kenapa di catatan lisensi di bawah). Ini **opsional** --
kalau kamu tidak akan memproses PDF hasil scan, lewati saja bagian ini.

Supaya OCR aktif:

1. Kalau install lewat pip/source (bukan `.exe`): `pip install "katalog-pdf[ocr]"`
   -- kalau pakai `.exe`, langkah ini tidak perlu, library Python-nya sudah
   ikut terbungkus di dalam `.exe`.
2. Install Tesseract & Poppler di sistem operasimu (langkah ini tetap
   dibutuhkan baik pakai `.exe` maupun `pip`, karena keduanya program
   terpisah, bukan library Python -- lihat tab **Panduan** di dalam app untuk
   instruksi step-by-step tanpa terminal/pip):

   | OS | Cara install |
   |---|---|
   | Windows | Tesseract: https://github.com/UB-Mannheim/tesseract/wiki -- Poppler: https://github.com/oschwartz10612/poppler-windows/releases (extract `.zip`, tambahkan `Library\bin` ke PATH) |
   | macOS | `brew install tesseract tesseract-lang poppler` |
   | Ubuntu/Debian | `sudo apt-get install tesseract-ocr tesseract-ocr-ind poppler-utils` |

OCR cocok untuk teks **cetak** yang di-scan. Untuk manuskrip **tulisan
tangan**, hasilnya biasanya kurang bisa dipakai.

## Pakai lewat UI (rekomendasi untuk pemula)

```bash
katalog-pdf ui
```

Ini akan membuka tab baru di browser dengan 4 fitur utama: **Bangun
Katalog**, **Cari**, **Cari Duplikat** (termasuk mode near-duplicate),
dan **Saran Rename** (deteksi DOI/ISBN).

## Pakai lewat command line

```bash
# 1. Bangun katalog dari sebuah folder PDF
katalog-pdf build "/path/ke/folder/pdf"

# 2. Cari
katalog-pdf search "machine learning" --db katalog_pdf.db
katalog-pdf search "\"supply chain\"" --limit 20      # frasa persis
katalog-pdf search "ekonomi AND makro"                 # operator boolean

# 3. Cari duplikat
katalog-pdf duplicates "/path/ke/folder/pdf"

# 4. Export ulang dari database yang sudah ada (tanpa scan ulang) --
#    format ditentukan dari ekstensi --output: .xlsx, .csv, .json, .ods, .tsv, atau .md
katalog-pdf export katalog_pdf.db --output katalog_pdf.xlsx
katalog-pdf export katalog_pdf.db --output katalog_pdf.json
```

Jalankan `katalog-pdf <subcommand> --help` untuk melihat semua opsi
(misalnya `--ocr`, `--max-pages`, `--fresh`, dll).

## Untuk developer

Struktur proyek:

```
katalog_pdf/
  core.py             -- logika inti (baca PDF, index FTS5, cari duplikat, export Excel)
  cli.py              -- command-line interface
  app.py              -- UI Streamlit (Bahasa Indonesia & English)
  i18n.py             -- teks UI dua bahasa, tinggal tambah bahasa baru di sini
  desktop_launcher.py -- entry point khusus untuk dibungkus jadi .exe
Buka_Katalog_PDF.bat  -- launcher untuk dipakai sendiri (double-click, tanpa buka terminal)
katalog-pdf.spec      -- konfigurasi build .exe (PyInstaller)
pyproject.toml
```

Membangun `.exe` standalone sendiri (tanpa perlu Python/conda di komputer
pemakainya):

```bash
pip install "katalog-pdf[build,ocr]"
pyinstaller katalog-pdf.spec
```

Hasilnya ada di `dist/KatalogPDF.exe`. Catatan: kombinasi Streamlit +
PyInstaller kadang butuh 1-2 kali percobaan. Kalau muncul error semacam
`PackageNotFoundError` yang menyebut nama library tertentu, biasanya cukup
ditambahkan lewat `copy_metadata('nama-library')` di `katalog-pdf.spec`,
lalu jalankan ulang `pyinstaller katalog-pdf.spec`.

Extra `[build]` sekarang juga mengikutkan `pywebview` (+ `pythonnet` di
Windows) supaya `.exe` hasil build bisa buka window native -- lihat
penjelasan WebView2/fallback di bagian **Instalasi** di atas.

Catatan soal lisensi OCR: library Python `pytesseract` dan `pdf2image`
(berlisensi permisif -- Apache 2.0 / MIT) ikut dibungkus ke dalam `.exe`
lewat extra `[ocr]` di atas, jadi checkbox OCR di `.exe` bisa langsung
dipakai. Tapi program Tesseract dan Poppler sendiri **sengaja tidak**
dibungkus ke dalam `.exe` (Poppler berlisensi GPL, jadi lebih aman kalau
tetap jadi program terpisah yang diinstall sendiri oleh pemakai, bukan
ikut dibundel) -- lihat bagian **Prasyarat** di atas untuk cara installnya
tanpa command line.

## Kontribusi

Issue dan pull request dipersilakan. Proyek ini awalnya dibuat untuk
kebutuhan pribadi mengkatalogkan koleksi PDF, lalu dikembangkan supaya bisa
dipakai siapa saja.

## Credit

Dibuat oleh **Muhammad Fatahillah Mubarak**, awalnya untuk kebutuhan pribadi
mengkatalogkan koleksi PDF, lalu dikembangkan lebih lanjut menjadi versi yang
bisa dipakai siapa saja. Tampilan UI, penerjemahan dua bahasa, dan proses
packaging ke `.exe` pada tool ini dikembangkan dengan bantuan **Claude**
(Anthropic) sebagai AI pairing assistant.

- 📧 Email: [fatahillah.mubarak@gmail.com](mailto:fatahillah.mubarak@gmail.com)
- 🔗 GitHub: [github.com/fatahillahmubarak](https://github.com/fatahillahmubarak)

## Lisensi

MIT
