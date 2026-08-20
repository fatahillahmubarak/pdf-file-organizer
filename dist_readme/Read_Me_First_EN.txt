====================================================
 PDF CATALOG -- Read this before you start
====================================================

HOW TO USE
----------
1. Double-click KatalogPDF.exe
2. Wait a moment -- a black window will appear, then your browser will open
   automatically showing the app. DO NOT close the black window while
   you're still using the app.
3. There are 4 tabs: Build Catalog, Search, Find Duplicates, and Guide.
4. Pick your language (Bahasa Indonesia / English) from the dropdown in the
   top-right corner of the app.

FEATURES THAT WORK RIGHT AWAY (no extra installation needed)
----------------------------------------------------------------
- Build Catalog: scan a PDF folder, produce an Excel catalog + search index
- Search: find documents by title/author/keyword/full text content
- Find Duplicates: find PDF files with exactly identical content

A NOTE ABOUT OCR (for scanned PDFs with no copyable text)
------------------------------------------------------------
The OCR feature NEEDS 2 separate extra programs installed outside this
.exe file: Tesseract and Poppler. This is the ONLY thing you'd ever need
to install manually -- if you won't be processing scanned PDFs, just skip
this part entirely. No terminal or commands needed, just download &
install like any ordinary Windows application.

Step 1 -- Install Tesseract:
  1. Go to https://github.com/UB-Mannheim/tesseract/wiki
  2. Download & run the Windows installer (.exe)
  3. Leave the "Add to PATH" option checked
  4. If you need a language other than English (e.g. Bahasa Indonesia),
     also check it under "Additional language data" during installation

Step 2 -- Install Poppler:
  1. Go to https://github.com/oschwartz10612/poppler-windows/releases
  2. Download the .zip file under "Assets" on the latest release
  3. Extract it anywhere, e.g. C:\poppler
  4. Add the Library\bin subfolder inside it to your Windows PATH via
     Start > "environment variables" > "Edit the system environment
     variables" > "Environment Variables..." > User variables > Path >
     Edit > New > paste the full path (e.g. C:\poppler\Library\bin)

Step 3 -- Close and reopen KatalogPDF.exe so the PATH change is picked up.

After that, the "Enable OCR" checkbox in the Build Catalog tab -> Advanced
options will become checkable. To verify it worked, open Command Prompt
and type "tesseract --version" and "pdftoppm -v" -- if both show a
version number, you're all set.

PRIVACY
-------
Everything runs on your own computer. No PDF file or its contents is ever
sent to the internet or to any server.

CONTACT
-------
Built by Muhammad Fatahillah Mubarak, with help from Claude (Anthropic)
Email  : fatahillah.mubarak@gmail.com
GitHub : https://github.com/fatahillahmubarak
