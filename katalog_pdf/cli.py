#!/usr/bin/env python3
"""
cli.py
======
Command-line interface untuk katalog_pdf. Menyatukan 4 command lama jadi
satu tool dengan subcommand, tapi perilakunya tetap sama seperti script asli:

    katalog-pdf build "/path/ke/folder/pdf"
    katalog-pdf search "kata kunci" --db katalog_pdf.db
    katalog-pdf duplicates "/path/ke/folder/pdf"
    katalog-pdf near-duplicates "/path/ke/folder/pdf"
    katalog-pdf suggest-renames "/path/ke/folder/pdf"
    katalog-pdf export katalog_pdf.db --output katalog_pdf.xlsx
    katalog-pdf ui                     # buka UI Streamlit

Dependencies: pip install katalog-pdf   (atau, dari source: pip install -e .)
"""

import argparse
import sys
from pathlib import Path

from . import core


def _cmd_build(args):
    ocr_note = f" (OCR aktif, lang={args.ocr_lang})" if args.ocr else ""
    print(f"Menscan folder: {args.folder}{ocr_note}")

    def progress(done, total, path):
        if done % 10 == 0 or done == total:
            print(f"  ...{done}/{total} ({path.name})")

    try:
        result = core.build_catalog(
            args.folder, output=args.output, db=args.db, max_pages=args.max_pages,
            use_ocr=args.ocr, ocr_lang=args.ocr_lang, ocr_max_pages=args.ocr_max_pages,
            ocr_dpi=args.ocr_dpi, fresh=args.fresh, progress_cb=progress,
        )
    except (FileNotFoundError, RuntimeError) as e:
        sys.exit(str(e))

    print(f"\nDitemukan {result.total_found} file PDF.")
    if result.n_skipped:
        print(f"{result.n_skipped} file sudah pernah diproses sebelumnya -- dilewati.")
    print(f"Memproses {result.n_processed} file baru.")
    print(f"Katalog Excel tersimpan: {args.output} ({result.n_rows_in_excel} baris total)")
    print(f"\nSekarang kamu bisa search dengan:\n    katalog-pdf search \"kata kunci\" --db {args.db}")


def _cmd_search(args):
    try:
        results = core.search_catalog(args.db, args.query, args.limit)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))

    if not results:
        print(f'Tidak ada hasil untuk: "{args.query}"')
        return

    if args.output:
        core.save_search_results_to_excel(results, args.output)
        print(f'Ditemukan {len(results)} hasil untuk "{args.query}".')
        print(f"Hasil pencarian tersimpan ke: {args.output}")
        return

    print(f'Ditemukan {len(results)} hasil untuk "{args.query}":\n')
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['judul']}")
        if r["penulis"]:
            print(f"   Penulis : {r['penulis']}")
        if r["tahun"]:
            print(f"   Tahun   : {r['tahun']}")
        print(f"   File    : {r['path_lengkap']}")
        print(f"   Cuplikan: {r['cuplikan_relevan']}")
        print()


def _cmd_duplicates(args):
    try:
        result = core.find_duplicates(args.folder)
    except FileNotFoundError as e:
        sys.exit(str(e))

    if not result.groups:
        print("\nTidak ditemukan file duplikat. Koleksi kamu bersih.")
        return

    df = core.duplicates_to_dataframe(result)
    df.to_excel(args.output, index=False, sheet_name="Duplikat")

    print(f"\n--- Ringkasan ---")
    print(f"Total file PDF diperiksa : {result.total_checked}")
    print(f"Grup duplikat ditemukan  : {len(result.groups)}")
    print(f"Perkiraan ruang dihemat  : {round(result.total_wasted_kb / 1024, 1)} MB")
    print(f"Laporan lengkap tersimpan: {args.output}")


def _cmd_near_duplicates(args):
    print(f"Membandingkan isi teks tiap PDF di: {args.folder} (bisa lebih lama dari cek exact-hash)")

    def progress(done, total):
        if done % 10 == 0 or done == total:
            print(f"  ...{done}/{total}")

    try:
        result = core.find_near_duplicates(
            args.folder, max_pages=args.max_pages, use_ocr=args.ocr, ocr_lang=args.ocr_lang,
            min_shared_keywords=args.min_shared_keywords, similarity_threshold=args.similarity,
            progress_cb=progress,
        )
    except FileNotFoundError as e:
        sys.exit(str(e))

    if not result.groups:
        print("\nTidak ditemukan kemungkinan duplikat mirip. (Ini heuristik -- exact-hash tetap "
              "dicek terpisah lewat 'katalog-pdf duplicates'.)")
        return

    df = core.near_duplicates_to_dataframe(result)
    df.to_excel(args.output, index=False, sheet_name="Duplikat Mirip")

    print(f"\n--- Ringkasan ---")
    print(f"Total file PDF diperiksa      : {result.total_checked}")
    print(f"Grup kemungkinan mirip ditemukan: {len(result.groups)}")
    print(f"Laporan lengkap tersimpan      : {args.output}")
    print("PENTING: ini heuristik berbasis kemiripan teks, BUKAN kepastian -- selalu cek "
          "manual dulu sebelum menghapus, terutama baris yang ditandai catatan halaman beda.")


def _cmd_suggest_renames(args):
    print(f"Mendeteksi DOI/ISBN & mencari metadata untuk PDF di: {args.folder}")
    if not args.email:
        print("Tips: pakai --email alamat@emailmu.com supaya request ke Crossref masuk "
              "'polite pool' (lebih jarang di-rate-limit).")

    def progress(done, total, path):
        if done % 5 == 0 or done == total:
            print(f"  ...{done}/{total} ({path.name})")

    try:
        result = core.suggest_renames(
            args.folder, max_pages=args.max_pages, use_ocr=args.ocr, ocr_lang=args.ocr_lang,
            contact_email=args.email, lookup_delay=args.delay, progress_cb=progress,
        )
    except FileNotFoundError as e:
        sys.exit(str(e))

    core.save_rename_suggestions_to_excel(result, args.output)

    print(f"\n--- Ringkasan ---")
    print(f"Total file diperiksa : {result.total_found}")
    print(f"Confidence High      : {result.n_high}  (DOI/ISBN ketemu & lengkap -- aman untuk auto-rename)")
    print(f"Confidence Medium    : {result.n_medium}  (ketemu tapi ada info hilang -- cek dulu)")
    print(f"Confidence Low       : {result.n_low}  (PERLU VERIFIKASI MANUAL)")
    print(f"Laporan lengkap tersimpan: {args.output}")

    if args.ps1:
        n = core.write_rename_powershell_script(result, args.ps1, min_confidence=args.min_confidence_ps1)
        print(f"Script rename PowerShell ({args.min_confidence_ps1}+ confidence, {n} file) tersimpan: {args.ps1}")
        print("PENTING: buka & review dulu isi script-nya sebelum dijalankan -- ini USULAN, bukan eksekusi otomatis.")


def _cmd_export(args):
    output_path = Path(args.output)
    ext = output_path.suffix.lower().lstrip(".") or "xlsx"
    if ext not in core.EXPORT_FORMATS:
        sys.exit(
            f"Format '.{ext}' tidak didukung. Gunakan salah satu ekstensi: "
            f"{', '.join(core.EXPORT_FORMATS)}. / "
            f"Format '.{ext}' is not supported. Use one of: {', '.join(core.EXPORT_FORMATS)}."
        )

    n_problem = 0
    try:
        if ext == "xlsx":
            n_rows, n_problem = core.export_excel_from_db_path(args.db, args.output)
        else:
            df = core.load_catalog_dataframe(args.db)
            output_path.write_bytes(core.dataframe_to_export_bytes(df, ext))
            n_rows = len(df)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))

    print(f"Berhasil! Katalog format {ext.upper()} tersimpan: {args.output} ({n_rows} baris)")
    if n_problem:
        print(f"Catatan: {n_problem} sel butuh pembersihan ekstra.")


def _cmd_ui(args):
    import subprocess
    from pathlib import Path
    core.ensure_streamlit_no_prompt()
    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


def main():
    parser = argparse.ArgumentParser(prog="katalog-pdf", description="Katalog & pencarian file PDF.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="Scan folder PDF & bangun katalog + index pencarian")
    p_build.add_argument("folder")
    p_build.add_argument("--output", default="katalog_pdf.xlsx")
    p_build.add_argument("--db", default="katalog_pdf.db")
    p_build.add_argument("--max-pages", type=int, default=20)
    p_build.add_argument("--ocr", action="store_true")
    p_build.add_argument("--ocr-lang", default="eng")
    p_build.add_argument("--ocr-max-pages", type=int, default=5)
    p_build.add_argument("--ocr-dpi", type=int, default=200)
    p_build.add_argument("--fresh", action="store_true")
    p_build.set_defaults(func=_cmd_build)

    p_search = sub.add_parser("search", help="Cari di katalog yang sudah dibangun")
    p_search.add_argument("query")
    p_search.add_argument("--db", default="katalog_pdf.db")
    p_search.add_argument("--limit", type=int, default=15)
    p_search.add_argument("--output", default=None)
    p_search.set_defaults(func=_cmd_search)

    p_dup = sub.add_parser("duplicates", help="Cari file PDF duplikat berdasarkan isi (hash exact SHA-256)")
    p_dup.add_argument("folder")
    p_dup.add_argument("--output", default="duplikat_pdf.xlsx")
    p_dup.set_defaults(func=_cmd_duplicates)

    p_near_dup = sub.add_parser(
        "near-duplicates",
        help="Cari kemungkinan duplikat berdasarkan KEMIRIPAN isi teks (bukan hash exact) -- "
             "menangkap scan/edisi berbeda dari buku yang sama",
    )
    p_near_dup.add_argument("folder")
    p_near_dup.add_argument("--output", default="duplikat_mirip_pdf.xlsx")
    p_near_dup.add_argument("--max-pages", type=int, default=10)
    p_near_dup.add_argument("--ocr", action="store_true")
    p_near_dup.add_argument("--ocr-lang", default="eng")
    p_near_dup.add_argument("--min-shared-keywords", type=int, default=2)
    p_near_dup.add_argument("--similarity", type=float, default=0.6,
                             help="Ambang kemiripan teks 0-1 (default 0.6). Naikkan kalau terlalu "
                                  "banyak false-positive, turunkan kalau ada duplikat yang terlewat.")
    p_near_dup.set_defaults(func=_cmd_near_duplicates)

    p_rename = sub.add_parser(
        "suggest-renames",
        help="Deteksi DOI/ISBN tiap PDF, cocokkan ke Crossref/Google Books, lalu usulkan nama "
             "file format TYPE_(Author, Year)_Judul (tidak me-rename apa pun secara langsung)",
    )
    p_rename.add_argument("folder")
    p_rename.add_argument("--output", default="saran_rename.xlsx")
    p_rename.add_argument("--max-pages", type=int, default=25)
    p_rename.add_argument("--ocr", action="store_true")
    p_rename.add_argument("--ocr-lang", default="eng")
    p_rename.add_argument("--email", default=None,
                           help="Alamat email kontak (opsional) -- supaya request Crossref masuk 'polite pool'.")
    p_rename.add_argument("--delay", type=float, default=0.3,
                           help="Jeda antar request API dalam detik (default 0.3) -- sopan ke server, hindari rate-limit.")
    p_rename.add_argument("--ps1", default=None,
                           help="Kalau diisi, tulis juga script PowerShell rename ke path ini.")
    p_rename.add_argument("--min-confidence-ps1", default="High", choices=["High", "Medium", "Low"],
                           help="Confidence minimum yang dimasukkan ke script PowerShell (default High).")
    p_rename.set_defaults(func=_cmd_suggest_renames)

    p_export = sub.add_parser(
        "export",
        help=(
            "Export ulang dari database yang sudah ada -- format ditentukan dari "
            "ekstensi --output (.xlsx, .csv, .json, .ods, .tsv, atau .md)"
        ),
    )
    p_export.add_argument("db")
    p_export.add_argument("--output", default="katalog_pdf.xlsx",
                           help="Nama file output -- pakai ekstensi .xlsx atau .csv")
    p_export.set_defaults(func=_cmd_export)

    p_ui = sub.add_parser("ui", help="Buka user interface (Streamlit) di browser")
    p_ui.set_defaults(func=_cmd_ui)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
