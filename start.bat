@echo off
REM ---------------------------------------------------------------
REM  Thu muc mang / thu muc chia se cua Parallels khong dung duoc.
REM  Hai ly do, ca hai deu khong vong tranh duoc:
REM    1. CMD khong nhan duong dan mang lam thu muc lam viec. `cd /d`
REM       that bai am tham, cmd nam lai o C:\Windows, roi tool tao moi
REM       truong ao vao C:\Windows\venv va bi tu choi (WinError 5).
REM    2. Database cua tool chay che do WAL. Che do nay CAN bo nho chia
REM       se, thu ma o dia mang khong co - nhe thi bao "database is
REM       locked", nang thi hong ca database.
REM ---------------------------------------------------------------
set "TOOLDIR=%~dp0"
if "%TOOLDIR:~0,2%"=="\\" goto :o_dia_mang

cd /d "%~dp0" 2>nul
if not exist "backend\main.py" goto :sai_thu_muc


title JEG Social Tools
echo =======================================
echo   JEG Social Tools - Dang khoi dong...
echo =======================================
echo.
echo [INFO] Working directory: %cd%
echo.

echo [CHECK] Dang tim Python...
REM Phai thu CHAY that, khong chi kiem tra co file: Windows co san mot
REM "python" gia (App Execution Alias) chi mo Microsoft Store chu khong chay duoc.
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong tim thay Python 3.11 tro len!
    echo.
    echo       1. Tai tai https://www.python.org/downloads/
    echo       2. Khi cai, PHAI tich o "Add Python to PATH"
    echo       3. Cai xong dong cua so nay va chay lai start.bat
    echo.
    echo       Xem huong dan chi tiet trong file CAI-DAT-WINDOWS.md
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do echo [OK] %%v

echo [CHECK] Dang tim FFmpeg...
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo [CANH BAO] Khong tim thay FFmpeg.
    echo            Tinh nang Video Studio va Tao Bien The CAN FFmpeg.
    echo            Xem cach cai trong file CAI-DAT-WINDOWS.md
    echo.
) else (
    echo [OK] FFmpeg da co
)

if not exist "venv" goto :setup_venv

venv\Scripts\python.exe -c "import uvicorn" >nul 2>nul
if %errorlevel% neq 0 goto :fix_venv
goto :run_server

:fix_venv
echo.
echo [CANH BAO] Moi truong ao bi loi - tao lai...
rmdir /s /q venv >nul 2>nul

:setup_venv
echo.
echo [CAI DAT] Dang tao moi truong ao...
python -m venv venv
if %errorlevel% neq 0 (
    echo [LOI] Khong tao duoc moi truong ao
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo [CAI DAT] Dang cai thu vien (lan dau co the mat vai phut)...
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [LOI] Cai thu vien that bai. Kiem tra ket noi mang roi thu lai.
    pause
    exit /b 1
)
echo [OK] Cai dat xong
goto :run_server

:run_server
call venv\Scripts\activate.bat

if exist "data\config.json" del "data\config.json" >nul 2>nul

echo.
echo [OK] May chu chay tai http://localhost:8000
echo [OK] Nhan Ctrl+C de dung
echo.

REM Doi may chu khoi dong xong roi moi mo trinh duyet. Mo ngay lap tuc se
REM hien loi "khong ket noi duoc" va nguoi dung phai tu bam F5.
REM Dung ping de cho thay vi timeout: timeout bao loi khi stdin bi chuyen huong.
start "" /min cmd /c "ping -n 5 127.0.0.1 >nul & start "" http://localhost:8000"

REM Khong dung --reload: che do do chay hai tien trinh (ton gap doi RAM) va se
REM khoi dong lai may chu neu co file .py thay doi, lam gian doan job dang render.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
if %errorlevel% neq 0 (
    echo.
    echo [LOI] May chu da dung do gap loi.
    pause
)

:sai_thu_muc
echo.
echo ===============================================
echo   [LOI] Khong vao duoc thu muc tool
echo ===============================================
echo.
echo   Dang o: %cd%
echo   Can o : %~dp0
echo.
echo   Khong tim thay  backend\main.py
echo.
echo   Hay chac chan start.bat nam CUNG THU MUC voi hai thu muc
echo   backend va frontend.
echo.
pause
exit /b 1

:o_dia_mang
echo.
echo ===============================================
echo   [LOI] Tool dang nam tren O DIA MANG
echo ===============================================
echo.
echo   %TOOLDIR%
echo.
echo   Duong dan bat dau bang  \\  la thu muc mang. Hay gap nhat la thu
echo   muc chia se cua Parallels (\\Mac\Home\...) khi chay Windows tren
echo   may Mac.
echo.
echo   Windows KHONG chay duoc tool tu day:
echo     - CMD khong vao duoc thu muc mang, nen tool tao moi truong ao
echo       nham vao C:\Windows va bi tu choi quyen (WinError 5).
echo     - Database cua tool khong chay an toan tren o mang. Nhe thi bao
echo       loi, nang thi hong het du lieu.
echo.
echo   Neu day la may Mac chay Parallels: dung thang BAN MAC se nhanh hon
echo   nhieu - bam dup  start.command  ben macOS, khoi can Windows.
echo   Xem file  CAI-DAT-MAC.md
echo.
echo -----------------------------------------------
for %%I in ("%TOOLDIR:~0,-1%") do set "DICH=%USERPROFILE%\JEG\%%~nxI"
echo   Muon chay tren Windows thi phai chep tool vao o dia cua Windows:
echo.
echo     %DICH%
echo.
echo   Bam Enter de tool tu chep, hoac go  N  roi Enter de tu chep bang tay.
set /p TUCHEP="   Lua chon: "
if /i "%TUCHEP%"=="N" goto :ket_thuc_mang

if exist "%DICH%\backend\main.py" (
    echo.
    echo   [LOI] Thu muc  %DICH%
    echo         da co san tool roi. Hay chay start.bat trong do.
    goto :ket_thuc_mang
)

echo.
echo   Dang chep... (nhieu video thi buoc nay lau, cu de chay)
robocopy "%TOOLDIR:~0,-1%" "%DICH%" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo.
    echo   [LOI] Chep that bai. Hay tu chep thu muc nay vao
    echo         %USERPROFILE%\JEG  roi chay start.bat trong do.
    goto :ket_thuc_mang
)

echo   [OK] Da chep xong.
echo.
echo   Tu gio hay chay tool tu thu muc moi:
echo     %DICH%
echo.
echo   Dang mo tool...
start "" "%DICH%\start.bat"
exit /b 0

:ket_thuc_mang
echo.
pause
exit /b 1
