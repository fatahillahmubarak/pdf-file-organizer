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
- [ ] (tambahkan ide lain di sini seiring berjalannya waktu)
