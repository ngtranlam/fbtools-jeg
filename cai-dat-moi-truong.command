#!/bin/bash
# MocLan Viral Hub — tu dong cai moi truong tren macOS
# Bam dup vao file nay. Khong can go lenh, khong can copy dan.

cd "$(dirname "$0")" || exit 1

echo "==============================================="
echo "   MocLan Viral Hub - Cai dat moi truong"
echo "==============================================="
echo
echo "Script nay se cai giup ban:"
echo "   1. Homebrew  (cong cu cai phan mem cho macOS)"
echo "   2. Python 3.12"
echo "   3. FFmpeg    (dung de ghep va render video)"
echo
echo "Qua trinh mat khoang 10-20 phut tuy toc do mang."
echo "May se hoi MAT KHAU dang nhap - go binh thuong,"
echo "man hinh KHONG hien ky tu nao la dung, go xong bam Enter."
echo
read -r -p "Bam Enter de bat dau (hoac dong cua so de huy)..."
echo

# ── Mo khoa Gatekeeper cho ca thu muc ─────────────────────
# File nay da duoc nguoi dung mo khoa thu cong roi moi chay duoc.
# Go luon nhan chan cho cac file con lai (nhat la start.command)
# de ho khong bi hoi lai lan nua.
if xattr -dr com.apple.quarantine . 2>/dev/null; then
    echo "[OK] Da mo khoa cac file trong thu muc (start.command se chay duoc ngay)"
else
    echo "[BO QUA] Khong can mo khoa them"
fi
chmod +x start.command 2>/dev/null
echo

# ── 1. Homebrew ───────────────────────────────────────────
load_brew() {
    # Apple Silicon (M1/M2/M3/M4) va Intel dat brew o hai noi khac nhau
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [ -x "$candidate" ]; then
            eval "$("$candidate" shellenv)"
            return 0
        fi
    done
    command -v brew >/dev/null 2>&1
}

echo "[1/3] Kiem tra Homebrew..."
if load_brew; then
    echo "      [OK] Da co Homebrew: $(brew --version | head -1)"
else
    echo "      Chua co - dang cai (se hoi mat khau may)..."
    echo
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo
    if ! load_brew; then
        echo "      [LOI] Cai Homebrew that bai."
        echo "            Kiem tra ket noi mang roi chay lai file nay."
        read -r -p "Bam Enter de thoat..."
        exit 1
    fi
    echo "      [OK] Da cai Homebrew"

    # Ghi vao ~/.zprofile de lan sau mo Terminal la co san
    BREW_PATH="$(command -v brew)"
    SHELLENV_LINE="eval \"\$($BREW_PATH shellenv)\""
    if ! grep -qF "$SHELLENV_LINE" "$HOME/.zprofile" 2>/dev/null; then
        echo "$SHELLENV_LINE" >> "$HOME/.zprofile"
        echo "      [OK] Da them Homebrew vao duong dan he thong"
    fi
fi
echo

# ── 2. Python ─────────────────────────────────────────────
echo "[2/3] Kiem tra Python 3.11 tro len..."
PYTHON_OK=0
for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && \
       "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
        echo "      [OK] Da co: $("$c" --version)"
        PYTHON_OK=1
        break
    fi
done
if [ "$PYTHON_OK" = "0" ]; then
    echo "      Dang cai Python 3.12..."
    brew install python@3.12 || {
        echo "      [LOI] Cai Python that bai"
        read -r -p "Bam Enter de thoat..."
        exit 1
    }
    echo "      [OK] Da cai Python"
fi
echo

# ── 3. FFmpeg ─────────────────────────────────────────────
echo "[3/3] Kiem tra FFmpeg..."
if command -v ffmpeg >/dev/null 2>&1; then
    echo "      [OK] Da co: $(ffmpeg -version 2>/dev/null | head -1 | cut -c1-40)"
else
    echo "      Dang cai FFmpeg (buoc nay lau nhat, khoang 5-10 phut)..."
    brew install ffmpeg || {
        echo "      [LOI] Cai FFmpeg that bai"
        read -r -p "Bam Enter de thoat..."
        exit 1
    }
    echo "      [OK] Da cai FFmpeg"
fi

# Co FFmpeg chua du: ban rut gon thieu `drawtext` (bo loc viet chu len video).
# Thieu no thi Video Studio bao "Ghep video that bai" ngay khi co chu tren man
# hinh - ma khong ai doan ra la do FFmpeg.
if command -v ffmpeg >/dev/null 2>&1; then
    if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx drawtext; then
        echo "      [OK] FFmpeg co du bo loc (drawtext)"
    else
        echo "      [CANH BAO] FFmpeg dang cai THIEU bo loc drawtext."
        echo "                 Video Studio se khong viet duoc chu len video."
        echo "                 Dang cai lai ban day du..."
        brew reinstall ffmpeg 2>/dev/null || brew install ffmpeg 2>/dev/null
        if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx drawtext; then
            echo "      [OK] Da sua xong, FFmpeg gio co drawtext"
        else
            echo "      [CANH BAO] Van thieu drawtext."
            echo "                 Hay chay tay:  brew reinstall ffmpeg"
            echo "                 Neu may co FFmpeg cai theo cach khac (tai file .zip ve),"
            echo "                 hay xoa ban do di de may dung ban cua Homebrew."
            echo "                 Kiem tra dang dung ban nao:  which ffmpeg"
        fi
    fi
fi
echo

# ── Kiem tra lai lan cuoi ─────────────────────────────────
echo "==============================================="
echo "   Ket qua"
echo "==============================================="

ALL_OK=1

FOUND_PY=""
for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && \
       "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
        FOUND_PY="$c"
        break
    fi
done

if [ -n "$FOUND_PY" ]; then
    echo "   [OK] $("$FOUND_PY" --version)"
else
    echo "   [THIEU] Python 3.11+ - chay lai file nay hoac bao Admin"
    ALL_OK=0
fi

if command -v ffmpeg >/dev/null 2>&1; then
    if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx drawtext; then
        echo "   [OK] FFmpeg da san sang (co du bo loc)"
    else
        echo "   [CANH BAO] FFmpeg thieu drawtext - khong viet duoc chu len video."
        echo "              Chay:  brew reinstall ffmpeg"
    fi
else
    echo "   [THIEU] FFmpeg - chay lai file nay hoac bao Admin"
    ALL_OK=0
fi

echo
if [ "$ALL_OK" = "1" ]; then
    echo "   XONG! Moi truong da san sang."
    echo
    echo "   Buoc tiep theo: bam dup vao file  start.command"
    echo "   de mo tool."
else
    echo "   Con thieu phan mem. Chay lai file nay hoac lien he Admin."
fi
echo
read -r -p "Bam Enter de dong cua so..."
