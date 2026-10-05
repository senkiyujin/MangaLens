@echo off
title MangaLens
chcp 65001 >nul
cls

echo.
echo  ===========================================
echo    MangaLens Baslatiyor...
echo  ===========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "MAIN=%SCRIPT_DIR%main.py"
set "LOG=%SCRIPT_DIR%manga_translate.log"

:: Python var mi kontrol et
if not exist "%PYTHON%" (
    echo [HATA] .venv bulunamadi!
    echo Lutfen once su komutu calistirin:
    echo.
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo  Python: %PYTHON%
echo  Log:    %LOG%
echo.
echo  Uygulama baslatiliyor... (API anahtari penceresi acilacak)
echo.

:: Uygulamayi calistir, hatayı log dosyasina yaz
"%PYTHON%" "%MAIN%" > "%LOG%" 2>&1

:: Cikis kodu kontrol et
if errorlevel 1 (
    echo.
    echo  [HATA] Uygulama bir hatayla kapandi!
    echo  Asagida hata detaylari goruntuleniyor:
    echo  ----------------------------------------
    type "%LOG%"
    echo  ----------------------------------------
    echo.
    echo  Log dosyasi: %LOG%
) else (
    echo  MangaLens kapatildi.
)

echo.
pause

