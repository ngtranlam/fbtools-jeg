#!/bin/bash
# JEG Social Tools — khởi động trên macOS / Linux
# Trên macOS có thể bấm đúp vào file này để chạy.

cd "$(dirname "$0")" || exit 1

echo "======================================="
echo "   JEG Social Tools - Dang khoi dong..."
echo "======================================="
echo
echo "[INFO] Thu muc: $(pwd)"
echo

# ── Kiểm tra Python ───────────────────────────────────────
# Phải thử CHẠY thật, không chỉ kiểm tra file có tồn tại: macOS có sẵn
# /usr/bin/python3 là bản rút gọn của Xcode, tìm thấy nhưng dùng thì lỗi.
PYTHON=""
FOUND_OLD=""
for candidate in python3.13 python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
    if "$candidate" --version >/dev/null 2>&1; then
        FOUND_OLD="$("$candidate" --version 2>&1)"
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[LOI] Khong tim thay Python 3.11 tro len!"
    if [ -n "$FOUND_OLD" ]; then
        echo "      May dang co: $FOUND_OLD  (qua cu, tool can 3.11+)"
    fi
    echo
    echo "      Cach cai:  brew install python@3.12"
    echo "      Chua co brew? Xem huong dan trong file CAI-DAT-MAC.md"
    read -r -p "Nhan Enter de thoat..."
    exit 1
fi
echo "[OK] Python: $($PYTHON --version)"

# ── Kiểm tra FFmpeg ───────────────────────────────────────
if command -v ffmpeg >/dev/null 2>&1; then
    echo "[OK] FFmpeg da co"
else
    echo "[CANH BAO] Khong tim thay FFmpeg."
    echo "           Tinh nang Video Studio va Tao Bien The CAN FFmpeg."
    echo "           macOS: chay lenh  brew install ffmpeg"
    echo
fi

# ── Môi trường ảo ─────────────────────────────────────────
NEED_SETUP=0
if [ ! -d "venv" ]; then
    NEED_SETUP=1
elif ! venv/bin/python -c "import uvicorn" >/dev/null 2>&1; then
    echo "[CANH BAO] Moi truong ao bi loi - tao lai..."
    rm -rf venv
    NEED_SETUP=1
fi

if [ "$NEED_SETUP" = "1" ]; then
    echo
    echo "[CAI DAT] Dang tao moi truong ao..."
    "$PYTHON" -m venv venv || {
        echo "[LOI] Khong tao duoc moi truong ao"
        read -r -p "Nhan Enter de thoat..."
        exit 1
    }
    echo "[CAI DAT] Dang cai thu vien (lan dau co the mat vai phut)..."
    venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1
    venv/bin/python -m pip install -r requirements.txt || {
        echo "[LOI] Cai thu vien that bai"
        read -r -p "Nhan Enter de thoat..."
        exit 1
    }
    echo "[OK] Cai dat xong"
fi

# Xoá cấu hình cũ: file này lưu đường dẫn FFmpeg của máy trước đó
rm -f data/config.json 2>/dev/null

echo
echo "[OK] May chu chay tai http://localhost:8000"
echo "[OK] Nhan Ctrl+C de dung"
echo

# Mở trình duyệt sau khi server kịp khởi động
( sleep 3
  if command -v open >/dev/null 2>&1; then open http://localhost:8000
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8000
  fi ) &

venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

echo
echo "[INFO] May chu da dung."
read -r -p "Nhan Enter de dong cua so..."
