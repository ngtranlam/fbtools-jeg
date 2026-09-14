#!/bin/bash
# MocLan Viral Hub — cap nhat len ban moi tren macOS
# Giu nguyen toan bo du lieu, chi thay ma nguon.

cd "$(dirname "$0")" || exit 1

echo "==============================================="
echo "   MocLan Viral Hub - CAP NHAT BAN MOI"
echo "==============================================="
echo
echo "Script nay se cap nhat tool len ban moi nhat."
echo
echo "  GIU NGUYEN : License, Fanpage, video, du an Studio"
echo "  THAY MOI   : Ma nguon va tai lieu"
echo

# ── Hoi thu muc tool dang dung ────────────────────────────
echo "Buoc 1: Cho biet thu muc tool DANG DUNG o dau."
echo
echo "  Cach de nhat: mo Finder, KEO THA thu muc tool"
echo "  vao cua so nay roi bam Enter."
echo
read -r -p "Duong dan thu muc tool: " TOOLDIR

# Bo dau nhay neu keo tha them vao, va bo khoang trang thua
TOOLDIR="${TOOLDIR%\"}"; TOOLDIR="${TOOLDIR#\"}"
TOOLDIR="${TOOLDIR%\'}"; TOOLDIR="${TOOLDIR#\'}"
TOOLDIR="$(echo "$TOOLDIR" | sed 's/[[:space:]]*$//')"

if [ -z "$TOOLDIR" ]; then
    echo
    echo "[LOI] Chua nhap duong dan."
    read -r -p "Bam Enter de thoat..."
    exit 1
fi

# ── Kiem tra dung thu muc tool khong ──────────────────────
if [ ! -f "$TOOLDIR/backend/main.py" ]; then
    echo
    echo "[LOI] Thu muc nay khong phai thu muc tool."
    echo "      Khong tim thay: $TOOLDIR/backend/main.py"
    echo
    echo "      Hay chon dung thu muc co chua backend, frontend"
    echo "      va file start.command"
    read -r -p "Bam Enter de thoat..."
    exit 1
fi

if [ "$(cd "$TOOLDIR" && pwd)" = "$(pwd)" ]; then
    echo
    echo "[LOI] Ban dang tro vao chinh thu muc goi cap nhat."
    echo "      Hay chon thu muc TOOL DANG DUNG."
    read -r -p "Bam Enter de thoat..."
    exit 1
fi

echo
echo "[OK] Da tim thay tool tai:"
echo "     $TOOLDIR"
echo

# ── Canh bao neu tool dang chay ───────────────────────────
echo "Buoc 2: DONG TOOL TRUOC KHI CAP NHAT"
echo
echo "  Neu cua so Terminal cua tool dang mo, hay dong lai ngay bay gio."
echo "  Cap nhat trong luc tool dang chay se bi loi."
echo
read -r -p "Bam Enter de tiep tuc..."
echo

# ── Sao luu du lieu quan trong ────────────────────────────
echo "Buoc 3: Sao luu du lieu..."
BACKUP="$TOOLDIR/data/backup-truoc-khi-cap-nhat"
mkdir -p "$BACKUP" 2>/dev/null

if [ -f "$TOOLDIR/data/moclan.db" ]; then
    cp -f "$TOOLDIR/data/moclan.db" "$BACKUP/moclan.db" && echo "      [OK] Da sao luu database"
fi
if [ -f "$TOOLDIR/data/license.dat" ]; then
    cp -f "$TOOLDIR/data/license.dat" "$BACKUP/license.dat" && echo "      [OK] Da sao luu license"
fi
echo "      Ban sao nam o: data/backup-truoc-khi-cap-nhat"
echo

# ── Chep ma nguon moi ─────────────────────────────────────
echo "Buoc 4: Dang chep ma nguon moi..."

rm -rf "$TOOLDIR/backend" "$TOOLDIR/frontend"
if ! cp -R "backend" "$TOOLDIR/backend" || ! cp -R "frontend" "$TOOLDIR/frontend"; then
    echo
    echo "[LOI] Chep ma nguon that bai!"
    echo "      Kiem tra tool da dong chua, va thu muc co cho ghi khong."
    echo "      Du lieu cua ban van an toan trong thu muc data."
    read -r -p "Bam Enter de thoat..."
    exit 1
fi

cp -f "requirements.txt" "$TOOLDIR/requirements.txt"
cp -f "start.command" "$TOOLDIR/start.command"
[ -f "cai-dat-moi-truong.command" ] && cp -f "cai-dat-moi-truong.command" "$TOOLDIR/cai-dat-moi-truong.command"
cp -f *.md "$TOOLDIR/" 2>/dev/null

# Go nhan chan cua macOS va cap lai quyen chay
xattr -dr com.apple.quarantine "$TOOLDIR" 2>/dev/null
chmod +x "$TOOLDIR/start.command" 2>/dev/null
chmod +x "$TOOLDIR/cai-dat-moi-truong.command" 2>/dev/null

echo "      [OK] Da chep xong"
echo

# ── Cap nhat thu vien ─────────────────────────────────────
echo "Buoc 5: Cap nhat thu vien (can thiet cho Spy TikTok)..."
echo "        Buoc nay can mang, mat khoang 1-3 phut."
echo

if [ -x "$TOOLDIR/venv/bin/python" ]; then
    if "$TOOLDIR/venv/bin/python" -m pip install -q --upgrade -r "$TOOLDIR/requirements.txt"; then
        echo "      [OK] Da cap nhat thu vien"
    else
        echo "      [CANH BAO] Cap nhat thu vien that bai."
        echo "                 Tool van chay duoc, nhung Spy TikTok co the loi."
        echo "                 Kiem tra mang roi chay lai script nay."
    fi
else
    echo "      [BO QUA] Chua co moi truong ao - lan dau chay start.command"
    echo "               tool se tu cai thu vien moi."
fi

echo
echo "==============================================="
echo "   CAP NHAT XONG"
echo "==============================================="
echo
echo "  Du lieu cua ban van con nguyen:"
echo "  License, Fanpage, video, du an Studio."
echo
echo "  *** BAT BUOC: phai KHOI DONG LAI tool ***"
echo "  Neu khong, may chu van chay ma nguon cu va cac tinh nang"
echo "  moi se bao loi 'May chu chua co tinh nang nay'."
echo
read -r -p "Mo tool ngay bay gio? (Enter = mo, go N roi Enter = bo qua): " OPENNOW

if [ "$OPENNOW" = "N" ] || [ "$OPENNOW" = "n" ]; then
    echo
    echo "  Nho tu mo lai: bam dup  start.command  trong thu muc tool,"
    echo "  roi bam  Command + Shift + R  tren trinh duyet."
else
    echo
    echo "Dang mo tool..."
    if ! open "$TOOLDIR/start.command" 2>/dev/null; then
        echo "  Khong tu mo duoc. Hay bam dup start.command trong thu muc tool."
    fi
    echo
    echo "  Nho bam  Command + Shift + R  tren trinh duyet de tai lai giao dien."
fi
echo
read -r -p "Bam Enter de dong cua so..."
