# 🚀 MocLan Viral Hub

> **Phiên bản 3.5** — dùng được trên cả **Windows** và **macOS**
> Hệ thống quản lý nội dung video và Fanpage Facebook

---

## 📖 Đọc file nào?

| Bạn cần gì | Mở file này |
|---|---|
| **Cài lần đầu trên Windows** | `CAI-DAT-WINDOWS.md` |
| **Cài lần đầu trên Mac** | `CAI-DAT-MAC.md` |
| **Học cách dùng tool** | `HUONG-DAN-SU-DUNG.md` |
| **Xem có gì mới** | `CHANGELOG.md` |

---

## ⚡ Cài nhanh — 2 bước

### 🪟 Windows
1. Bấm đúp **`cai-dat-moi-truong.bat`** → tự cài Python và FFmpeg *(5–15 phút)*
2. Bấm đúp **`start.bat`** → tool mở tại **http://localhost:8000**

### 🍎 Mac
1. Mở **Terminal**, gõ `bash ` *(có dấu cách)*, **kéo thả `cai-dat-moi-truong.command`** vào → Enter
2. Bấm đúp **`start.command`** → tool mở tại **http://localhost:8000**

> 🍎 **Vì sao Mac phải làm vòng vèo bước 1?** macOS chặn file tải từ mạng.
> Chạy qua Terminal thì không bị chặn. Script này tự mở khoá cho `start.command`,
> nên từ lần sau chỉ cần bấm đúp bình thường.

**Lần đầu chạy sẽ hiện màn hình nhập License Key — liên hệ Admin để lấy.**

---

## 🔄 Đã dùng tool rồi, giờ muốn cập nhật?

**Đừng cài lại từ đầu** — sẽ mất hết dữ liệu. Dùng script cập nhật:

### 🪟 Windows
1. **Đóng tool** (đóng cửa sổ đen)
2. Bấm đúp **`cap-nhat.bat`**
3. **Kéo thả thư mục tool đang dùng** vào cửa sổ đen → Enter

### 🍎 Mac
1. **Đóng tool** (đóng cửa sổ Terminal)
2. Terminal → gõ `bash ` → **kéo thả `cap-nhat.command`** → Enter
3. **Kéo thả thư mục tool đang dùng** vào Terminal → Enter

> ✅ **Dữ liệu không mất.** Script chỉ thay mã nguồn, không đụng vào thư mục `data`
> (license, Fanpage, video, dự án Studio). Nó còn tự sao lưu database và license
> vào `data/backup-truoc-khi-cap-nhat` trước khi làm.

---

## 🧰 Tool làm được gì

| Tính năng | Mô tả |
|---|---|
| **Spy Đối Thủ** | Theo dõi kênh TikTok / YouTube / Facebook, bắt video mới và video đang lên. Tự cập nhật mỗi 3 giờ, báo Telegram khi đối thủ tăng vọt |
| **Tải Video** | Tải từ TikTok, YouTube, Facebook, Instagram. Tải xong tự chuyển sang Video Studio |
| **Video Studio** | Cắt cảnh → ghép clip → chuyển cảnh + chữ + nhạc → nhân ra tới 200 bản khác nhau → đăng nhiều Fanpage |
| **Tạo Biến Thể** | Spoof video chống trùng lặp cho một video đơn lẻ |
| **Content Studio** | Soạn caption, spin nội dung bằng AI, lên lịch đăng Reels |
| **Kiểm Tra Trùng Lặp** | So sánh video bằng perceptual hash |
| **Fanpage & Tài Khoản** | Quản lý nhiều Fanpage, đăng Reels hàng loạt, theo dõi viral |
| **Unified Inbox** | Gom bình luận của mọi Fanpage về một chỗ |

---

## 🔑 Kết nối Facebook

Vào **Tài Khoản** → **"+ Thêm tài khoản Facebook"**, chọn kiểu token:

### ⭐ Token System User — vĩnh viễn (nên dùng)

Có Business Manager thì dùng cách này, token **không bao giờ hết hạn**:

1. **business.facebook.com** → Cài đặt doanh nghiệp → **Người dùng hệ thống**
2. Thêm System User (vai trò Quản trị viên) → **Thêm tài sản** → chọn Trang →
   bật **Toàn quyền**
3. **Tạo mã truy cập mới** → chọn App → **Token Expiration: Never** → tích đủ quyền
4. Copy token (**chỉ hiện một lần**) → dán vào tool → **Xác thực & Quét Fanpage**

App ID / App Secret không bắt buộc với kiểu này, nhập vào chỉ để tool kiểm tra
được hạn và quyền của token.

### Token tài khoản cá nhân — 60 ngày

Không có Business Manager thì dùng cách cũ: nhập **Tên, App ID, App Secret**
(developers.facebook.com → App → Settings → Basic) rồi lấy token ở **Graph API
Explorer** — cửa sổ có nút mở sẵn kèm danh sách quyền cần tích.

> ⚠️ Kiểu này **phải nhập đủ App ID và App Secret**, thiếu là token chỉ sống
> 1–2 tiếng, hôm sau đăng bài là lỗi.

### Sau khi thêm

- **"Kiểm tra token"** — còn bao nhiêu ngày, có những quyền gì
- **"Cập nhật token"** — thay token mới, dữ liệu vẫn nguyên (đổi từ token 60 ngày
  sang token System User cũng làm ở đây)
- Cấp thêm quyền cho Page rồi thì phải **quét lại Fanpage**, vì token Page được
  cấp tại thời điểm quét

---

## 💻 Máy cần gì

| Thành phần | Tối thiểu | Khuyến nghị |
|---|---|---|
| Hệ điều hành | Windows 10 64-bit / macOS 12+ | Windows 11 / macOS 14+ |
| RAM | 8 GB | 16 GB |
| Ổ cứng trống | 20 GB | 50 GB+ |
| CPU | 4 nhân | 8 nhân trở lên |

> Render video rất nặng CPU. Máy 4 nhân render 100 biến thể có thể mất hơn 1 tiếng.

**Cần cài sẵn:** Python 3.11+ và FFmpeg — script `cai-dat-moi-truong` lo giúp.

---

## ⚠️ Ba điều hay quên nhất

**1. Cửa sổ đen / Terminal phải LUÔN MỞ.** Đóng nó là tool tắt ngay, job đang render dừng giữa chừng.

**2. Cập nhật xong phải KHỞI ĐỘNG LẠI tool.** Không thì máy chủ vẫn chạy mã cũ và các nút mới sẽ báo *"Máy chủ chưa có tính năng này"*. Script cập nhật có hỏi *"Mở tool ngay bây giờ?"* — cứ bấm Enter.

**3. Đừng để thư mục tool trong OneDrive / iCloud Drive.** Tool lưu hàng GB video, sẽ làm đầy tài khoản đám mây và máy chạy ì.

---

## 🆘 Gặp lỗi?

Mục **"FAQ & Xử Lý Lỗi"** trong `HUONG-DAN-SU-DUNG.md` có sẵn cách xử lý cho các lỗi hay gặp:

- Python / FFmpeg not found
- Token Facebook hết hạn *(lỗi 190)*
- Ứng dụng Facebook thiếu quyền đăng bài
- Spy TikTok không quét được kênh
- Ghép video thất bại
- macOS chặn không cho chạy file

Tool cũng có sẵn hai nút tự chẩn đoán:
- **Tài Khoản → "Kiểm tra token"** — token còn sống bao lâu, loại gì
- **Fanpage → "Quyền"** — Page có đủ quyền đăng bài chưa, thiếu thì vì sao

---

## 📁 Thư mục `data` chứa gì

Toàn bộ dữ liệu của bạn nằm ở đây — **không xoá, không copy lên mây**:

```
data/
├── moclan.db          Fanpage, bài đăng, kênh spy, dự án Studio
├── license.dat        License đã kích hoạt (gắn với máy này)
├── downloads/         Video đã tải
├── variants/          Biến thể đã spoof
├── studio/            Clip nguồn, nhạc, bản ghép, bản render
└── app.log            Nhật ký để tra lỗi
```

Muốn sao lưu thì copy nguyên thư mục `data`.

---

> 📞 **Cần hỗ trợ:** liên hệ Admin.
