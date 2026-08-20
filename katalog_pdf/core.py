#!/usr/bin/env python3
"""
core.py
=======
Logika inti katalog PDF -- dipakai bersama oleh CLI (cli.py) dan UI
Streamlit (app.py). Modul ini TIDAK melakukan print/sys.exit; setiap error
dilempar sebagai exception biasa supaya pemanggilnya (CLI atau UI) bebas
menampilkannya dengan cara masing-masing.

Fungsi-fungsi di sini adalah hasil refactor dari script asli:
build_catalog.py, search_catalog.py, find_duplicates.py, export_excel_from_db.py
-- perilakunya sengaja dipertahankan sama, hanya dipindah dari "script yang
langsung jalan" jadi "fungsi yang bisa dipanggil dan diberi progress callback".
"""

import hashlib
import io
import re
import sqlite3
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from pypdf import PdfReader
import pandas as pd
from openpyxl import Workbook

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# ---------------------------------------------------------------------------
# Auto-keyword / tahun
# ---------------------------------------------------------------------------

STOPWORDS = set("""
yang dan di ke dari untuk pada dengan adalah ini itu atau juga tidak akan
dapat oleh sebagai telah para dalam suatu antara karena namun sehingga
sebuah bahwa maka jika hal bagi tersebut merupakan lebih dua satu tiga
the a an of to in on for and or is are was were be been being this that
these those with as by at from into it its it's not no yes we you they
he she his her their our your i my mine ours yours theirs
""".split())

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-']{2,}")


def extract_keywords(text: str, top_n: int = 10) -> str:
    """Ambil top_n kata paling sering muncul (di luar stopword) sebagai auto-tag."""
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 3]
    counts = Counter(tokens)
    return ", ".join(word for word, _ in counts.most_common(top_n))


def guess_year(text_or_meta: str):
    """Cari angka tahun 19xx/20xx pertama yang masuk akal."""
    match = re.search(r"\b(19|20)\d{2}\b", text_or_meta or "")
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# Sanitasi nilai untuk Excel (PDF lama/rusak kadang punya karakter aneh)
# ---------------------------------------------------------------------------

def sanitize_for_excel(value):
    """Buang semua karakter kontrol (kategori Unicode 'Cc') yang ditolak Excel,
    kecuali tab/newline/carriage-return yang aman."""
    if value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        value = str(value)
    return "".join(
        ch for ch in value
        if ch in ("\t", "\n", "\r") or unicodedata.category(ch) != "Cc"
    )


def write_cell_safely(ws, row_idx: int, col_idx: int, value) -> bool:
    """Tulis satu sel ke Excel dengan lapisan pengaman bertingkat. Return True
    kalau perlu pembersihan ekstra (dipakai untuk pelaporan ke pengguna)."""
    cell = ws.cell(row=row_idx, column=col_idx)
    needed_extra = False
    try:
        cell.value = value
        return needed_extra
    except Exception:
        needed_extra = True
    try:
        s = value if isinstance(value, str) else str(value)
        s = "".join(ch for ch in s if ch.isprintable() or ch in ("\t", "\n", "\r"))
        cell.value = s
        return needed_extra
    except Exception:
        pass
    try:
        s = value if isinstance(value, str) else str(value)
        cell.value = s.encode("ascii", errors="ignore").decode("ascii")
        return needed_extra
    except Exception:
        pass
    cell.value = "[tidak bisa ditampilkan]"
    return needed_extra


# ---------------------------------------------------------------------------
# Baca satu PDF (metadata + teks + OCR fallback opsional)
# ---------------------------------------------------------------------------

def ocr_pdf(path: Path, max_pages: int, lang: str, dpi: int = 200):
    try:
        images = convert_from_path(str(path), dpi=dpi, first_page=1, last_page=max_pages)
    except Exception as e:
        return "", f"OCR_FAILED (gagal render halaman: {e})"

    text_chunks = []
    for img in images:
        try:
            text_chunks.append(pytesseract.image_to_string(img, lang=lang))
        except Exception as e:
            return "", f"OCR_FAILED ({e})"
    return "\n".join(text_chunks), None


def read_pdf(path: Path, max_pages: int, use_ocr: bool = False, ocr_lang: str = "eng",
             ocr_max_pages: int = 5, ocr_dpi: int = 200) -> dict:
    """Baca satu PDF: metadata + teks. Return dict berisi field katalog +
    '_full_text' (dipakai untuk index FTS, tidak masuk Excel)."""
    result = {
        "filename": path.name,
        "path": str(path),
        "title": "",
        "author": "",
        "year": "",
        "pages": 0,
        "size_kb": round(path.stat().st_size / 1024, 1),
        "keywords": "",
        "text_sample": "",
        "status": "OK",
    }

    try:
        reader = PdfReader(str(path), strict=False)
        result["pages"] = len(reader.pages)

        meta = reader.metadata or {}
        title = (meta.title or "").strip()
        author = (meta.author or "").strip()

        text_chunks = []
        pages_to_read = min(len(reader.pages), max_pages)
        for i in range(pages_to_read):
            try:
                text_chunks.append(reader.pages[i].extract_text() or "")
            except Exception:
                continue
        full_text = "\n".join(text_chunks)

        if not title or title.lower() in ("untitled", "microsoft word - document1"):
            title = path.stem.replace("_", " ").replace("-", " ")

        result["title"] = title
        result["author"] = author
        result["year"] = guess_year(title) or guess_year(str(meta)) or guess_year(full_text[:2000])

        if not full_text.strip() and use_ocr and OCR_AVAILABLE:
            ocr_text, ocr_error = ocr_pdf(path, ocr_max_pages, ocr_lang, ocr_dpi)
            if ocr_error:
                result["status"] = ocr_error
            elif ocr_text.strip():
                full_text = ocr_text
                result["status"] = f"OK_VIA_OCR (dibaca {ocr_max_pages} hlm pertama, lang={ocr_lang})"
                if not title or title == path.stem.replace("_", " ").replace("-", " "):
                    first_line = next((l.strip() for l in ocr_text.splitlines() if l.strip()), "")
                    if first_line:
                        title = first_line[:120]
            else:
                result["status"] = "NO_TEXT_LAYER (OCR tidak menghasilkan teks -- kemungkinan tulisan tangan atau scan buram)"
        elif not full_text.strip() and not use_ocr:
            result["status"] = "NO_TEXT_LAYER (mungkin PDF hasil scan -- aktifkan opsi OCR)"

        result["title"] = title
        result["keywords"] = extract_keywords(full_text, top_n=12)
        result["text_sample"] = full_text[:500].replace("\n", " ").strip()
        result["_full_text"] = full_text

    except Exception as e:
        result["status"] = f"ERROR: {e}"
        result["_full_text"] = ""

    return result


# ---------------------------------------------------------------------------
# Database (SQLite FTS5)
# ---------------------------------------------------------------------------

def ensure_db(db_path: Path) -> sqlite3.Connection:
    """Siapkan database. Kalau .db sudah ada, tidak dihapus (fitur resume)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS catalog USING fts5(
            filename, path, title, author, year, keywords, full_text,
            pages UNINDEXED, size_kb UNINDEXED, status UNINDEXED,
            tokenize = 'porter unicode61'
        )
    """)
    conn.commit()
    return conn


def get_already_processed_paths(conn: sqlite3.Connection) -> set:
    cur = conn.cursor()
    cur.execute("SELECT path FROM catalog")
    return {row[0] for row in cur.fetchall()}


def insert_record(conn: sqlite3.Connection, r: dict):
    """Simpan satu hasil baca PDF, commit langsung (kunci fitur resume)."""
    conn.execute(
        "INSERT INTO catalog (filename, path, title, author, year, keywords, full_text, "
        "pages, size_kb, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (r["filename"], r["path"], r["title"], r["author"], r["year"],
         r["keywords"], r.get("_full_text", ""), r["pages"], r["size_kb"], r["status"]),
    )
    conn.commit()


def export_excel_from_db(conn: sqlite3.Connection, output_path: str) -> int:
    """Bangun ulang file Excel dari seluruh isi database saat ini."""
    cur = conn.cursor()
    cur.execute("SELECT filename, title, author, year, pages, size_kb, keywords, "
                "full_text, status, path FROM catalog")
    rows = cur.fetchall()
    cols = ["filename", "title", "author", "year", "pages", "size_kb",
            "keywords", "full_text", "status", "path"]

    df = pd.DataFrame(rows, columns=cols)
    df["full_text"] = df["full_text"].apply(sanitize_for_excel)
    df["text_sample"] = df["full_text"].apply(lambda t: (t or "")[:500].replace("\n", " ").strip())
    df = df.drop(columns=["full_text"])
    df = df[["filename", "title", "author", "year", "pages", "size_kb",
              "keywords", "text_sample", "status", "path"]]

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(sanitize_for_excel)

    wb = Workbook()
    ws = wb.active
    ws.title = "Katalog"
    ws.append(list(df.columns))
    for row_idx, row in enumerate(df.itertuples(index=False), start=2):
        for col_idx, value in enumerate(row, start=1):
            write_cell_safely(ws, row_idx, col_idx, value)
    wb.save(output_path)
    return len(df)


def load_catalog_dataframe(db_path: str) -> pd.DataFrame:
    """Baca ulang seluruh isi database jadi DataFrame pandas -- dipakai bersama
    oleh export_excel_from_db_path() dan export_csv_from_db_path() (dan bisa
    dipakai langsung dari UI untuk generate file in-memory tanpa nulis ke disk).
    Mentolerir database versi lama (tanpa kolom pages/size_kb/status)."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(catalog)")
    available_cols = {row[1] for row in cur.fetchall()}

    has_extra = {"pages", "size_kb", "status"}.issubset(available_cols)
    if has_extra:
        cur.execute("SELECT filename, title, author, year, pages, size_kb, keywords, "
                    "full_text, status, path FROM catalog")
        rows = cur.fetchall()
        cols = ["filename", "title", "author", "year", "pages", "size_kb",
                "keywords", "full_text", "status", "path"]
    else:
        cur.execute("SELECT filename, title, author, year, keywords, full_text, path FROM catalog")
        rows = cur.fetchall()
        cols = ["filename", "title", "author", "year", "keywords", "full_text", "path"]
    conn.close()

    if not rows:
        raise ValueError("Database kosong, tidak ada data untuk di-export. / Database is empty, nothing to export.")

    df = pd.DataFrame(rows, columns=cols)
    df["full_text"] = df["full_text"].apply(sanitize_for_excel)
    df["text_sample"] = df["full_text"].apply(lambda t: (t or "")[:500].replace("\n", " ").strip())
    df = df.drop(columns=["full_text"])

    preferred_order = ["filename", "title", "author", "year", "pages", "size_kb",
                        "keywords", "text_sample", "status", "path"]
    df = df[[c for c in preferred_order if c in df.columns]]
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(sanitize_for_excel)
    return df


def export_excel_from_db_path(db_path: str, output_path: str) -> tuple[int, int]:
    """Sama seperti export_excel_from_db, tapi menerima path .db dan juga
    mentolerir database versi lama (tanpa kolom pages/size_kb/status)."""
    df = load_catalog_dataframe(db_path)

    wb = Workbook()
    ws = wb.active
    ws.title = "Katalog"
    ws.append(list(df.columns))
    n_problem_cells = 0
    for row_idx, row in enumerate(df.itertuples(index=False), start=2):
        for col_idx, value in enumerate(row, start=1):
            if write_cell_safely(ws, row_idx, col_idx, value):
                n_problem_cells += 1
    wb.save(output_path)
    return len(df), n_problem_cells


EXPORT_FORMATS = ("xlsx", "csv", "json", "ods", "tsv", "md")


def dataframe_to_export_bytes(df: pd.DataFrame, fmt: str) -> bytes:
    """Ubah DataFrame katalog jadi bytes sesuai format yang diminta -- dipakai
    bersama oleh CLI (export ke file) dan UI (tombol download). Format yang
    didukung: 'csv', 'tsv', 'json', 'md' (tabel Markdown), 'ods'
    (OpenDocument / LibreOffice Calc). Untuk 'xlsx', dianjurkan tetap pakai
    export_excel_from_db_path() / export_excel_from_db() secara langsung
    (bukan lewat fungsi ini) karena keduanya memakai write_cell_safely yang
    lebih toleran terhadap isi sel bermasalah (misal teks yang diawali "=",
    yang oleh Excel bisa disalahartikan sebagai formula)."""
    if fmt == "csv":
        # utf-8-sig: supaya karakter non-ASCII (misal huruf ber-aksen) tetap
        # tampil benar kalau file-nya dibuka di Excel.
        return df.to_csv(index=False).encode("utf-8-sig")
    if fmt == "tsv":
        return df.to_csv(index=False, sep="\t").encode("utf-8-sig")
    if fmt == "json":
        return df.to_json(orient="records", indent=2, force_ascii=False).encode("utf-8")
    if fmt == "md":
        return df.to_markdown(index=False).encode("utf-8")
    if fmt == "ods":
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="odf")
        return buf.getvalue()
    if fmt == "xlsx":
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        return buf.getvalue()
    raise ValueError(
        f"Format export tidak dikenal: '{fmt}'. Format yang didukung: "
        f"{', '.join(EXPORT_FORMATS)}. / "
        f"Unknown export format: '{fmt}'. Supported formats: {', '.join(EXPORT_FORMATS)}."
    )


def export_csv_from_db_path(db_path: str, output_path: str) -> int:
    """Sama seperti export_excel_from_db_path, tapi hasilnya file .csv --
    lebih ringan dan gampang dibuka di tool lain (Google Sheets, database,
    dll) tanpa perlu Excel."""
    df = load_catalog_dataframe(db_path)
    Path(output_path).write_bytes(dataframe_to_export_bytes(df, "csv"))
    return len(df)


# ---------------------------------------------------------------------------
# Build catalog (orkestrasi build_catalog.py)
# ---------------------------------------------------------------------------

@dataclass
class BuildResult:
    total_found: int = 0
    n_skipped: int = 0
    n_processed: int = 0
    n_rows_in_excel: int = 0
    interrupted: bool = False
    errors: list = field(default_factory=list)


def list_pdfs(folder) -> list[Path]:
    root = Path(folder).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Folder tidak ditemukan / Folder not found: {root}")
    pdf_files = sorted(root.rglob("*.pdf")) + sorted(root.rglob("*.PDF"))
    return list(dict.fromkeys(pdf_files))


def build_catalog(
    folder: str,
    output: str = "katalog_pdf.xlsx",
    db: str = "katalog_pdf.db",
    max_pages: int = 20,
    use_ocr: bool = False,
    ocr_lang: str = "eng",
    ocr_max_pages: int = 5,
    ocr_dpi: int = 200,
    fresh: bool = False,
    progress_cb: Optional[Callable[[int, int, Path], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> BuildResult:
    """Scan folder, ekstrak metadata+teks tiap PDF, simpan ke db (resumable),
    lalu export ulang Excel dari seluruh isi db.

    progress_cb(done, total, current_path) dipanggil setiap 1 file selesai --
    dipakai UI untuk update progress bar.
    should_stop() dipanggil tiap iterasi; kalau return True, proses berhenti
    dengan aman (hasil sejauh ini tetap sudah tersimpan di db, resumable).
    """
    if use_ocr and not OCR_AVAILABLE:
        raise RuntimeError(
            "OCR diaktifkan tapi library belum terinstall. Jalankan: "
            "pip install pytesseract pdf2image, dan pastikan tesseract-ocr terinstall di sistem (lihat README). / "
            "OCR is enabled but the library isn't installed. Run: pip install pytesseract pdf2image, "
            "and make sure tesseract-ocr is installed on your system (see README)."
        )

    pdf_files = list_pdfs(folder)
    if not pdf_files:
        raise FileNotFoundError(f"Tidak ada file PDF ditemukan di / No PDF files found in: {folder}")

    db_path = Path(db)
    if fresh and db_path.exists():
        db_path.unlink()

    conn = ensure_db(db_path)
    already_done = get_already_processed_paths(conn)
    to_process = [p for p in pdf_files if str(p) not in already_done]
    n_skipped = len(pdf_files) - len(to_process)

    result = BuildResult(total_found=len(pdf_files), n_skipped=n_skipped)

    total = len(to_process)
    for i, path in enumerate(to_process, start=1):
        if should_stop is not None and should_stop():
            result.interrupted = True
            break
        record = read_pdf(
            path, max_pages,
            use_ocr=use_ocr, ocr_lang=ocr_lang,
            ocr_max_pages=ocr_max_pages, ocr_dpi=ocr_dpi,
        )
        insert_record(conn, record)
        result.n_processed += 1
        if record["status"].startswith("ERROR"):
            result.errors.append((str(path), record["status"]))
        if progress_cb is not None:
            progress_cb(i, total, path)

    try:
        result.n_rows_in_excel = export_excel_from_db(conn, output)
    finally:
        conn.close()

    return result


# ---------------------------------------------------------------------------
# Search (orkestrasi search_catalog.py)
# ---------------------------------------------------------------------------

def search_catalog(db_path: str, query: str, limit: int = 15) -> list[dict]:
    if not Path(db_path).exists():
        raise FileNotFoundError(f"File index tidak ditemukan / Index file not found: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql = """
        SELECT filename, path, title, author, year,
               snippet(catalog, 6, '[', ']', '...', 12) AS snippet,
               bm25(catalog) AS score
        FROM catalog
        WHERE catalog MATCH ?
        ORDER BY score
        LIMIT ?
    """
    try:
        cur.execute(sql, (query, limit))
    except sqlite3.OperationalError as e:
        conn.close()
        raise ValueError(
            f"Query tidak valid untuk pencarian ({e}). Tips: gunakan kata biasa, atau "
            f"\"frasa persis\" dengan tanda kutip, atau operator AND/OR/NOT (huruf besar). / "
            f"Invalid search query ({e}). Tip: use plain words, an \"exact phrase\" in quotes, "
            f"or the AND/OR/NOT operators (uppercase)."
        )
    rows = cur.fetchall()
    conn.close()

    results = []
    for filename, path, title, author, year, snippet, score in rows:
        results.append({
            "judul": title or filename,
            "penulis": author,
            "tahun": year,
            "cuplikan_relevan": (snippet or "").replace("\n", " ").strip(),
            "nama_file": filename,
            "path_lengkap": path,
            "skor": score,
        })
    return results


def save_search_results_to_excel(results: list[dict], output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Hasil Pencarian"
    headers = ["no", "judul", "penulis", "tahun", "cuplikan_relevan", "nama_file", "path_lengkap"]
    ws.append(headers)
    for i, r in enumerate(results, 1):
        values = [i, r["judul"], r["penulis"], r["tahun"], r["cuplikan_relevan"],
                   r["nama_file"], r["path_lengkap"]]
        for col_idx, value in enumerate(values, 1):
            write_cell_safely(ws, i + 1, col_idx, value)
    wb.save(output_path)


# ---------------------------------------------------------------------------
# Duplikat (orkestrasi find_duplicates.py)
# ---------------------------------------------------------------------------

@dataclass
class DuplicateResult:
    total_checked: int = 0
    groups: list = field(default_factory=list)  # list of list[dict]
    total_wasted_kb: float = 0.0
    errors: list = field(default_factory=list)


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_duplicates(
    folder: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> DuplicateResult:
    pdf_files = list_pdfs(folder)
    if not pdf_files:
        raise FileNotFoundError(f"Tidak ada file PDF ditemukan di / No PDF files found in: {folder}")

    groups: dict = {}
    errors = []
    for i, path in enumerate(pdf_files, 1):
        try:
            h = hash_file(path)
            groups.setdefault(h, []).append(path)
        except Exception as e:
            errors.append((str(path), str(e)))
        if progress_cb is not None:
            progress_cb(i, len(pdf_files))

    duplicate_groups = {h: paths for h, paths in groups.items() if len(paths) > 1}

    result = DuplicateResult(total_checked=len(pdf_files), errors=errors)
    total_wasted_kb = 0.0
    for group_id, (h, paths) in enumerate(duplicate_groups.items(), 1):
        paths_sorted = sorted(paths, key=lambda p: p.stat().st_mtime)
        size_kb = round(paths_sorted[0].stat().st_size / 1024, 1)
        total_wasted_kb += size_kb * (len(paths_sorted) - 1)

        group_rows = []
        for idx, p in enumerate(paths_sorted):
            group_rows.append({
                "grup_duplikat": group_id,
                "jumlah_salinan": len(paths_sorted),
                "status_saran": "simpan (paling lama)" if idx == 0 else "kandidat dihapus",
                "nama_file": p.name,
                "ukuran_kb": size_kb,
                "path_lengkap": str(p),
            })
        result.groups.append(group_rows)

    result.total_wasted_kb = total_wasted_kb
    return result


def duplicates_to_dataframe(result: DuplicateResult) -> pd.DataFrame:
    rows = [row for group in result.groups for row in group]
    return pd.DataFrame(rows, columns=[
        "grup_duplikat", "jumlah_salinan", "status_saran", "nama_file", "ukuran_kb", "path_lengkap",
    ])


# ---------------------------------------------------------------------------
# Streamlit first-run helper
# ---------------------------------------------------------------------------

def ensure_streamlit_no_prompt():
    """Streamlit menampilkan prompt "masukkan email" di layar pertama kali dia
    dijalankan di suatu komputer (sekali saja, lalu diingat lewat file
    ~/.streamlit/credentials.toml). Untuk orang yang pakai versi .exe
    standalone, prompt itu bisa bikin bingung (kelihatan seperti aplikasi
    'macet' padahal cuma menunggu input). Fungsi ini menulis file itu duluan
    dengan email kosong, supaya prompt-nya tidak pernah muncul."""
    config_dir = Path.home() / ".streamlit"
    creds_path = config_dir / "credentials.toml"
    if creds_path.exists():
        return
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        creds_path.write_text('[general]\nemail = ""\n')
    except OSError:
        pass  # tidak fatal -- kalau gagal, paling banter prompt tetap muncul
