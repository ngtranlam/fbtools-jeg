# 🍎 Hướng Dẫn Cài Đặt — MocLan Viral Hub (BẢN MAC)

> **Phiên bản:** 3.5 | **Dành cho máy Mac (macOS 12 Monterey trở lên)**
> Bộ cài này dùng chung cho cả Windows và Mac.

---

## ⚡ CÁCH CHẠY — làm đúng như sau là được

macOS chặn file tải từ mạng về theo **hai kiểu khác nhau**, nên bấm đúp lần đầu
thường sẽ bị báo lỗi:

| Bảng báo lỗi | Nguyên nhân |
|---|---|
| *"...chưa được mở. Apple không thể xác minh..."* | Gatekeeper chặn file lạ |
| *"...vì bạn không có đặc quyền truy cập thích hợp"* | File mất quyền chạy khi giải nén |

> 🚫 **Nếu thấy nút "Chuyển vào Thùng rác" thì ĐỪNG BẤM** — sẽ xoá mất file.
> Bấm **"Xong"** hoặc **"OK"** rồi làm theo bên dưới.

### ✅ Cách chạy lần đầu — bỏ qua được CẢ HAI lỗi trên

Chạy script qua Terminal thì macOS không chặn, và cũng **không cần** quyền chạy:

1. Mở **Terminal** — bấm `Command ⌘ + dấu cách`, gõ `Terminal`, Enter
2. Gõ chữ **`bash`** rồi **một dấu cách** (chưa bấm Enter):

       bash 

3. Từ Finder, **kéo thả file `cai-dat-moi-truong.command`** vào cửa sổ Terminal
   → đường dẫn tự điền vào, không phải gõ chữ nào
4. Bấm **Enter**

Script sẽ chạy và tự cài Homebrew, Python, FFmpeg.

> 💡 Script này còn **tự mở khoá cho `start.command`** luôn. Nên sau khi nó chạy xong,
> những lần sau chỉ cần **bấm đúp `start.command`** như bình thường, không vướng gì nữa.

### Nếu vẫn muốn bấm đúp ngay từ đầu

Mở Terminal, gõ dòng này (**có dấu cách ở cuối**), rồi **kéo thả thư mục tool** vào
cửa sổ Terminal và bấm Enter:

       chmod +x 

Sau đó vào  **> System Settings > Privacy & Security**, kéo xuống mục **Security**,
bấm **"Open Anyway" / "Vẫn mở"**.

> Nút "Open Anyway" chỉ hiện trong khoảng **1 giờ** sau khi file bị chặn.
> Không thấy thì bấm đúp file lại cho nó hiện ra.

---

## Sau khi cài môi trường xong

**Bấm đúp `start.command`** → tool mở tại http://localhost:8000

Chỉ khi script cài môi trường báo lỗi thì mới cần làm thủ công theo các bước dưới đây.

---

# 🔧 Cài thủ công (khi script không chạy được)

## 📌 Cần cài 2 phần mềm

| Phần mềm | Dùng để làm gì |
|----------|----------------|
| **Python 3.11+** | Chạy tool |
| **FFmpeg** | Ghép video, tạo biến thể — thiếu là không dùng được Video Studio |

Cả hai cài bằng **Homebrew** chỉ trong một lệnh.

> ⚠️ **Khi copy lệnh trong tài liệu này:** chỉ bôi đen và copy **đúng dòng lệnh**.
> **Không copy các dấu ``` ở trên và dưới** — đó là ký hiệu đóng khung của tài liệu,
> không phải một phần của lệnh. Dán nhầm dấu ``` vào Terminal sẽ khiến dấu nhắc
> đổi thành `bash-3.2$` và lệnh cài **không hề chạy**.

---

## Bước 1 — Cài Homebrew

Homebrew là công cụ cài phần mềm cho máy Mac. Nếu máy đã có rồi thì **bỏ qua bước này**.

1. Mở **Terminal**: bấm `Command (⌘) + dấu cách`, gõ `Terminal`, Enter
2. Dán nguyên dòng lệnh sau vào rồi Enter:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

3. Máy hỏi mật khẩu → gõ mật khẩu đăng nhập máy
   > Gõ mật khẩu sẽ **không hiện ký tự nào** trên màn hình — đó là bình thường, cứ gõ rồi Enter.
4. Chờ khoảng 5–10 phút

### Máy Mac chip Apple (M1 / M2 / M3 / M4)
Sau khi cài xong, chạy thêm lệnh này để máy nhận Homebrew:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile && source ~/.zprofile
```

### Kiểm tra
```bash
brew --version
```
Hiện ra số phiên bản là đạt.

---

## Bước 2 — Cài Python và FFmpeg

Trong Terminal, chạy:

```bash
brew install python@3.12 ffmpeg
```

Chờ khoảng 5–10 phút (FFmpeg khá nặng).

### Kiểm tra
```bash
python3 --version
```
```bash
ffmpeg -version
```
Cả hai hiện thông tin phiên bản là đạt.

---

## Bước 3 — Chạy tool

1. Giải nén **`MocLan-Viral-Hub-v3.5.zip`** vào nơi muốn để
   — ví dụ thư mục **Documents**

   > ⚠️ **Không** để trong thư mục đồng bộ **iCloud Drive** (Desktop và Documents
   > thường được iCloud đồng bộ sẵn). Tool lưu rất nhiều video, sẽ làm đầy iCloud
   > và máy chạy ì. Nên tạo thư mục riêng ngoài iCloud, ví dụ:
   > ```bash
   > mkdir -p ~/MocLan
   > ```
   > rồi giải nén vào đó.

2. Mở thư mục vừa giải nén trong **Finder**

3. **Bấm đúp vào file `start.command`**

4. Lần đầu chờ **3–5 phút** — tool tự tải và cài thư viện.
   Cửa sổ Terminal chạy nhiều dòng chữ, đó là bình thường.

5. Trình duyệt tự mở tại **http://localhost:8000**

> 💡 **Những lần sau** cũng chỉ cần bấm đúp `start.command`, khởi động trong vài giây.

### ⚠️ Lưu ý khi dùng
**Cửa sổ Terminal phải luôn mở** trong suốt lúc dùng tool. Đóng nó là tool tắt ngay,
job đang render sẽ dừng giữa chừng. Muốn tắt tool thì bấm `Control + C` trong Terminal.

---

## Bước 4 — Kích hoạt License

1. Tool mở lên sẽ hiện màn hình nhập key
2. **Liên hệ Admin để nhận License Key**
3. Dán key vào ô → bấm **"Kích Hoạt"**

> Key gắn với **một máy duy nhất**, không copy sang máy khác dùng được.
> Key hết hạn thì **dữ liệu vẫn còn nguyên** — xin key mới nhập vào là dùng tiếp bình thường.

---

## ❓ Lỗi thường gặp

### Dấu nhắc đổi thành `bash-3.2$` và Homebrew không được cài
Bạn đã copy nhầm **cả dấu ``` ** của khung code trong tài liệu. Trong Terminal, dấu
backtick có nghĩa là "chạy lệnh bên trong", nên nó chỉ khởi động shell `bash` chứ
không chạy lệnh cài.

Cách sửa:
1. Gõ `exit` rồi Enter để quay về dấu nhắc `%`
2. Copy lại — **chỉ lấy dòng lệnh**, bỏ hết dấu ```
3. Hoặc đơn giản hơn: bấm đúp file **`cai-dat-moi-truong.command`** cho khỏi phải gõ

### macOS chặn: *"không mở được vì đến từ nhà phát triển chưa xác định"*
1. Vào  → **System Settings** → **Privacy & Security**
2. Kéo xuống dưới cùng, thấy dòng nhắc về `start.command`
3. Bấm **Open Anyway** → nhập mật khẩu máy

### "permission denied: ./start.command"
Một số phần mềm giải nén làm mất quyền chạy của file. Sửa bằng cách:
1. Mở **Terminal**
2. Gõ `cd ` (có dấu cách ở cuối), rồi **kéo thả thư mục tool** vào cửa sổ Terminal → Enter
3. Chạy lệnh này **một lần duy nhất**:
```bash
chmod +x start.command
```

### "command not found: brew"
Homebrew chưa cài xong hoặc chưa được nạp. Đóng Terminal, mở lại rồi thử lại.
Máy chip Apple cần chạy thêm lệnh `eval` ở **Bước 1**.

### "command not found: python3"
Chưa cài Python. Chạy lại: `brew install python@3.12`

### Cài thư viện thất bại
Kiểm tra mạng. Sau đó xoá thư mục `venv` trong thư mục tool rồi bấm đúp lại `start.command`:
```bash
rm -rf venv
```

### "Lỗi kết nối server" trên trình duyệt
Cửa sổ Terminal đã bị đóng. Bấm đúp lại `start.command`,
rồi tải lại trang bằng **Command + Shift + R**.

### Cổng 8000 đã bị chiếm
Có phần mềm khác đang dùng cổng này. Xem tiến trình nào đang chiếm:
```bash
lsof -i :8000
```
Đóng phần mềm đó rồi thử lại, hoặc báo Admin.

### Chữ tiếng Việt trong Video Studio bị lỗi font
Tool dùng font Arial có sẵn của macOS. Nếu máy thiếu font, báo Admin.
**Emoji không hiển thị được** trên video là bình thường — hãy dùng chữ thường.

---

## 🔄 Cập nhật lên bản mới

Dùng chính bộ cài đặt mới nhất `MocLan-Viral-Hub-v3.5.zip`
— chính là bộ cài đặt này, không cần gói riêng.

1. **Đóng tool lại** — đóng cửa sổ Terminal nếu đang mở
2. Giải nén gói cập nhật
3. Mở **Terminal**, gõ chữ `bash` rồi **một dấu cách**, sau đó
   **kéo thả file `cap-nhat.command`** vào cửa sổ → bấm **Enter**
4. Khi được hỏi đường dẫn: **kéo thả thư mục tool đang dùng** vào Terminal → **Enter**
5. Chờ script chạy xong (1–3 phút)
6. Vào thư mục tool, bấm đúp **`start.command`**
7. Trên trình duyệt bấm **Command + Shift + R** để tải lại giao diện

> ✅ **Dữ liệu không bị mất.** Script chỉ thay mã nguồn, **không đụng vào thư mục `data`**
> (license, Fanpage, video, dự án Studio). Trước khi làm, nó còn tự sao lưu database
> và license vào `data/backup-truoc-khi-cap-nhat`.
>
> Script cũng tự **gỡ nhãn chặn của macOS** và cấp lại quyền chạy, nên sau khi cập nhật
> bấm đúp `start.command` là chạy được ngay.

> ⚠️ Nếu script báo *"Thu muc nay khong phai thu muc tool"* nghĩa là chọn sai chỗ.
> Phải chọn thư mục có chứa `backend`, `frontend` và `start.command`.

---

> 📞 **Cần hỗ trợ:** liên hệ Admin.
