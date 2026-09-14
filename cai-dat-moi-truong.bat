@echo off
setlocal enabledelayedexpansion
set "TOOLDIR=%~dp0"
if not "%TOOLDIR:~0,2%"=="\\" goto :duong_dan_on

echo.
echo ===============================================
echo   [CANH BAO] Tool dang nam tren O DIA MANG
echo ===============================================
echo.
echo   %TOOLDIR%
echo.
echo   Script nay van cai duoc Python va FFmpeg. Nhung TOOL SE KHONG
echo   CHAY DUOC tu thu muc mang - CMD khong vao duoc thu muc mang, va
echo   database cua tool khong chay an toan tren o mang.
echo.
echo   Cai xong, hay chep ca thu muc tool vao o dia cua Windows:
echo     %USERPROFILE%\MocLan
echo   roi chay start.bat trong do.
echo.
echo   Neu day la may Mac chay Parallels: dung thang ban Mac se nhanh hon
echo   nhieu. Xem file  CAI-DAT-MAC.md
echo.
pause
goto :bo_qua_cd

:duong_dan_on
cd /d "%~dp0"
:bo_qua_cd

title MocLan Viral Hub - Cai dat moi truong

echo ===============================================
echo    MocLan Viral Hub - Cai dat moi truong
echo ===============================================
echo.
echo Script nay se cai giup ban:
echo    1. Python 3.12
echo    2. FFmpeg    (dung de ghep va render video)
echo.
echo Qua trinh mat khoang 5-15 phut tuy toc do mang.
echo Windows co the hien hop thoai xin quyen - bam Yes/Co.
echo.
pause
echo.

REM -- Kiem tra winget -----------------------------------
where winget >nul 2>nul
if %errorlevel% neq 0 goto :no_winget

echo [1/2] Kiem tra Python 3.11 tro len...
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if %errorlevel% equ 0 (
    for /f "delims=" %%v in ('python --version 2^>^&1') do echo       [OK] Da co: %%v
) else (
    echo       Chua co - dang cai Python 3.12...
    winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo       [LOI] Cai Python that bai. Xem huong dan thu cong ben duoi.
        goto :manual_python
    )
    echo       [OK] Da cai Python
    set NEED_RESTART=1
)
echo.

echo [2/2] Kiem tra FFmpeg...
where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    echo       [OK] FFmpeg da co
) else (
    echo       Chua co - dang cai FFmpeg ^(buoc nay lau nhat^)...
    winget install --id Gyan.FFmpeg -e --source winget --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo       [LOI] Cai FFmpeg that bai. Xem huong dan thu cong ben duoi.
        goto :manual_ffmpeg
    )
    echo       [OK] Da cai FFmpeg
    set NEED_RESTART=1
)
echo.

REM Co FFmpeg chua du: ban rut gon thieu `drawtext` (bo loc viet chu len video).
REM Thieu no thi Video Studio bao "Ghep video that bai" ngay khi co chu tren
REM man hinh - ma khong ai doan ra la do FFmpeg.
where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    ffmpeg -hide_banner -filters 2>nul | findstr /r /c:" drawtext " >nul
    if errorlevel 1 (
        echo       [CANH BAO] FFmpeg dang cai THIEU bo loc drawtext.
        echo                  Video Studio se khong viet duoc chu len video.
        echo                  Hay tai ban DAY DU tai:
        echo                    https://www.gyan.dev/ffmpeg/builds/
        echo                  chon file  ffmpeg-release-full.7z  roi thay ban cu.
    ) else (
        echo       [OK] FFmpeg co du bo loc ^(drawtext^)
    )
)

echo ===============================================
echo    Ket qua
echo ===============================================
echo.
if defined NEED_RESTART (
    echo    Da cai xong phan mem can thiet.
    echo.
    echo    QUAN TRONG: phan mem vua cai chua duoc Windows nhan ngay.
    echo    Hay DONG cua so nay lai, roi bam dup vao  start.bat
    echo    de mo tool.
) else (
    echo    Moi truong da day du san.
    echo.
    echo    Buoc tiep theo: bam dup vao file  start.bat
)
echo.
pause
exit /b 0


:no_winget
echo [CANH BAO] May nay khong co winget nen khong cai tu dong duoc.
echo            ^(winget co san tren Windows 11 va Windows 10 ban moi^)
echo.
goto :manual_all


:manual_python
echo.
goto :manual_all


:manual_ffmpeg
echo.
goto :manual_all


:manual_all
echo ===============================================
echo    Cach cai thu cong
echo ===============================================
echo.
echo PYTHON:
echo    1. Vao  https://www.python.org/downloads/
echo    2. Tai va chay file cai dat
echo    3. QUAN TRONG: tich o "Add Python to PATH" o man hinh dau tien
echo.
echo FFMPEG:
echo    1. Vao  https://www.gyan.dev/ffmpeg/builds/
echo    2. Muc "release builds" - tai file  ffmpeg-release-full.7z
echo    3. Giai nen, doi ten thu muc thanh  ffmpeg
echo    4. Copy thu muc  ffmpeg  vao o  C:\
echo       ^(phai co file C:\ffmpeg\bin\ffmpeg.exe^)
echo    5. Bam phim Windows, go "environment variables"
echo       Mo "Edit the system environment variables"
echo    6. Bam "Environment Variables..."
echo    7. Khung duoi ^(System variables^), chon dong "Path", bam "Edit"
echo    8. Bam "New", dan vao:  C:\ffmpeg\bin
echo    9. Bam OK ca 3 cua so
echo.
echo Chi tiet day du xem trong file  CAI-DAT-WINDOWS.md
echo.
pause
exit /b 1
