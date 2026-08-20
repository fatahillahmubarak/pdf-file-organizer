@echo off
setlocal
cd /d "%~dp0"

set PY_EXE=%USERPROFILE%\miniconda3\envs\pdf-katalog\python.exe

if not exist "%PY_EXE%" (
    echo.
    echo Tidak menemukan Python di:
    echo   %PY_EXE%
    echo.
    echo Pastikan environment conda "pdf-katalog" sudah pernah dibuat di komputer ini.
    echo Kalau lokasi Miniconda-mu berbeda, edit file .bat ini dan sesuaikan baris PY_EXE.
    echo.
    pause
    exit /b 1
)

echo Membuka Katalog PDF, tunggu sebentar...
echo (Jendela ini JANGAN ditutup selama aplikasi masih dipakai)
echo.

"%PY_EXE%" -m katalog_pdf.cli ui

pause
