# Roadmap / Ide untuk versi selanjutnya

Catatan ide-ide yang sengaja di-*hold* dulu supaya tidak lupa, untuk
dikerjakan di rilis berikutnya (bukan untuk rilis `.exe` v1 pertama ini).

- [x] **Export multi-format**: sudah selesai -- dropdown pilihan format
  (Excel, CSV, JSON, ODS/LibreOffice, TSV, tabel Markdown) ditambahkan di
  tombol download tab Bangun Katalog, Cari, dan Cari Duplikat, plus
  `katalog-pdf export db.db --output hasil.<ext>` di CLI (format otomatis
  ditentukan dari ekstensi `--output`). Perlu `pip install "katalog-pdf[build,ocr]"`
  lalu `pyinstaller katalog-pdf.spec` ulang supaya `.exe` yang sudah dirilis
  (v0.1.0) ikut punya fitur ini -- dua library baru (`tabulate`, `odfpy`)
  sudah ditambahkan ke `katalog-pdf.spec` supaya ikut terbungkus.
- [x] **Cari duplikat MIRIP (near-duplicate)**: sudah selesai --
  membandingkan isi teks (bukan cuma hash exact) lewat inverted keyword index
  + kemiripan teks (`difflib`), jadi bisa nemuin buku yang sama di-scan dua
  kali atau cetakan ulang. Ada di UI (bagian bawah tab Cari Duplikat) dan CLI
  (`katalog-pdf near-duplicates <folder>`).
- [x] **Saran rename otomatis (DOI/ISBN)**: sudah selesai -- deteksi
  DOI/ISBN tiap PDF, cocokkan ke Crossref/Google Books, usulkan nama file
  `TIPE_(Penulis, Tahun)_Judul` gaya APA (1 penulis apa adanya, 2 penulis "A
  & B", 3+ penulis "A et al."), plus opsi download script PowerShell rename
  (selalu perlu direview manual dulu). Ada di tab baru "🏷️ Saran Rename" dan
  CLI (`katalog-pdf suggest-renames <folder>`).
- [ ] (tambahkan ide lain di sini seiring berjalannya waktu)
