#!/usr/bin/env python3
"""
app.py
======
UI Streamlit untuk katalog_pdf (Bahasa Indonesia & English). Jalankan dengan:

    streamlit run app.py
    # atau, setelah "pip install katalog-pdf":
    katalog-pdf ui

Semua logika berat ada di core.py -- file ini murni tampilan & interaksi.
Teks UI ada di i18n.py -- lihat file itu untuk menambah bahasa baru.
"""

import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from katalog_pdf import core
from katalog_pdf.i18n import TRANSLATIONS, LANGUAGES

# Nama bahasa OCR ditulis dalam bahasa aslinya masing-masing (endonim), jadi
# tidak perlu diterjemahkan ulang -- tetap masuk akal dibaca di UI Indonesia
# maupun English. Kode di sebelah kiri harus kode Tesseract yang valid.
OCR_LANGUAGE_OPTIONS = [
    ("eng", "English"),
    ("ind", "Bahasa Indonesia"),
    ("nld", "Nederlands (Dutch)"),
    ("lat", "Latin"),
    ("deu", "Deutsch (German)"),
    ("fra", "Français (French)"),
    ("spa", "Español (Spanish)"),
    ("por", "Português (Portuguese)"),
    ("ara", "العربية (Arabic)"),
    ("chi_sim", "中文 (Chinese Simplified)"),
    ("jpn", "日本語 (Japanese)"),
    ("kor", "한국어 (Korean)"),
]

# Urutan & MIME type format export yang ditawarkan di tombol download tiap
# tab. "xlsx" ditaruh paling pertama karena paling umum dipakai; sisanya
# (core.EXPORT_FORMATS) dihasilkan lewat core.dataframe_to_export_bytes().
EXPORT_FORMAT_ORDER = list(core.EXPORT_FORMATS)
EXPORT_MIME = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "json": "application/json",
    "md": "text/markdown",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
}

# ---------------------------------------------------------------------------
# Bahasa / Language
# ---------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state["lang"] = "id"

st.set_page_config(page_title="Katalog PDF / PDF Catalog", page_icon="📚", layout="wide")

_lang_codes = list(LANGUAGES.keys())
_top_left, _top_right = st.columns([5, 1])
with _top_right:
    st.session_state["lang"] = st.selectbox(
        "🌐", options=_lang_codes, format_func=lambda k: LANGUAGES[k],
        index=_lang_codes.index(st.session_state["lang"]), key="lang_selector",
        label_visibility="collapsed",
    )

LANG = st.session_state["lang"]
T = TRANSLATIONS[LANG]

# Terjemahan kolom tabel hasil (data mentahnya dari core.py selalu berbahasa
# Indonesia -- ini cuma label tampilan, bukan mengubah data aslinya).
_SEARCH_COLS = {
    "id": {"judul": "judul", "penulis": "penulis", "tahun": "tahun",
           "cuplikan_relevan": "cuplikan_relevan", "nama_file": "nama_file", "path_lengkap": "path_lengkap"},
    "en": {"judul": "title", "penulis": "author", "tahun": "year",
           "cuplikan_relevan": "snippet", "nama_file": "file_name", "path_lengkap": "full_path"},
}
_DUP_COLS = {
    "id": {"grup_duplikat": "grup_duplikat", "jumlah_salinan": "jumlah_salinan",
           "status_saran": "status_saran", "nama_file": "nama_file",
           "ukuran_kb": "ukuran_kb", "path_lengkap": "path_lengkap"},
    "en": {"grup_duplikat": "group", "jumlah_salinan": "copies",
           "status_saran": "suggested_status", "nama_file": "file_name",
           "ukuran_kb": "size_kb", "path_lengkap": "full_path"},
}
_DUP_STATUS = {
    "simpan (paling lama)": {"id": "simpan (paling lama)", "en": "keep (oldest)"},
    "kandidat dihapus": {"id": "kandidat dihapus", "en": "deletion candidate"},
}
_NEAR_DUP_COLS = {
    "id": {"grup_mirip": "grup_mirip", "jumlah_salinan": "jumlah_salinan",
           "status_saran": "status_saran", "nama_file": "nama_file",
           "judul_terdeteksi": "judul_terdeteksi", "halaman": "halaman",
           "ukuran_kb": "ukuran_kb", "catatan": "catatan", "path_lengkap": "path_lengkap"},
    "en": {"grup_mirip": "similar_group", "jumlah_salinan": "copies",
           "status_saran": "suggested_status", "nama_file": "file_name",
           "judul_terdeteksi": "detected_title", "halaman": "pages",
           "ukuran_kb": "size_kb", "catatan": "note", "path_lengkap": "full_path"},
}
_NEAR_DUP_STATUS = {
    "kandidat simpan": {"id": "kandidat simpan", "en": "candidate to keep"},
    "cek sebelum dihapus": {"id": "cek sebelum dihapus", "en": "check before deleting"},
}


def _localize_search_df(results: list) -> pd.DataFrame:
    df = pd.DataFrame(results)[["judul", "penulis", "tahun", "cuplikan_relevan", "nama_file", "path_lengkap"]]
    return df.rename(columns=_SEARCH_COLS[LANG])


def _localize_dup_df(result) -> pd.DataFrame:
    df = core.duplicates_to_dataframe(result)
    df["status_saran"] = df["status_saran"].map(lambda s: _DUP_STATUS.get(s, {}).get(LANG, s))
    return df.rename(columns=_DUP_COLS[LANG])


def _localize_near_dup_df(result) -> pd.DataFrame:
    df = core.near_duplicates_to_dataframe(result)
    df["status_saran"] = df["status_saran"].map(lambda s: _NEAR_DUP_STATUS.get(s, {}).get(LANG, s))
    return df.rename(columns=_NEAR_DUP_COLS[LANG])


def _read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def _export_format_picker(key: str) -> str:
    TC = T["common"]
    return st.selectbox(
        TC["export_format_label"], options=EXPORT_FORMAT_ORDER,
        format_func=lambda f: TC["export_format_names"][f],
        key=key,
    )


def _df_to_export_bytes(df: pd.DataFrame, fmt: str) -> bytes:
    if fmt == "xlsx":
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        return buf.getvalue()
    return core.dataframe_to_export_bytes(df, fmt)


def _export_download_button(df: pd.DataFrame, fmt: str, base_filename: str, key: str):
    TC = T["common"]
    data = _df_to_export_bytes(df, fmt)
    st.download_button(
        TC["export_download_button"].format(format=TC["export_format_names"][fmt]),
        data=data, file_name=f"{base_filename}.{fmt}", mime=EXPORT_MIME[fmt], key=key,
    )


with _top_left:
    st.title(T["common"]["app_title"])
st.caption(T["common"]["app_caption"])

tab_build, tab_search, tab_dup, tab_rename, tab_help = st.tabs(
    [T["common"]["tab_build"], T["common"]["tab_search"], T["common"]["tab_dup"],
     T["common"]["tab_rename"], T["common"]["tab_help"]]
)

# ---------------------------------------------------------------------------
# TAB 1: Bangun Katalog / Build Catalog
# ---------------------------------------------------------------------------
with tab_build:
    TB = T["build"]
    st.subheader(TB["subheader"])
    st.write(TB["description"])

    col1, col2 = st.columns(2)
    with col1:
        folder = st.text_input(TB["folder_label"], key="build_folder", placeholder=TB["folder_placeholder"])
        output_xlsx = st.text_input(TB["output_label"], value="katalog_pdf.xlsx", key="build_output")
    with col2:
        db_path = st.text_input(TB["db_label"], value="katalog_pdf.db", key="build_db")
        fresh = st.checkbox(TB["fresh_label"], value=False, key="build_fresh", help=TB["fresh_help"])

    with st.expander(TB["advanced_expander"]):
        max_pages = st.slider(TB["max_pages_label"], 5, 100, 20, key="build_max_pages")
        use_ocr = st.checkbox(
            TB["ocr_checkbox_label"],
            value=False, key="build_ocr", disabled=not core.OCR_AVAILABLE,
        )
        if not core.OCR_AVAILABLE:
            st.caption(TB["ocr_unavailable_caption"])
        ocr_lang_codes = st.multiselect(
            TB["ocr_lang_label"],
            options=[code for code, _ in OCR_LANGUAGE_OPTIONS],
            default=["eng"],
            format_func=lambda code: dict(OCR_LANGUAGE_OPTIONS).get(code, code),
            key="build_ocr_lang_multiselect",
            disabled=not use_ocr,
            help=TB["ocr_lang_help"],
        )
        ocr_lang_custom = st.text_input(
            TB["ocr_lang_custom_label"], value="", key="build_ocr_lang_custom",
            disabled=not use_ocr, help=TB["ocr_lang_custom_help"],
        )
        ocr_lang = ocr_lang_custom.strip() or "+".join(ocr_lang_codes) or "eng"
        ocr_max_pages = st.slider(TB["ocr_max_pages_label"], 1, 20, 5, key="build_ocr_max_pages",
                                   disabled=not use_ocr)
        ocr_dpi = st.slider(TB["ocr_dpi_label"], 100, 400, 200, key="build_ocr_dpi", disabled=not use_ocr)

    start = st.button(TB["start_button"], type="primary", key="build_start")

    if start:
        if not folder.strip():
            st.error(TB["error_empty_folder"])
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def progress_cb(done, total, path):
                progress_bar.progress(done / total if total else 1.0)
                status_text.text(TB["progress_processing"].format(done=done, total=total, name=path.name))

            try:
                with st.spinner(TB["spinner_text"]):
                    result = core.build_catalog(
                        folder, output=output_xlsx, db=db_path, max_pages=max_pages,
                        use_ocr=use_ocr, ocr_lang=ocr_lang, ocr_max_pages=ocr_max_pages,
                        ocr_dpi=ocr_dpi, fresh=fresh, progress_cb=progress_cb,
                    )
            except (FileNotFoundError, RuntimeError) as e:
                st.error(str(e))
            else:
                progress_bar.progress(1.0)
                status_text.empty()
                # Simpan hasilnya di session_state (bukan cuma variabel lokal) --
                # supaya tetap tampil setelah rerun, misalnya begitu tombol
                # download di-klik (st.download_button juga memicu rerun seperti
                # tombol biasa, dan tanpa ini seluruh blok "if start:" ini jadi
                # False lagi sehingga hasil & tombol downloadnya hilang).
                st.session_state["_last_build_result"] = result
                st.session_state["_last_build_output_xlsx"] = output_xlsx
                st.session_state["_last_build_db_path"] = db_path

    build_result = st.session_state.get("_last_build_result")
    if build_result is not None:
        st.success(TB["success_text"])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(TB["metric_total_found"], build_result.total_found)
        m2.metric(TB["metric_skipped"], build_result.n_skipped)
        m3.metric(TB["metric_processed"], build_result.n_processed)
        m4.metric(TB["metric_total_rows"], build_result.n_rows_in_excel)

        if build_result.errors:
            with st.expander(TB["errors_expander"].format(count=len(build_result.errors))):
                st.dataframe(pd.DataFrame(build_result.errors, columns=["path", "error"]))

        saved_output_xlsx = st.session_state["_last_build_output_xlsx"]
        saved_db_path = st.session_state["_last_build_db_path"]

        build_fmt = _export_format_picker(key="build_export_format")
        if build_fmt == "xlsx":
            # Format xlsx langsung dari file yang sudah ditulis build_catalog()
            # di disk (lebih aman untuk isi sel bermasalah, lihat catatan di
            # core.dataframe_to_export_bytes), bukan dibuat ulang dari DataFrame.
            st.download_button(
                T["common"]["export_download_button"].format(
                    format=T["common"]["export_format_names"]["xlsx"]),
                data=_read_bytes(saved_output_xlsx),
                file_name=Path(saved_output_xlsx).name,
                mime=EXPORT_MIME["xlsx"],
                key="build_download",
            )
        else:
            try:
                catalog_df = core.load_catalog_dataframe(saved_db_path)
            except (FileNotFoundError, ValueError):
                catalog_df = None
            if catalog_df is not None:
                _export_download_button(
                    catalog_df, build_fmt, Path(saved_output_xlsx).stem, key="build_download",
                )
        st.caption(TB["resume_caption"].format(db_path=saved_db_path))

# ---------------------------------------------------------------------------
# TAB 2: Cari / Search
# ---------------------------------------------------------------------------
with tab_search:
    TS = T["search"]
    st.subheader(TS["subheader"])
    st.write(TS["description"])

    col1, col2 = st.columns([3, 1])
    with col1:
        search_db = st.text_input(TS["db_label"], value="katalog_pdf.db", key="search_db")
    with col2:
        limit = st.number_input(TS["limit_label"], min_value=1, max_value=500, value=15, key="search_limit")

    query = st.text_input(TS["query_label"], key="search_query", placeholder=TS["query_placeholder"])
    st.caption(TS["tips_caption"])

    if st.button(TS["search_button"], type="primary", key="search_start"):
        if not query.strip():
            st.error(TS["error_empty_query"])
        else:
            try:
                results = core.search_catalog(search_db, query, int(limit))
            except (FileNotFoundError, ValueError) as e:
                st.error(str(e))
            else:
                st.session_state["_last_search_results"] = results
                st.session_state["_last_search_query"] = query

    results = st.session_state.get("_last_search_results")
    if results is not None:
        if not results:
            st.info(TS["no_results"].format(query=st.session_state.get("_last_search_query")))
        else:
            st.write(TS["found_count"].format(count=len(results)))
            df = _localize_search_df(results)
            st.dataframe(df, use_container_width=True, hide_index=True)
            search_fmt = _export_format_picker(key="search_export_format")
            _export_download_button(df, search_fmt, "hasil_pencarian", key="search_download")

# ---------------------------------------------------------------------------
# TAB 3: Cari Duplikat / Find Duplicates
# ---------------------------------------------------------------------------
with tab_dup:
    TD = T["dup"]
    st.subheader(TD["subheader"])
    st.write(TD["description"])

    dup_folder = st.text_input(TD["folder_label"], key="dup_folder", placeholder=T["build"]["folder_placeholder"])

    if st.button(TD["button"], type="primary", key="dup_start"):
        if not dup_folder.strip():
            st.error(TD["error_empty_folder"])
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def dup_progress_cb(done, total):
                progress_bar.progress(done / total if total else 1.0)
                status_text.text(TD["progress_checking"].format(done=done, total=total))

            try:
                with st.spinner(TD["spinner_text"]):
                    result = core.find_duplicates(dup_folder, progress_cb=dup_progress_cb)
            except FileNotFoundError as e:
                st.error(str(e))
            else:
                progress_bar.progress(1.0)
                status_text.empty()
                st.session_state["_last_dup_result"] = result

    result = st.session_state.get("_last_dup_result")
    if result is not None:
        m1, m2, m3 = st.columns(3)
        m1.metric(TD["metric_total_checked"], result.total_checked)
        m2.metric(TD["metric_groups_found"], len(result.groups))
        m3.metric(TD["metric_wasted_space"], f"{round(result.total_wasted_kb / 1024, 1)} MB")

        if not result.groups:
            st.success(TD["no_duplicates"])
        else:
            df = _localize_dup_df(result)
            st.dataframe(df, use_container_width=True, hide_index=True)
            dup_fmt = _export_format_picker(key="dup_export_format")
            _export_download_button(df, dup_fmt, "duplikat_pdf", key="dup_download")

        if result.errors:
            with st.expander(TD["errors_expander"].format(count=len(result.errors))):
                st.dataframe(pd.DataFrame(result.errors, columns=["path", "error"]))

    st.divider()
    st.subheader(TD["near_dup_divider_title"])
    st.write(TD["near_dup_description"])

    with st.expander(TD["near_dup_advanced_expander"]):
        near_dup_similarity = st.slider(
            TD["near_dup_similarity_label"], 0.0, 1.0, 0.6, step=0.05,
            key="near_dup_similarity", help=TD["near_dup_similarity_help"],
        )

    if st.button(TD["near_dup_button"], type="primary", key="near_dup_start"):
        if not dup_folder.strip():
            st.error(TD["error_empty_folder"])
        else:
            near_dup_progress_bar = st.progress(0.0)
            near_dup_status_text = st.empty()

            def near_dup_progress_cb(done, total):
                near_dup_progress_bar.progress(done / total if total else 1.0)
                near_dup_status_text.text(TD["near_dup_progress_checking"].format(done=done, total=total))

            try:
                with st.spinner(TD["near_dup_spinner_text"]):
                    near_dup_result = core.find_near_duplicates(
                        dup_folder, similarity_threshold=near_dup_similarity,
                        progress_cb=near_dup_progress_cb,
                    )
            except FileNotFoundError as e:
                st.error(str(e))
            else:
                near_dup_progress_bar.progress(1.0)
                near_dup_status_text.empty()
                st.session_state["_last_near_dup_result"] = near_dup_result

    near_dup_result = st.session_state.get("_last_near_dup_result")
    if near_dup_result is not None:
        m1, m2 = st.columns(2)
        m1.metric(TD["metric_total_checked"], near_dup_result.total_checked)
        m2.metric(TD["near_dup_metric_groups_found"], len(near_dup_result.groups))

        if not near_dup_result.groups:
            st.success(TD["near_dup_no_duplicates"])
        else:
            st.warning(TD["near_dup_warning"])
            near_dup_df = _localize_near_dup_df(near_dup_result)
            st.dataframe(near_dup_df, use_container_width=True, hide_index=True)
            near_dup_fmt = _export_format_picker(key="near_dup_export_format")
            _export_download_button(near_dup_df, near_dup_fmt, "duplikat_mirip_pdf", key="near_dup_download")

        if near_dup_result.errors:
            with st.expander(TD["errors_expander"].format(count=len(near_dup_result.errors))):
                st.dataframe(pd.DataFrame(near_dup_result.errors, columns=["path", "error"]))

# ---------------------------------------------------------------------------
# TAB 4: Saran Rename / Suggest Rename
# ---------------------------------------------------------------------------
with tab_rename:
    TR = T["rename"]
    st.subheader(TR["subheader"])
    st.write(TR["description"])

    col1, col2 = st.columns([3, 1])
    with col1:
        rename_folder = st.text_input(
            TR["folder_label"], key="rename_folder", placeholder=T["build"]["folder_placeholder"],
        )
    with col2:
        rename_email = st.text_input(TR["email_label"], key="rename_email", help=TR["email_help"])

    with st.expander(TR["advanced_expander"]):
        rename_max_pages = st.slider(TR["max_pages_label"], 5, 60, 25, key="rename_max_pages")

    if st.button(TR["button"], type="primary", key="rename_start"):
        if not rename_folder.strip():
            st.error(TR["error_empty_folder"])
        else:
            rename_progress_bar = st.progress(0.0)
            rename_status_text = st.empty()

            def rename_progress_cb(done, total, path):
                rename_progress_bar.progress(done / total if total else 1.0)
                rename_status_text.text(TR["progress_processing"].format(done=done, total=total, name=path.name))

            try:
                with st.spinner(TR["spinner_text"]):
                    rename_result = core.suggest_renames(
                        rename_folder, max_pages=rename_max_pages,
                        contact_email=rename_email.strip() or None,
                        progress_cb=rename_progress_cb,
                    )
            except FileNotFoundError as e:
                st.error(str(e))
            else:
                rename_progress_bar.progress(1.0)
                rename_status_text.empty()
                st.session_state["_last_rename_result"] = rename_result

    rename_result = st.session_state.get("_last_rename_result")
    if rename_result is not None:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(TR["metric_total_found"], rename_result.total_found)
        m2.metric(TR["metric_high"], rename_result.n_high, help=TR["high_help"])
        m3.metric(TR["metric_medium"], rename_result.n_medium)
        m4.metric(TR["metric_low"], rename_result.n_low, help=TR["low_help"])

        rename_df = core.rename_suggestions_to_dataframe(rename_result)
        st.dataframe(rename_df, use_container_width=True, hide_index=True)
        rename_fmt = _export_format_picker(key="rename_export_format")
        _export_download_button(rename_df, rename_fmt, "saran_rename", key="rename_download")

        st.divider()
        st.subheader(TR["ps1_subheader"])
        st.warning(TR["ps1_warning"])
        ps1_min_confidence = st.selectbox(
            TR["ps1_min_confidence_label"], options=["High", "Medium", "Low"], key="rename_ps1_min_confidence",
        )
        with tempfile.NamedTemporaryFile(mode="r", suffix=".ps1", delete=False) as _tmp:
            _tmp_path = _tmp.name
        core.write_rename_powershell_script(rename_result, _tmp_path, min_confidence=ps1_min_confidence)
        ps1_bytes = Path(_tmp_path).read_bytes()
        Path(_tmp_path).unlink(missing_ok=True)
        st.download_button(
            TR["ps1_download_button"], data=ps1_bytes, file_name="rename_pdf.ps1",
            mime="text/plain", key="rename_ps1_download",
        )

        if rename_result.errors:
            with st.expander(TR["errors_expander"].format(count=len(rename_result.errors))):
                st.dataframe(pd.DataFrame(rename_result.errors, columns=["path", "error"]))

# ---------------------------------------------------------------------------
# TAB 5: Panduan / Guide
# ---------------------------------------------------------------------------
with tab_help:
    TH = T["help"]
    st.subheader(TH["subheader"])
    st.markdown(TH["body"])

    st.divider()
    TC = T["credits"]
    st.subheader(TC["title"])
    st.markdown(TC["body"])

# ---------------------------------------------------------------------------
# Footer -- muncul di bawah semua tab, apa pun tab yang lagi aktif
# ---------------------------------------------------------------------------
st.divider()
st.caption(T["credits"]["footer"])
