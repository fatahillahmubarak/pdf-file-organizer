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

import difflib
import hashlib
import io
import itertools
import json
import re
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
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
# Deteksi DOI/ISBN & saran rename otomatis -- otomatisasi dari langkah yang
# sebelumnya dikerjakan manual (riset DOI lewat Crossref, ISBN lewat Google
# Books, lalu susun nama file) di project "Rename File".
# ---------------------------------------------------------------------------

DOI_RE = re.compile(r'\b10\.\d{4,9}/[^\s"<>\)\]]+', re.IGNORECASE)
ISBN_RE = re.compile(
    r'\bISBN(?:-1[03])?\s*[:\s]*((?:97[89][-\s]?)?(?:\d[-\s]?){9}[\dXx])\b',
    re.IGNORECASE,
)


def extract_doi(text: str) -> str:
    """Cari DOI pertama yang masuk akal (pola resmi 10.xxxx/...) di teks bebas."""
    if not text:
        return ""
    match = DOI_RE.search(text)
    if not match:
        return ""
    return match.group(0).rstrip(".,;:)]}>\"'").lower()


def extract_isbn(text: str) -> str:
    """Cari ISBN-10/13 di teks bebas (butuh label 'ISBN' di depannya supaya
    tidak salah tangkap nomor lain). Hasil dinormalisasi (tanpa strip/spasi)."""
    if not text:
        return ""
    match = ISBN_RE.search(text)
    if not match:
        return ""
    digits = re.sub(r"[-\s]", "", match.group(1))
    if len(digits) in (10, 13):
        return digits.upper()
    return ""


def _sanitize_filename_piece(value: str, max_len: int = 150) -> str:
    """Buang karakter yang tidak boleh ada di nama file Windows/macOS/Linux."""
    value = re.sub(r'[\\/:*?"<>|]', "", value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:max_len].rstrip(" .")


def build_suggested_filename(doc_type: str, authors: str, year: str, title: str) -> str:
    """Susun nama file sesuai konvensi TYPE_(Author, Year)_Judul yang dipakai
    manual di batch-1/batch-2 project Rename File."""
    author_part = _sanitize_filename_piece(authors, 80) or "Unknown"
    year_part = _sanitize_filename_piece(year, 12) or "n.d."
    title_part = _sanitize_filename_piece(title) or "Untitled"
    doc_type = doc_type or "PAPER"
    return f"{doc_type}_({author_part}, {year_part})_{title_part}"


def lookup_crossref(doi: str, contact_email: Optional[str] = None, timeout: float = 8.0) -> Optional[dict]:
    """Cari metadata via Crossref API (gratis, tanpa API key). contact_email
    opsional tapi disarankan Crossref supaya request masuk 'polite pool'
    (lebih jarang di-rate-limit) -- lihat https://api.crossref.org."""
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    if contact_email:
        url += f"?mailto={urllib.parse.quote(contact_email)}"
    headers = {"User-Agent": f"katalog-pdf/0.2 (mailto:{contact_email or 'unknown@example.com'})"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    msg = data.get("message") or {}
    author_list = msg.get("author") or []
    author_names = ", ".join(a["family"].strip() for a in author_list if a.get("family"))
    if not author_names:
        author_names = ", ".join(a.get("name", "") for a in author_list if a.get("name"))

    year = ""
    for key in ("published-print", "published-online", "published", "issued"):
        parts = (msg.get(key) or {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            year = str(parts[0][0])
            break

    title = (msg.get("title") or [""])[0].strip()
    work_type = msg.get("type", "")
    if work_type in ("book", "monograph", "reference-book", "edited-book"):
        doc_type = "BOOK"
    elif work_type in ("book-chapter", "book-section", "book-part"):
        doc_type = "BOOK_CHAPTER"
    else:
        doc_type = "PAPER"

    if not title:
        return None
    return {"author": author_names, "year": year, "title": title, "type": doc_type, "source": "crossref"}


def lookup_google_books(isbn: str, timeout: float = 8.0) -> Optional[dict]:
    """Cari metadata via Google Books API (gratis, tanpa API key, tapi punya
    rate limit per-IP -- makanya dipanggil dengan jeda, lihat lookup_delay di
    suggest_renames())."""
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{urllib.parse.quote(isbn)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    items = data.get("items") or []
    if not items:
        return None
    info = items[0].get("volumeInfo", {})
    authors = info.get("authors") or []
    author_names = ", ".join(a.split()[-1] if " " in a else a for a in authors)
    year = (info.get("publishedDate") or "")[:4]
    title = (info.get("title") or "").strip()
    if info.get("subtitle"):
        title = f"{title}: {info['subtitle']}".strip()
    if not title:
        return None
    return {"author": author_names, "year": year, "title": title, "type": "BOOK", "source": "google_books"}


@dataclass
class RenameSuggestion:
    path: str = ""
    filename: str = ""
    doc_type: str = ""
    authors: str = ""
    year: str = ""
    title: str = ""
    doi: str = ""
    isbn: str = ""
    confidence: str = "Low"
    source: str = ""
    suggested_filename: str = ""
    notes: str = ""


@dataclass
class RenameSuggestionResult:
    total_found: int = 0
    suggestions: list = field(default_factory=list)  # list[RenameSuggestion]
    n_high: int = 0
    n_medium: int = 0
    n_low: int = 0
    interrupted: bool = False
    errors: list = field(default_factory=list)


def suggest_renames(
    folder: str,
    max_pages: int = 25,
    use_ocr: bool = False,
    ocr_lang: str = "eng",
    ocr_max_pages: int = 5,
    ocr_dpi: int = 200,
    contact_email: Optional[str] = None,
    lookup_delay: float = 0.3,
    progress_cb: Optional[Callable[[int, int, Path], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> RenameSuggestionResult:
    """Scan folder, deteksi DOI/ISBN tiap PDF, cocokkan ke Crossref/Google
    Books buat dapat penulis/tahun/judul yang akurat, lalu usulkan nama file
    format TYPE_(Author, Year)_Judul.

    Untuk PDF yang tidak punya DOI/ISBN yang bisa ditemukan/dicocokkan
    (banyak dijumpai di buku lama, scan buram, atau judul berbahasa asing),
    hasilnya ditandai confidence "Low" dan PERLU DICEK MANUAL -- fungsi ini
    TIDAK menebak-nebak lewat riset web seperti yang dibantu Claude secara
    manual di batch-1/batch-2. Tidak ada file yang benar-benar di-rename di
    sini -- lihat write_rename_powershell_script() untuk itu.
    """
    pdf_files = list_pdfs(folder)
    if not pdf_files:
        raise FileNotFoundError(f"Tidak ada file PDF ditemukan di / No PDF files found in: {folder}")

    result = RenameSuggestionResult(total_found=len(pdf_files))
    seen_titles: dict = {}

    for i, path in enumerate(pdf_files, start=1):
        if should_stop is not None and should_stop():
            result.interrupted = True
            break

        sugg = RenameSuggestion(path=str(path), filename=path.name)
        try:
            rec = read_pdf(
                path, max_pages, use_ocr=use_ocr, ocr_lang=ocr_lang,
                ocr_max_pages=ocr_max_pages, ocr_dpi=ocr_dpi,
            )
            full_text = rec.get("_full_text", "")

            doi = extract_doi(full_text) or extract_doi(path.name)
            isbn = extract_isbn(full_text) or extract_isbn(path.name)
            sugg.doi, sugg.isbn = doi, isbn

            meta = None
            if doi:
                meta = lookup_crossref(doi, contact_email=contact_email)
                time.sleep(lookup_delay)
            if not meta and isbn:
                meta = lookup_google_books(isbn)
                time.sleep(lookup_delay)

            if meta:
                sugg.doc_type = meta["type"]
                sugg.authors = meta["author"] or "Unknown"
                sugg.year = meta["year"]
                sugg.title = meta["title"]
                sugg.source = meta["source"]
                sugg.confidence = "High" if (meta["author"] and meta["year"]) else "Medium"
                if not meta["year"]:
                    sugg.notes = "Tahun tidak ditemukan di hasil lookup -- cek manual"
            else:
                sugg.doc_type = "BOOK" if rec["pages"] > 60 else "PAPER"
                sugg.authors = rec["author"] or ""
                sugg.year = rec["year"] or ""
                sugg.title = rec["title"] or path.stem.replace("_", " ").replace("-", " ")
                sugg.confidence = "Low"
                reason = "tidak ada DOI/ISBN yang terdeteksi" if not (doi or isbn) \
                    else "DOI/ISBN terdeteksi tapi tidak ketemu di Crossref/Google Books"
                sugg.notes = f"PERLU VERIFIKASI MANUAL ({reason})"

            norm_title = re.sub(r"[^a-z0-9]+", "", sugg.title.lower())
            if norm_title:
                if norm_title in seen_titles and seen_titles[norm_title] != sugg.filename:
                    dup_note = f"KEMUNGKINAN DUPLIKAT dari: {seen_titles[norm_title]}"
                    sugg.notes = f"{sugg.notes} | {dup_note}" if sugg.notes else dup_note
                else:
                    seen_titles[norm_title] = sugg.filename

            sugg.suggested_filename = build_suggested_filename(
                sugg.doc_type, sugg.authors, sugg.year, sugg.title
            ) + path.suffix

        except Exception as e:
            sugg.notes = f"ERROR: {e}"
            sugg.confidence = "Low"
            result.errors.append((str(path), str(e)))

        result.suggestions.append(sugg)
        if sugg.confidence == "High":
            result.n_high += 1
        elif sugg.confidence == "Medium":
            result.n_medium += 1
        else:
            result.n_low += 1

        if progress_cb is not None:
            progress_cb(i, len(pdf_files), path)

    return result


def rename_suggestions_to_dataframe(result: RenameSuggestionResult) -> pd.DataFrame:
    rows = [
        {
            "nama_file_asli": s.filename, "tipe": s.doc_type, "penulis": s.authors,
            "tahun": s.year, "judul": s.title, "doi": s.doi, "isbn": s.isbn,
            "confidence": s.confidence, "nama_file_usulan": s.suggested_filename,
            "catatan": s.notes, "sumber": s.source, "path_lengkap": s.path,
        }
        for s in result.suggestions
    ]
    return pd.DataFrame(rows, columns=[
        "nama_file_asli", "tipe", "penulis", "tahun", "judul", "doi", "isbn",
        "confidence", "nama_file_usulan", "catatan", "sumber", "path_lengkap",
    ])


def save_rename_suggestions_to_excel(result: RenameSuggestionResult, output_path: str) -> int:
    df = rename_suggestions_to_dataframe(result)
    wb = Workbook()
    ws = wb.active
    ws.title = "Saran Rename"
    ws.append(list(df.columns))
    for row_idx, row in enumerate(df.itertuples(index=False), start=2):
        for col_idx, value in enumerate(row, start=1):
            write_cell_safely(ws, row_idx, col_idx, sanitize_for_excel(value))
    wb.save(output_path)
    return len(df)


def write_rename_powershell_script(
    result: RenameSuggestionResult, output_path: str, min_confidence: str = "High",
) -> int:
    """Tulis script PowerShell (Rename-Item, tanpa transfer isi file) untuk
    baris dengan confidence >= min_confidence saja. SELALU review dulu isi
    script-nya sebelum dijalankan -- ini cuma USULAN, bukan eksekusi otomatis."""
    order = {"Low": 1, "Medium": 2, "High": 3}
    threshold = order.get(min_confidence, 3)
    lines = [
        "# Auto-generated oleh katalog-pdf (suggest-renames) -- REVIEW dulu isinya",
        "# sebelum dijalankan! Setiap baris cuma me-rename di tempat (nama folder",
        "# tidak berubah), tidak ada isi file yang diubah/dipindah.",
        "",
    ]
    n = 0
    for s in result.suggestions:
        if order.get(s.confidence, 0) < threshold or not s.suggested_filename:
            continue
        old_path = str(Path(s.path))
        new_name = s.suggested_filename.replace('"', "'")
        lines.append(f'Rename-Item -LiteralPath "{old_path}" -NewName "{new_name}"')
        n += 1
    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n


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
# Duplikat MIRIP berdasarkan isi teks (bukan hash exact) -- menangkap kasus
# scan/edisi berbeda dari buku yang sama yang tidak akan ketahuan oleh
# find_duplicates() karena isi filenya secara byte tidak identik. Pola ini
# sebelumnya dipakai manual (fuzzy text-similarity) di project "Rename File".
# ---------------------------------------------------------------------------

@dataclass
class NearDuplicateResult:
    total_checked: int = 0
    groups: list = field(default_factory=list)  # list of list[dict]
    errors: list = field(default_factory=list)


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).quick_ratio()


def find_near_duplicates(
    folder: str,
    max_pages: int = 10,
    use_ocr: bool = False,
    ocr_lang: str = "eng",
    min_shared_keywords: int = 2,
    similarity_threshold: float = 0.6,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> NearDuplicateResult:
    """Bandingkan ISI (bukan hash) tiap PDF buat cari kemungkinan duplikat
    yang byte-nya berbeda -- misal buku yang sama di-scan dua kali dengan
    kualitas beda, atau edisi cetak ulang yang isinya nyaris sama.

    Supaya tidak harus membandingkan setiap pasang file satu-per-satu (bisa
    sangat lambat untuk koleksi besar), file dikelompokkan dulu lewat kata
    kunci yang sama (inverted index, mirip cara mesin pencari bekerja) --
    baru pasangan yang berbagi minimal `min_shared_keywords` kata kunci
    diperiksa lebih detail lewat kemiripan teks (difflib). Ini heuristik,
    bukan jaminan 100% -- selalu cek manual sebelum menghapus apa pun,
    terutama kalau jumlah halaman kedua file berbeda jauh (ditandai di
    kolom 'catatan').
    """
    pdf_files = list_pdfs(folder)
    if not pdf_files:
        raise FileNotFoundError(f"Tidak ada file PDF ditemukan di / No PDF files found in: {folder}")

    docs = []
    errors = []
    for i, path in enumerate(pdf_files, start=1):
        try:
            rec = read_pdf(path, max_pages, use_ocr=use_ocr, ocr_lang=ocr_lang)
            keywords = {k.strip() for k in rec["keywords"].split(",") if k.strip()}
            docs.append({
                "path": path,
                "pages": rec["pages"],
                "size_kb": rec["size_kb"],
                "title": rec["title"],
                "keywords": keywords,
                "text": rec.get("_full_text", "")[:4000],
            })
        except Exception as e:
            errors.append((str(path), str(e)))
        if progress_cb is not None:
            progress_cb(i, len(pdf_files))

    # Inverted index: kata kunci -> indeks dokumen yang mengandungnya. Kata
    # kunci yang muncul di terlalu banyak dokumen (>50) dianggap tidak
    # distingtif (misal "abstract", "chapter") dan dilewati.
    inverted: dict = defaultdict(set)
    for idx, d in enumerate(docs):
        for kw in d["keywords"]:
            inverted[kw].add(idx)

    shared_count: dict = defaultdict(int)
    for kw, idxs in inverted.items():
        if len(idxs) < 2 or len(idxs) > 50:
            continue
        for a, b in itertools.combinations(sorted(idxs), 2):
            shared_count[(a, b)] += 1

    # Union-find sederhana buat gabungkan pasangan yang mirip jadi satu grup
    # (misal A mirip B, B mirip C -> A, B, C jadi satu grup).
    parent = list(range(len(docs)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for (a, b), n_shared in shared_count.items():
        if n_shared < min_shared_keywords:
            continue
        if _text_similarity(docs[a]["text"], docs[b]["text"]) >= similarity_threshold:
            union(a, b)

    clusters: dict = defaultdict(list)
    for idx in range(len(docs)):
        clusters[find(idx)].append(idx)

    result = NearDuplicateResult(total_checked=len(docs), errors=errors)
    group_id = 0
    for idxs in clusters.values():
        if len(idxs) < 2:
            continue
        group_id += 1
        idxs_sorted = sorted(idxs, key=lambda i: (-docs[i]["pages"], docs[i]["path"].stat().st_mtime))
        ref_pages = docs[idxs_sorted[0]]["pages"]
        group_rows = []
        for rank, idx in enumerate(idxs_sorted):
            d = docs[idx]
            page_note = "" if d["pages"] == ref_pages else \
                f"⚠ jumlah halaman beda ({d['pages']} vs {ref_pages}) -- cek manual dulu"
            group_rows.append({
                "grup_mirip": group_id,
                "jumlah_salinan": len(idxs_sorted),
                "status_saran": "kandidat simpan" if rank == 0 else "cek sebelum dihapus",
                "nama_file": d["path"].name,
                "judul_terdeteksi": d["title"],
                "halaman": d["pages"],
                "ukuran_kb": d["size_kb"],
                "catatan": page_note,
                "path_lengkap": str(d["path"]),
            })
        result.groups.append(group_rows)

    return result


def near_duplicates_to_dataframe(result: NearDuplicateResult) -> pd.DataFrame:
    rows = [row for group in result.groups for row in group]
    return pd.DataFrame(rows, columns=[
        "grup_mirip", "jumlah_salinan", "status_saran", "nama_file", "judul_terdeteksi",
        "halaman", "ukuran_kb", "catatan", "path_lengkap",
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
