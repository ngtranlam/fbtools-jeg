@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title MocLan Viral Hub - Cap nhat ban moi

echo ===============================================
echo    MocLan Viral Hub - CAP NHAT BAN MOI
echo ===============================================
echo.
echo Script nay se cap nhat tool len ban moi nhat.
echo.
echo   GIU NGUYEN : License, Fanpage, video, du an Studio
echo   THAY MOI   : Ma nguon va tai lieu
echo.

REM -- Hoi thu muc tool dang dung ------------------------
echo Buoc 1: Cho biet thu muc tool DANG DUNG o dau.
echo.
echo   Cach de nhat: mo File Explorer, KEO THA thu muc tool
echo   vao cua so nay roi bam Enter.
echo.
set /p TOOLDIR="Duong dan thu muc tool: "

REM Bo dau ngoac kep neu co (keo tha thuong tu them vao)
set TOOLDIR=%TOOLDIR:"=%

if "%TOOLDIR%"=="" (
    echo.
    echo [LOI] Chua nhap duong dan.
    pause
    exit /b 1
)

REM -- Kiem tra dung thu muc tool khong ------------------
if "%TOOLDIR:~0,2%"=="\\" (
    echo.
    echo [LOI] Duong dan nay nam tren O DIA MANG:
    echo       %TOOLDIR%
    echo.
    echo       Tool khong chay duoc tu thu muc mang ^(thu muc chia se cua
    echo       Parallels, o dia mang...^). Hay chep tool vao o dia cua
    echo       Windows truoc, vi du %USERPROFILE%\MocLan, roi cap nhat lai.
    echo.
    pause
    exit /b 1
)

if not exist "%TOOLDIR%\backend\main.py" (
    echo.
    echo [LOI] Thu muc nay khong phai thu muc tool.
    echo       Khong tim thay file: %TOOLDIR%\backend\main.py
    echo.
    echo       Hay chon dung thu muc co chua cac thu muc
    echo       backend, frontend va file start.bat
    echo.
    pause
    exit /b 1
)

REM Khong cho cap nhat de len chinh no
if /i "%TOOLDIR%"=="%CD%" (
    echo.
    echo [LOI] Ban dang tro vao chinh thu muc goi cap nhat.
    echo       Hay chon thu muc TOOL DANG DUNG.
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Da tim thay tool tai:
echo      %TOOLDIR%
echo.

REM -- Canh bao neu tool dang chay -----------------------
echo Buoc 2: DONG TOOL TRUOC KHI CAP NHAT
echo.
echo   Neu cua so den cua tool dang mo, hay dong lai ngay bay gio.
echo   Cap nhat trong luc tool dang chay se bi loi.
echo.
pause
echo.

REM -- Sao luu du lieu quan trong ------------------------
echo Buoc 3: Sao luu du lieu...
set BACKUP=%TOOLDIR%\data\backup-truoc-khi-cap-nhat
if not exist "%BACKUP%" mkdir "%BACKUP%" >nul 2>nul

if exist "%TOOLDIR%\data\moclan.db" (
    copy /y "%TOOLDIR%\data\moclan.db" "%BACKUP%\moclan.db" >nul
    echo       [OK] Da sao luu database
)
if exist "%TOOLDIR%\data\license.dat" (
    copy /y "%TOOLDIR%\data\license.dat" "%BACKUP%\license.dat" >nul
    echo       [OK] Da sao luu license
)
echo       Ban sao nam o: data\backup-truoc-khi-cap-nhat
echo.

REM -- Chep ma nguon moi ---------------------------------
echo Buoc 4: Dang chep ma nguon moi...

rmdir /s /q "%TOOLDIR%\backend" >nul 2>nul
rmdir /s /q "%TOOLDIR%\frontend" >nul 2>nul

xcopy /e /i /y /q "backend" "%TOOLDIR%\backend" >nul
if %errorlevel% neq 0 goto :copy_failed
xcopy /e /i /y /q "frontend" "%TOOLDIR%\frontend" >nul
if %errorlevel% neq 0 goto :copy_failed

copy /y "requirements.txt" "%TOOLDIR%\requirements.txt" >nul
copy /y "start.bat" "%TOOLDIR%\start.bat" >nul
if exist "cai-dat-moi-truong.bat" copy /y "cai-dat-moi-truong.bat" "%TOOLDIR%\cai-dat-moi-truong.bat" >nul
for %%f in (*.md) do copy /y "%%f" "%TOOLDIR%\%%f" >nul

echo       [OK] Da chep xong
echo.

REM -- Cap nhat thu vien ---------------------------------
echo Buoc 5: Cap nhat thu vien (can thiet cho Spy TikTok)...
echo         Buoc nay can mang, mat khoang 1-3 phut.
echo.

if exist "%TOOLDIR%\venv\Scripts\python.exe" (
    "%TOOLDIR%\venv\Scripts\python.exe" -m pip install -q --upgrade -r "%TOOLDIR%\requirements.txt"
    if !errorlevel! equ 0 (
        echo       [OK] Da cap nhat thu vien
    ) else (
        echo       [CANH BAO] Cap nhat thu vien that bai.
        echo                  Tool van chay duoc, nhung Spy TikTok co the loi.
        echo                  Kiem tra mang roi chay lai script nay.
    )
) else (
    echo       [BO QUA] Chua co moi truong ao - lan dau chay start.bat
    echo                tool se tu cai thu vien moi.
)

echo.
echo ===============================================
echo    CAP NHAT XONG
echo ===============================================
echo.
echo   Du lieu cua ban van con nguyen:
echo   License, Fanpage, video, du an Studio.
echo.
echo   *** BAT BUOC: phai KHOI DONG LAI tool ***
echo   Neu khong, may chu van chay ma nguon cu va cac tinh nang
echo   moi se bao loi "May chu chua co tinh nang nay".
echo.

set /p OPENNOW="Mo tool ngay bay gio? (Enter = mo, go N roi Enter = bo qua): "
if /i "%OPENNOW%"=="N" goto :skip_open

echo.
echo Dang mo tool...
start "" "%TOOLDIR%\start.bat"
echo.
echo   Tool dang khoi dong trong cua so moi.
echo   Nho bam  Ctrl + F5  tren trinh duyet de tai lai giao dien.
echo.
pause
exit /b 0

:skip_open
echo.
echo   Nho tu mo lai:
echo   1. Vao thu muc tool, bam dup  start.bat
echo   2. Tren trinh duyet bam  Ctrl + F5
echo.
pause
exit /b 0


:copy_failed
echo.
echo [LOI] Chep ma nguon that bai!
echo.
echo       Nguyen nhan thuong gap:
echo       - Tool dang chay (dong cua so den roi chay lai script)
echo       - Khong du quyen ghi vao thu muc do
echo.
echo       Du lieu cua ban van an toan trong thu muc data.
echo.
pause
exit /b 1
