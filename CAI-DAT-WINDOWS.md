# 🪟 Hướng Dẫn Cài Đặt — JEG Social Tools (BẢN WINDOWS)

> **Phiên bản:** 3.5 | **Dành cho máy Windows 10 / 11 (64-bit)**
> Bộ cài này dùng chung cho cả Windows và Mac.

---

## ⚡ Cách nhanh nhất — chỉ 2 lần bấm đúp

**Không cần tải gì, không cần chỉnh PATH.**

1. Giải nén gói, mở thư mục vừa giải nén
2. **Bấm đúp `cai-dat-moi-truong.bat`** → tự cài Python và FFmpeg
   - Chờ 5–15 phút. Windows có thể hỏi quyền → bấm **Yes**
   - Cài xong hãy **đóng cửa sổ đó lại** (để Windows nhận phần mềm mới)
3. **Bấm đúp `start.bat`** → tool mở tại http://localhost:8000

> Cách này dùng `winget` có sẵn trên Windows 11 và Windows 10 bản mới.
> Máy nào không có `winget`, script sẽ tự hiện hướng dẫn cài thủ công.

Chỉ khi script báo lỗi thì mới cần làm thủ công theo các bước dưới đây.

---

# 🔧 Cài thủ công (khi script không chạy được)

## 📌 Cần cài 2 phần mềm

| Phần mềm | Dùng để làm gì |
|----------|----------------|
| **Python 3.11+** | Chạy tool |
| **FFmpeg** | Ghép video, tạo biến thể — thiếu là không dùng được Video Studio |

---

## Bước 1 — Cài Python

1. Tải tại **https://www.python.org/downloads/** → bấm nút vàng **Download Python**
2. Chạy file vừa tải
3. ⚠️ **QUAN TRỌNG NHẤT:** ở màn hình đầu tiên, tích vào ô
   **☑ Add Python to PATH** (nằm dưới cùng)
   > Không tích ô này là tool sẽ báo **"Python not found"** và không chạy được.
4. Bấm **Install Now** → chờ xong → bấm **Close**

### Kiểm tra
Bấm phím **Windows**, gõ `cmd`, Enter. Trong cửa sổ đen gõ:

```bash
python --version
```

Hiện ra `Python 3.x.x` là đạt. Nếu báo lỗi → gỡ Python ra cài lại và **nhớ tích ô Add to PATH**.

---

## Bước 2 — Cài FFmpeg

1. Tải tại **https://www.gyan.dev/ffmpeg/builds/**
   → kéo xuống mục **release builds** → tải file **`ffmpeg-release-full.7z`**
2. Giải nén file vừa tải (cần phần mềm **7-Zip** hoặc **WinRAR**)
3. Đổi tên thư mục vừa giải nén thành **`ffmpeg`**
4. Copy thư mục `ffmpeg` vào ổ **C:\**

   → Kiểm tra: phải tồn tại file **`C:\ffmpeg\bin\ffmpeg.exe`**

5. Thêm FFmpeg vào PATH:
   - Bấm phím **Windows** → gõ **environment variables**
   - Mở **"Edit the system environment variables"**
   - Bấm nút **Environment Variables...**
   - Ở khung **dưới** (System variables), chọn dòng **Path** → bấm **Edit**
   - Bấm **New** → dán vào: `C:\ffmpeg\bin`
   - Bấm **OK** ở cả 3 cửa sổ

6. **Đóng hết cửa sổ Command Prompt đang mở**, rồi mở lại cái mới

### Kiểm tra
```bash
ffmpeg -version
```
Hiện ra thông tin phiên bản là đạt.

---

## Bước 3 — Chạy tool

1. Giải nén vào nơi muốn để
   — ví dụ `D:\JEG`

   > ⚠️ **Không** để trong **Desktop**, **Documents** hay **Downloads** nếu máy có
   > **OneDrive**. OneDrive sẽ đồng bộ hàng GB video lên mây, làm đầy tài khoản
   > và máy chạy ì. Hãy để ở ổ **D:\** hoặc thư mục không đồng bộ.

2. Vào thư mục vừa giải nén, **bấm đúp vào file `start.bat`**

3. Lần đầu chờ **3–5 phút** — tool tự tải và cài thư viện.
   Cửa sổ đen sẽ chạy nhiều dòng chữ, đó là bình thường.

4. Trình duyệt tự mở tại **http://localhost:8000**

> 💡 **Những lần sau** cũng chỉ cần bấm đúp `start.bat`, khởi động trong vài giây.

### ⚠️ Lưu ý khi dùng
**Cửa sổ đen phải luôn mở** trong suốt lúc dùng tool. Đóng nó là tool tắt ngay,
job đang render sẽ dừng giữa chừng. Muốn tắt tool thì bấm `Ctrl + C` trong cửa sổ đó.

---

## Bước 4 — Kích hoạt License

1. Tool mở lên sẽ hiện màn hình nhập key
2. **Liên hệ Admin để nhận License Key**
3. Dán key vào ô → bấm **"Kích Hoạt"**

> Key gắn với **một máy duy nhất**, không copy sang máy khác dùng được.
> Key hết hạn thì **dữ liệu vẫn còn nguyên** — xin key mới nhập vào là dùng tiếp bình thường.

---

## ❓ Lỗi thường gặp

### "Python not found"
Chưa tích **Add Python to PATH** lúc cài. Gỡ Python, cài lại và nhớ tích ô đó.

### "FFmpeg not found"
- Kiểm tra file `C:\ffmpeg\bin\ffmpeg.exe` có thật sự tồn tại không
- Kiểm tra đã thêm đúng `C:\ffmpeg\bin` vào PATH chưa (không phải `C:\ffmpeg`)
- Đã đóng và mở lại Command Prompt sau khi thêm PATH chưa

### Cài thư viện thất bại
Kiểm tra mạng. Sau đó **xoá thư mục `venv`** trong thư mục tool rồi bấm lại `start.bat`.

### Lỗi `[WinError 5] Access is denied: 'C:\Windows\venv'`
Tool đang nằm trên **ổ đĩa mạng** — hay gặp nhất là thư mục chia sẻ của Parallels
(`\\Mac\Home\Downloads\...`) khi chạy Windows trên máy Mac.

Windows không chạy được tool từ đó: CMD không vào được thư mục mạng, nên tool tạo
môi trường ảo nhầm vào `C:\Windows` và bị từ chối quyền. Database của tool cũng
không chạy an toàn trên ổ mạng.

**Cách sửa:** chạy `start.bat`, nó sẽ hiện thông báo và **mời tự chép tool sang
`C:\Users\<tên bạn>\JEG`** — bấm Enter là xong.

Hoặc tự làm: chép cả thư mục tool vào ổ `C:` rồi chạy `start.bat` trong đó.

> 💡 Máy Mac chạy Parallels thì **dùng thẳng bản Mac sẽ nhanh hơn nhiều** — bấm đúp
> `start.command` bên macOS, khỏi cần Windows. Xem `CAI-DAT-MAC.md`.

### "Lỗi kết nối server" trên trình duyệt
Cửa sổ đen đã bị đóng. Bấm lại `start.bat`, rồi tải lại trang bằng **Ctrl + F5**.

### Cổng 8000 đã bị chiếm
Có phần mềm khác đang dùng cổng này. Đóng bớt ứng dụng rồi thử lại, hoặc báo Admin.

### Windows Defender / antivirus chặn
Tool chạy máy chủ nội bộ nên có thể bị cảnh báo. Chọn **Allow access** cho Python
khi Windows Firewall hỏi.

---

## 🔄 Cập nhật lên bản mới

Dùng chính bộ cài đặt mới nhất — không cần gói riêng.

1. **Đóng tool lại** — đóng cửa sổ đen nếu đang mở
2. Giải nén gói cập nhật ra đâu cũng được (không cần để cạnh thư mục tool)
3. Bấm đúp **`cap-nhat.bat`**
4. Khi được hỏi đường dẫn: mở File Explorer, **kéo thả thư mục tool đang dùng**
   vào cửa sổ đen → bấm **Enter**
5. Chờ script chạy xong (1–3 phút)
6. Vào thư mục tool, bấm đúp **`start.bat`**
7. Trên trình duyệt bấm **Ctrl + F5** để tải lại giao diện

> ✅ **Dữ liệu không bị mất.** Script chỉ thay mã nguồn, **không đụng vào thư mục `data`**
> (license, Fanpage, video, dự án Studio). Trước khi làm, nó còn tự sao lưu database
> và license vào `dataackup-truoc-khi-cap-nhat`.
>
> Script cũng tự cập nhật thư viện — **cần thiết để Spy TikTok chạy được**.

> ⚠️ Nếu script báo *"Thu muc nay khong phai thu muc tool"* nghĩa là chọn sai chỗ.
> Phải chọn thư mục có chứa `backend`, `frontend` và `start.bat`.

---

> 📞 **Cần hỗ trợ:** liên hệ Admin.
