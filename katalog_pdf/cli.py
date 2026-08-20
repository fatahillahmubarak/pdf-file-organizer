#!/usr/bin/env python3
"""
cli.py
======
Command-line interface untuk katalog_pdf. Menyatukan 4 command lama jadi
satu tool dengan subcommand, tapi perilakunya tetap sama seperti script asli:

    katalog-pdf build "/path/ke/folder/pdf"
    katalog-pdf search "kata kunci" --db katalog_pdf.db
    katalog-pdf duplicates "/path/ke/folder/pdf"
    katalog-pdf export katalog_pdf.db --output katalog_pdf.xlsx
    katalog-pdf ui                     # buka UI Streamlit

Dependencies: pip install katalog-pdf   (atau, dari source: pip install -e .)
"""

import argparse
import sys

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


def _cmd_export(args):
    try:
        n_rows, n_problem = core.export_excel_from_db_path(args.db, args.output)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))
    print(f"Berhasil! Excel katalog tersimpan: {args.output} ({n_rows} baris)")
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

    p_dup = sub.add_parser("duplicates", help="Cari file PDF duplikat berdasarkan isi")
    p_dup.add_argument("folder")
    p_dup.add_argument("--output", default="duplikat_pdf.xlsx")
    p_dup.set_defaults(func=_cmd_duplicates)

    p_export = sub.add_parser("export", help="Export ulang Excel dari database yang sudah ada")
    p_export.add_argument("db")
    p_export.add_argument("--output", default="katalog_pdf.xlsx")
    p_export.set_defaults(func=_cmd_export)

    p_ui = sub.add_parser("ui", help="Buka user interface (Streamlit) di browser")
    p_ui.set_defaults(func=_cmd_ui)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
