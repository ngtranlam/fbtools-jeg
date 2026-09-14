# 📋 CHANGELOG — MocLan Viral Hub

> Ghi chú thay đổi để update cho nhân sự.

---

## [2026-09-09] — Hàng đợi đăng bài, quét Page cho System User, và kiểm tra FFmpeg

### ✨ Hàng đợi đăng bài tuần tự — nghỉ 60–120 giây giữa các bài
Trước đây đăng lên nhiều Fanpage là một vòng lặp bắn liên tiếp, bài nọ nối bài kia
không nghỉ giây nào. Hàng chục Page cùng đăng một video trong vài giây là **dấu
hiệu máy chạy tự động rõ nhất** với Facebook.

Nay mọi bài đi qua **một hàng đợi chung**, một luồng duy nhất lấy ra từng bài một,
đăng xong nghỉ **ngẫu nhiên 60–120 giây** rồi mới sang bài kế tiếp.

- Áp cho **cả ba đường**: Content Studio, Video Studio (đăng hàng loạt), và bài
  hẹn giờ. Dù ba chỗ cùng đẩy bài vào, chúng vẫn nối đuôi chứ không bắn song song.
- **Bấm đăng là trả về ngay**, không bắt trình duyệt chờ — đăng 20 Page với khoảng
  nghỉ này mất 20–40 phút, không thể bắt người dùng ngồi đợi trong một lần bấm.
- **Bảng theo dõi ở góc phải** hiện đang đăng Page nào, còn bao nhiêu bài, còn bao
  nhiêu giây tới bài kế, ước tính bao lâu xong, và 5 bài gần nhất.
- Có nút **huỷ các bài còn chờ** nếu đổi ý giữa chừng.
- Khoảng nghỉ chỉnh được trong `data/config.json` (`publish_delay_min` /
  `publish_delay_max`), nhưng **không cho đặt dưới 5 giây**.
- Bài hẹn giờ cũng qua hàng đợi: tool tắt một lúc rồi mở lại, chục bài cùng đến
  hạn sẽ **không bị bắn hết trong vài giây**.

### 🔧 Token System User thêm được mà không thấy Fanpage nào
System User **không "sở hữu" Page** theo kiểu tài khoản cá nhân — Page được **gán**
cho nó trong Business. Vì vậy `/me/accounts`, đường mà tool vẫn dùng, gần như luôn
trả về rỗng. Đó là lý do thêm token System User vào mà quét ra 0 Page.

Nay tool hỏi lần lượt:
1. `/me/accounts` — cách cũ, vẫn dùng cho token cá nhân
2. `assigned_pages` của chính System User
3. Page mà Business sở hữu hoặc được cấp quyền (`owned_pages`, `client_pages`),
   rồi xin token riêng cho từng Page

Quét xong mà vẫn 0 Page thì **hiện bảng hướng dẫn kiểm tra 4 điểm** (gán tài sản,
quyền của token, App trong Business, Page trong Business) kèm đúng những gì
Facebook đã trả lời — thay vì chỉ báo "Tìm thấy 0 Fanpage" rồi thôi.

### 🔧 Bảng thông tin token hết mâu thuẫn
Nút "Kiểm tra token" với tài khoản System User báo *"Chưa nhập App ID / App Secret"*
nhưng ngay dưới lại ghi *"Có App Secret: Có"*. Do bảng đọc nhầm ô. Nay:

- **"Có App Secret"** phản ánh đúng thực tế, và ghi rõ *"không bắt buộc với System User"*
- Thêm dòng **"Kiểu token"**
- Tiêu đề không còn nói *"sắp hết hạn"* khi thực ra chỉ là **chưa kiểm chứng được hạn**
  — hai chuyện khác hẳn nhau, nói nhầm là đi lấy token mới trong khi token cũ chẳng sao

### 🔧 Kiểm tra FFmpeg có đủ bộ lọc khi cài môi trường
Máy Mac cài FFmpeg bản rút gọn thì thiếu `drawtext`, và chỉ lộ ra khi thêm chữ vào
video — báo *"Ghép video thất bại"* mà không ai đoán ra là do FFmpeg.

Nay script cài môi trường **kiểm tra ngay lúc cài**:
- **Mac:** thiếu thì tự chạy `brew reinstall ffmpeg`, vẫn thiếu thì hướng dẫn kiểm
  tra xem máy đang dùng bản FFmpeg nào (`which ffmpeg`)
- **Windows:** báo rõ và chỉ chỗ tải bản đầy đủ

---

## [2026-09-07b] — Chặn lỗi khi tool nằm trên ổ đĩa mạng (Parallels)

### 🔧 Lỗi *"Access is denied: C:\Windows\venv"*
Chạy `start.bat` từ thư mục chia sẻ của Parallels (`\\Mac\Home\Downloads\...`)
báo lỗi khó hiểu: **`[WinError 5] Access is denied: 'C:\Windows\venv'`**.

Nguyên nhân: **CMD của Windows không nhận đường dẫn mạng làm thư mục làm việc.**
Lệnh `cd` vào thư mục tool thất bại, cmd nằm lại ở `C:\Windows`, rồi tool tạo môi
trường ào vào `C:\Windows\venv` — chỗ mà người dùng thường không có quyền ghi.

Ngay cả khi lách được chỗ đó thì vẫn còn vấn đề nặng hơn: **database của tool chạy
chế độ WAL, chế độ này cần bộ nhớ chia sẻ mà ổ đĩa mạng không có.** Nhẹ thì báo
*"database is locked"*, nặng thì hỏng cả database.

Nay cả ba script đều nhận ra và xử lý:

- **`start.bat`** dừng lại với thông báo tiếng Việt giải thích rõ, và **mời tự chép
  tool sang `C:\Users\<tên>\MocLan`** — bấm Enter là xong, chép xong tự mở tool
  ở thư mục mới.
- **`cai-dat-moi-truong.bat`** cảnh báo nhưng vẫn cài Python/FFmpeg bình thường
  (hai thứ này không phụ thuộc chỗ để tool).
- **`cap-nhat.bat`** từ chối nếu trỏ vào thư mục tool nằm trên ổ mạng.

Thêm một lớp chặn nữa: nếu vì lý do gì đó script không vào được đúng thư mục,
nó **dừng ngay với thông báo rõ ràng** thay vì chạy tiếp ở nhầm chỗ.

> 💡 **Máy Mac chạy Parallels thì nên dùng thẳng bản Mac** — nhanh hơn nhiều, không
> qua máy ảo, không vướng thư mục chia sẻ. Bấm đúp `start.command` bên macOS.

---

## [2026-09-07] — Phần thân cắt ngẫu nhiên, xem trước, và đảo ngược cảnh

### ✨ Video B cũng cắt ngẫu nhiên được
Trước đây chỉ cảnh mở đầu là ngẫu nhiên, phần thân giữ nguyên. Nay ở bước 6 có
thêm ô **"Phần thân cũng cắt ngẫu nhiên"**: chọn clip và **tự đặt lấy bao nhiêu
giây** (ví dụ 10–15s), mỗi bản sẽ lấy một đoạn khác nhau.

Hai phần ngẫu nhiên độc lập nhau nên số bản khác biệt nhân lên rất nhiều: cùng
một video A + B, 20 bản là 20 cặp (mở đầu, thân) không trùng nhau.

Không tích thì phần thân giữ nguyên đúng như bước 2 — y như cũ.

### ✨ Xem trước trước khi render
Không phải render cả loạt rồi mới biết ra cái gì:

- Nút **"Xem trước N bản sẽ ghép"** hiện bảng: bản nào lấy đoạn nào, của clip nào,
  từ giây mấy đến giây mấy, thành phẩm dài bao nhiêu — kèm **thanh biểu thị vị
  trí** đoạn đó nằm ở đâu trong clip gốc.
- Nút **"Ghép thử"** trên từng dòng ghép thật **đúng một bản** để xem tận mắt,
  chỉ mất vài giây thay vì chờ cả loạt.
- Nút **🎲 Trộn lại** bốc lại toàn bộ nếu chưa ưng.

> Bảng xem trước **chính là bản sẽ render**, không phải phỏng đoán: cả hai dùng
> chung một mã trộn. Đã đo: bản ghép thử và dự kiến khớp tuyệt đối, bản render
> cuối chỉ lệch dưới 0.15s do bước tạo biến thể lệch tốc độ ±1% cho khác vân tay.

### ✨ Đảo ngược cảnh
Mỗi cảnh ở bước 2 có ô tích **⟲ Đảo ngược** — cảnh phát từ cuối về đầu.
Video B đang phát từ giây 1 đến giây 8, tích vào là phát từ giây 8 ngược về giây 1.

- Đảo cả **hình lẫn tiếng**, không có chuyện hình chạy ngược mà tiếng vẫn xuôi.
- Cảnh thân được cắt ngẫu nhiên vẫn **giữ nguyên thiết lập đảo** đã tích.
- Thêm một cách nữa để các bản khác nhau mà không cần thêm clip mới.

---

## [2026-09-05b] — Sửa lỗi cập nhật xong nhưng giao diện vẫn là bản cũ

### 🔧 Nguyên nhân trang Tài Khoản không hiện đúng sau khi cập nhật
`index.html` gắn số phiên bản cho từng file JS/CSS (`accounts.js?v=301`) để trình
duyệt biết khi nào phải tải lại. Nhưng **số đó gõ tay**, và sửa mã nguồn thì
không ai nhớ tăng — số vẫn là `301` suốt từ tháng 8.

Máy **cài mới** không sao vì chưa có gì trong bộ nhớ đệm. Máy **đã cài từ trước**
thì trình duyệt thấy y hệt đường dẫn cũ nên dùng lại bản cũ trong máy: **máy chủ
chạy mã mới, giao diện vẫn là mã cũ**. Nửa mới nửa cũ, hỏng những chỗ không ai
đoán ra được.

**Nay máy chủ tự đánh số theo vân tay nội dung file** — sửa file nào là số của
file ấy đổi theo, không phụ thuộc việc nhớ hay quên nữa. `index.html` cũng được
đánh dấu không lưu vào bộ nhớ đệm, nên từ nay cập nhật xong chỉ cần tải lại trang
bình thường.

> ⚠️ **Riêng lần cập nhật này** vẫn phải bấm **Ctrl + F5** (Mac: **Command +
> Shift + R**) một lần, vì trình duyệt còn giữ bản `index.html` cũ. Từ lần sau
> thì không cần nữa.

### 🔧 Trang Tài Khoản không còn nói dối
Trước đây gọi máy chủ lỗi thì trang **nuốt lỗi rồi hiện "Chưa có tài khoản
Facebook"** — y hệt màn hình lúc chưa thêm tài khoản nào. Máy chủ hỏng, chưa khởi
động lại, hay lệch phiên bản đều ra cùng một màn hình trống, nên không thể lần ra
nguyên nhân.

Nay hỏng thì hiện **dải cảnh báo đỏ** ghi rõ lỗi gì và cách xử lý, và **không còn
hiện câu "Chưa có tài khoản"** nữa.

---

## [2026-09-05] — Thêm token System User (Business Manager) — token vĩnh viễn

### ✨ Hết cảnh 60 ngày lại đi gia hạn token
Cửa sổ **Thêm tài khoản Facebook** nay cho chọn một trong hai kiểu token:

| Kiểu | Hạn dùng | Lấy ở đâu |
|---|---|---|
| **Người dùng hệ thống (System User)** ⭐ | **Vĩnh viễn** | Business Manager → Cài đặt doanh nghiệp |
| Tài khoản cá nhân | 60 ngày | Graph API Explorer |

Chọn System User thì tool **không đổi token sang bản 60 ngày nữa**. Đây là điểm
quan trọng: token System User vốn đã vĩnh viễn, đem đi đổi chỉ làm nó **ngắn đi**.

- Cửa sổ có **hướng dẫn từng bước** lấy token trong Business Manager, kèm nhắc
  chỗ hay làm sai nhất: **Token Expiration phải chọn Never**.
- **App ID / App Secret không còn bắt buộc** với kiểu System User — nhập vào chỉ
  để tool kiểm tra được hạn và quyền của token.
- Chọn System User mà dán nhầm token thường thì tool **phát hiện và báo ngay**:
  *"Token này CÓ HẠN (… nữa là hết) chứ không phải vĩnh viễn."*
- Thẻ tài khoản hiện nhãn **System User** và ghi **"Vĩnh viễn"** ở ô hạn token,
  thay vì "N/A" như trước.
- Nút **"Cập nhật token"** cũng chọn được kiểu, để chuyển tài khoản đang dùng
  token 60 ngày sang token vĩnh viễn mà không phải xoá đi thêm lại.
- Cảnh báo về token nay hiện trong **hộp thoại phải bấm "Đã hiểu"**, không trôi
  mất sau vài giây như thông báo cũ.

> Page token do tool quét được cũng thừa hưởng: token Page lấy từ một System User
> vĩnh viễn thì cũng không hết hạn.

---

## [2026-09-04] — Hook ngẫu nhiên + sửa lỗi "Filter not found"

### ✨ Hook ngẫu nhiên — một video ra hàng chục mở đầu khác nhau
Có video A dài 1 phút và video B 30 giây muốn giữ nguyên? Bật **Hook ngẫu nhiên**
ở bước 6, mỗi bản render sẽ tự cắt một đoạn khác nhau của video A làm mở đầu,
phần thân giữ y nguyên.

- **Trải đều khắp clip nguồn**, không bốc ngẫu nhiên rồi trùng chỗ nhau: bản 1
  lấy đoạn đầu, bản 2 lấy đoạn sau, cứ thế xoay tua hết clip.
- **Thay 1 hoặc 2 cảnh đầu** (hook và cảnh 2), độ dài mỗi cảnh tự đặt — mặc định
  5–10 giây.
- Chọn 2 cảnh thì hai đoạn **không bao giờ chồng lên nhau** và luôn đúng thứ tự
  thời gian của clip gốc.
- **Luôn chừa lại ít nhất một cảnh thân** — timeline chỉ có mỗi video B thì hook
  được chèn thêm vào đầu chứ không xoá gì.
- Ô cấu hình nói trước sắp render ra cái gì, và cảnh báo ngay khi clip nguồn quá
  ngắn so với độ dài hook đang đặt.

> ⏱ Mỗi bản phải ghép lại từ đầu nên **render lâu hơn** so với khi tắt hook.
> Số lần mã hoá vẫn là hai như trước nên chất lượng không đổi.

### 🔧 Sửa lỗi: *"Ghép video thất bại — Error : Filter not found"*
Câu báo lỗi này của FFmpeg **không nói thiếu cái gì**, nên không ai tự sửa được.
Nguyên nhân là bản FFmpeg trên máy thiếu một bộ lọc mà tool cần — hay gặp nhất là
`drawtext` (dùng để viết chữ lên video, chỉ có ở bản FFmpeg đầy đủ). Bản rút gọn
chạy tốt cho tới lúc dùng đến tính năng đó thì mới lộ ra.

- **Tool hỏi thẳng FFmpeg** xem máy có đủ bộ lọc không **trước khi render**, thay
  vì để chạy rồi hỏng.
- Thông báo nay nói rõ **thiếu bộ lọc nào, dùng cho việc gì, và cách cài lại**.
- Render biến thể lỗi cũng báo đúng nguyên nhân thay vì câu chung chung
  *"Kiểm tra log tại data/app.log"*.

---

## [2026-08-26] — Gộp thành một bộ cài đặt duy nhất

### 📦 Chỉ còn một file gửi cho nhân sự
Trước đây có 4 gói (cài mới / cập nhật × Windows / Mac) — dễ gửi nhầm.
Nay chỉ còn **`MocLan-Viral-Hub-v3.5.zip`** dùng chung cho:

- Cả **Windows và macOS** (mã nguồn vốn giống hệt nhau, chỉ khác script khởi động)
- Cả **cài mới** (`cai-dat-moi-truong` → `start`) lẫn **cập nhật** (`cap-nhat`)

Thêm **`README.md`** làm cửa ngõ: chỉ rõ đọc file nào, cài thế nào, cập nhật ra sao,
tool làm được gì, và ba điều nhân sự hay quên nhất.

Cách **thêm tài khoản Facebook giữ nguyên như cũ** — nhập App ID, App Secret và
token lấy từ Graph API Explorer.

---

## [2026-08-25g] — Sửa lỗi ghép video và chẩn đoán quyền Facebook

### 🔧 Sửa lỗi
- **Ghép video báo `[WinError 32] The process cannot access the file`**: sau khi dựng
  xong, tool xoá bản ghép cũ để đỡ rác ổ đĩa — nhưng file đó đang được trình duyệt
  phát ở bước 5 nên Windows khoá lại. Lỗi này làm **cả bước ghép báo thất bại dù
  video mới đã dựng xong**. Nay xoá không được thì bỏ qua và dọn ở lần sau.

### ✨ Chẩn đoán quyền Facebook
Báo *"thiếu quyền đăng bài"* trong khi đã cấp full quyền là tình huống rất khó hiểu.
Nay tool **hỏi thẳng Facebook xem token của Page thực sự có quyền gì**:

- Trang **Fanpage** có thêm nút **"Quyền"** cho từng Page.
- Khi đăng bài lỗi vì thiếu quyền, thông báo tự kèm phần *"Kiểm tra thực tế"*.
- Phân biệt rõ hai trường hợp:
  - **Thiếu quyền thật** → token Page cấp lúc quét, cấp quyền sau phải **quét lại Fanpage**
  - **Đã đủ quyền** → vấn đề ở App: đang ở chế độ Development, chưa qua App Review,
    hoặc tài khoản không còn là quản trị viên của Page

---

## [2026-08-25f] — Báo ngay khi token chỉ sống được vài tiếng

### 🔧 Sửa lỗi nghiêm trọng
Thêm tài khoản hôm nay, hôm sau đăng bài đã lỗi token. Nguyên nhân: khi việc đổi
sang token 60 ngày **thất bại** (sai App Secret, thiếu App ID, mạng lỗi), tool chỉ
ghi vào log rồi **âm thầm lưu token ngắn hạn**. Người dùng thấy "thêm thành công"
nên tưởng đã có token 60 ngày, trong khi nó chết sau 1–2 tiếng.

- **Tool giờ hỏi thẳng Facebook** (`debug_token`) xem token sống được bao lâu, ngay
  khi thêm hoặc cập nhật tài khoản.
- **Báo to nếu token dưới 24 tiếng**, kèm hướng dẫn lấy App ID / App Secret ở
  `developers.facebook.com → App → Settings → Basic`.
- **Nút "Kiểm tra token" hiện bảng chẩn đoán**: còn lại bao lâu, loại token
  (ngắn hạn / dài hạn), có App Secret chưa, ứng dụng đang có những quyền gì.

---

## [2026-08-25e] — Sửa lỗi bấm chọn bị giật như tải lại trang

### 🔧 Sửa lỗi
- **Chọn biến thể để đăng bị "reload" mỗi lần bấm**: mỗi lần tích, tool vẽ lại
  toàn bộ 7 bước và tải lại clip / dự án / Fanpage từ máy chủ, làm màn hình nhảy
  về đầu trang. Nay chỉ cập nhật đúng ô vừa bấm — **không vẽ lại trang** (đo thực tế:
  từ 1 lần vẽ lại xuống 0), giữ nguyên vị trí đang xem.
- **Tích bộ màu và nhạc ở bước 6 không sáng lên**: giá trị được ghi nhận nhưng viền
  chip không đổi, nên tưởng nút hỏng và tích đi tích lại. Nay sáng ngay khi bấm.
- **Render lượt mới hoặc mở dự án khác** giờ tự chọn lại tất cả biến thể — trước đây
  còn giữ danh sách chọn của lượt cũ nên các bản mới không được tính khi đăng.

---

## [2026-08-25d] — Tải video sang Studio, rõ ràng phần nhạc, chọn biến thể để đăng

### ✨ Tính năng mới
- **Tải video xong tự chuyển sang Video Studio** — có ô bật/tắt ngay trang Tải Video,
  lựa chọn được ghi nhớ cho lần sau. Mỗi video trong thư viện cũng có nút **"→ Studio"**.
- **Chọn biến thể để đăng** ở bước 7: hiện lưới video có ảnh xem trước, tích chọn
  bản nào muốn đăng, có nút *Chọn tất cả* / *Bỏ chọn*. Trước đây luôn dùng hết
  mọi bản đã render, không chọn được.

### 🔧 Sửa lỗi âm thanh
- **Cảnh báo khi bản ghép đã cũ**: đổi nhạc hoặc sửa cảnh ở bước 2–4 mà quên bấm
  *"Ghép & Xem trước"* lại thì các biến thể vẫn mang **tiếng của bản ghép cũ**.
  Nay tool tự phát hiện và hiện cảnh báo, nút cũng đổi thành
  *"Ghép lại (có thay đổi chưa áp dụng)"*.
- **Nhãn nhạc trên thẻ biến thể**: bản không chọn nhạc riêng ở bước 6 vẫn dùng nhạc
  của bản ghép, nhưng trước đây không hiện gì nên tưởng mất nhạc. Nay luôn hiện rõ
  đang dùng nhạc nào, hoặc ghi "tiếng gốc".
- **Bước 6 nói rõ nhạc nào đang áp**: *"Tất cả các bản dùng nhạc X đã chọn ở bước 4.
  Chỉ tick thêm nếu muốn mỗi bản một bài khác nhau."*

### ✅ Đã kiểm chứng
Ghép video A (12s, tiếng 440Hz) + video B (13s, tiếng 660Hz) với nhạc nền 220Hz,
rồi phân tích phổ tần từng đoạn của thành phẩm 25s:
**100% năng lượng ở 220Hz, 0% ở 440Hz và 660Hz** — tiếng gốc của cả hai video đã bị
xoá hoàn toàn, cả ở bản ghép lẫn các biến thể.

---

## [2026-08-25c] — Tự phát hiện khi chưa khởi động lại tool

### 🔧 Sửa vấn đề thực tế
Sau khi cập nhật, nhân sự bấm các nút mới thì báo **"Lỗi: Not Found"** — thông báo
này đến thẳng từ máy chủ và không nói được điều gì hữu ích.

Nguyên nhân: cập nhật xong **chưa khởi động lại tool**. Trình duyệt tải giao diện mới
ngay khi bấm Ctrl+F5, nhưng máy chủ vẫn giữ mã nguồn cũ trong bộ nhớ cho tới khi
tắt và mở lại. Giao diện mới gọi vào đường dẫn máy chủ cũ chưa có → 404 "Not Found".

### ✨ Nay tool tự phát hiện
- **Dải cảnh báo vàng ở đáy màn hình** hiện ngay khi mở tool nếu giao diện và máy chủ
  lệch phiên bản, kèm hướng dẫn đóng/mở lại tool.
- **Thông báo lỗi 404** đổi từ *"Not Found"* thành
  *"Máy chủ chưa có tính năng này. Hãy ĐÓNG hẳn tool rồi mở lại bằng start.bat..."*
- **Script cập nhật giờ hỏi "Mở tool ngay bây giờ?"** và tự chạy `start.bat` /
  `start.command` — bấm Enter là xong, khỏi quên bước khởi động lại.

---

## [2026-08-25b] — Gói cập nhật riêng cho máy đã dùng tool

### ✨ Tính năng mới
- **Thêm 2 gói cập nhật** bên cạnh 2 gói cài mới:
  `...-UPDATE-WINDOWS.zip` và `...-UPDATE-MAC.zip`
- **Script `cap-nhat.bat` / `cap-nhat.command`** — nhân sự chỉ cần kéo thả thư mục
  tool đang dùng vào, script tự lo phần còn lại:
  - Sao lưu database và license vào `data/backup-truoc-khi-cap-nhat`
  - Thay mã nguồn mới, **không đụng vào thư mục `data`**
  - Cập nhật thư viện (cần thiết cho Spy TikTok)
  - Trên Mac còn tự gỡ nhãn chặn của macOS và cấp lại quyền chạy
- Script **từ chối** nếu trỏ nhầm vào thư mục không phải tool, hoặc trỏ vào
  chính thư mục gói cập nhật.

### 🔧 Lý do làm
Cách cũ bắt nhân sự tự copy thư mục `data` từ bản cũ sang bản mới — dễ làm sai
và mất toàn bộ license, Fanpage, video, dự án Studio.

---

## [2026-08-25] — Xử lý token Facebook hết hạn

### 🔧 Sửa vấn đề thực tế
Đăng bài báo lỗi tiếng Anh kỹ thuật *"Facebook API Error (190): Error validating
access token: Session has expired..."* — nhân sự đọc không biết phải làm gì.

- **Thông báo lỗi nay bằng tiếng Việt kèm các bước xử lý cụ thể**, áp cho cả các lỗi
  hay gặp khác: thiếu quyền (200), Page bị khoá đăng (368), gọi quá nhiều (4/17/32),
  Facebook đòi xác minh danh tính.

### ✨ Tính năng mới ở mục Tài Khoản
- **Nút "Cập nhật token"** — thay token mà **không phải xoá tài khoản rồi thêm lại**.
  Tự đổi sang token dài hạn 60 ngày và **tự quét lại toàn bộ Fanpage** để mọi Page
  nhận token mới.
- **Nút "Kiểm tra token"** — hỏi thẳng Facebook xem token còn sống không, còn bao
  nhiêu ngày; cảnh báo khi tài khoản chưa có App Secret.

### ⚠️ Nguyên nhân gốc cần biết
Mỗi Fanpage giữ **token riêng**, cấp dựa trên token tài khoản lúc quét. Chỉ đổi token
tài khoản mà không quét lại Page thì các Page vẫn dùng token cũ đã chết.
Ngoài ra, **thiếu App ID / App Secret** thì Facebook chỉ cấp token sống 1–2 tiếng.

---

## [2026-08-24] — Spy tự động cập nhật chạy nền

### ✨ Tính năng mới
- **Tự động cập nhật kênh đối thủ**: tool chạy nền, mặc định **mỗi 3 giờ** tự cập nhật
  chỉ số toàn bộ kênh đang theo dõi (cả TikTok/YouTube lẫn Facebook) —
  không phải mở trang bấm tay nữa.
- **Cảnh báo Telegram khi đối thủ lên**: video nào tăng vượt ngưỡng (mặc định 5.000 views
  giữa hai lần cập nhật) sẽ được nhắn kèm tên kênh và link.
- **Ô điều khiển ngay trên trang Spy**: bật/tắt, chọn nhịp (1–24 giờ), đặt ngưỡng cảnh báo.
  Đổi xong **áp dụng ngay**, không cần khởi động lại tool.

### ⚙️ Kỹ thuật
- Tác vụ nền đặt `max_instances=1` và `coalesce=True` — quét nhiều kênh có thể mất
  hàng chục phút, không cho hai lượt chạy chồng lên nhau.

### ⚠️ Cần biết
- Nâng yêu cầu **yt-dlp lên bản 2026.8.19 trở lên**. Bản cũ (2026.3.17) đã **không còn
  quét được kênh TikTok** — báo lỗi *"Unable to extract secondary user ID"*.
  Máy đang dùng cần chạy: `pip install -U yt-dlp`
- Hướng dẫn sử dụng có thêm mục xử lý lỗi này.

---

## [2026-08-22e] — Spy Facebook

### ✨ Tính năng mới
- **Thêm được kênh Facebook** vào Spy Đối Thủ — trước đây báo *"URL không hợp lệ"*.
  Nhận cả link trang (`facebook.com/tenpage`) lẫn link trang cá nhân
  (`facebook.com/profile.php?id=...`).
- **Thêm video bằng link**: dán nhiều link reel/video cùng lúc, mỗi dòng một link.
  Tool đọc được views, likes, bình luận, chia sẻ, thời lượng, ngày đăng.
- **Cập nhật chỉ số**: đọc lại các link đã lưu để biết video nào đang tăng views —
  giống hệt cách theo dõi tăng trưởng của TikTok/YouTube.

### ⚠️ Giới hạn cần biết
Facebook **không cho quét danh sách video** của trang người khác, nên kênh Facebook
hoạt động như một **bộ sưu tập link**: người dùng tự dán link video muốn theo dõi,
tool lo phần cập nhật chỉ số. Đây là giới hạn từ phía Facebook
(CrowdTangle cũng đã bị đóng cửa từ 8/2024), không phải lỗi tool.
Giao diện có ghi chú giải thích rõ ngay trong trang.

### 🔧 Sửa lỗi
- Chuẩn hoá URL trước đây **cắt mất tham số `?id=`**, làm hỏng link trang cá nhân Facebook.

---

## [2026-08-22d] — Rõ ràng hơn về thời lượng + sửa nút "Dự án mới"

### 🔧 Sửa lỗi
- **Nút "+ Dự án mới" không dùng được**: bấm xong thì trang tự nạp lại dự án gần nhất
  đè lên timeline trống, nên người dùng vẫn thấy dự án cũ. Nay giữ đúng trạng thái mới.

### 💄 Dễ hiểu hơn
- Rê chuột vào ô **"Thành phẩm: X.Xs"** sẽ hiện phép tính đầy đủ,
  ví dụ *"10.0 + 10.0 − 1.0 (chuyển cảnh chồng hai cảnh lên nhau) = 19.0s"*
- Ngay tại ô chuyển cảnh có nhãn **"video ngắn đi 1.0s"** để thấy trước mức bị trừ
- Hướng dẫn sử dụng có thêm mục giải thích vì sao thời lượng ngắn hơn tổng các cảnh

---

## [2026-08-22c] — Hướng dẫn chạy trên Mac khi bị chặn

### 🔧 Sửa vấn đề thực tế
Nhân sự Mac gặp **hai bảng chặn khác nhau** khi bấm đúp file `.command`:
- *"chưa được mở, Apple không thể xác minh"* — Gatekeeper chặn file tải từ mạng
- *"không có đặc quyền truy cập thích hợp"* — file mất **bit thực thi** khi giải nén
  (hay xảy ra khi gói đi qua Zalo, Google Drive, hoặc giải nén trên Windows rồi copy sang)

Nay tài liệu hướng dẫn chạy lần đầu bằng cách **kéo thả file vào Terminal sau chữ `bash`**
— cách này không cần bit thực thi và cũng không bị Gatekeeper chặn.

### ✨ Cải tiến
- `cai-dat-moi-truong.command` giờ **tự gỡ nhãn chặn và cấp quyền chạy cho `start.command`**,
  nên nhân sự chỉ phải xử lý một lần duy nhất, sau đó bấm đúp bình thường.
- Cảnh báo rõ trong tài liệu: **không bấm "Chuyển vào Thùng rác"** ở bảng chặn của macOS.

---

## [2026-08-22b] — Script tự động cài môi trường

### ✨ Tính năng mới
- **`cai-dat-moi-truong.command` (Mac)** — bấm đúp là tự cài Homebrew, Python 3.12
  và FFmpeg. Tự thêm Homebrew vào đường dẫn hệ thống, có xử lý riêng cho máy chip
  Apple (M1/M2/M3/M4). Nhân sự **không phải gõ lệnh nào vào Terminal**.
- **`cai-dat-moi-truong.bat` (Windows)** — bấm đúp là tự cài Python và FFmpeg qua
  `winget`, khỏi phải tải file và chỉnh PATH thủ công. Máy không có `winget` thì
  script tự hiện hướng dẫn cài thủ công từng bước.

### 🔧 Lý do làm
Nhân sự copy lệnh cài Homebrew từ tài liệu đã dính **cả dấu ``` của khung code**.
Trong Terminal, dấu backtick nghĩa là "chạy lệnh bên trong", nên máy chỉ khởi động
shell `bash` (dấu nhắc đổi thành `bash-3.2$`) còn lệnh cài **không hề chạy**.
Nay tài liệu có cảnh báo rõ về lỗi này, và có script để khỏi phải copy dán.

### 🔧 Sửa lỗi
- File `.bat` chứa ký tự ngoài bảng mã ASCII và dùng kết thúc dòng LF —
  gây ra các dòng lỗi lạ khi chạy. Nay chuyển hết sang ASCII thuần và CRLF chuẩn Windows.

---

## [2026-08-22] — Tinh chỉnh tiếng gốc

### ✨ Tính năng mới
- **Bảng "Tinh chỉnh tiếng gốc"** ở bước 4, hiện khi chọn *Giữ tiếng gốc* hoặc *Trộn*:
  - 4 mức sẵn: **Giữ nguyên / Nhẹ / Vừa / Mạnh** — mặc định là **Vừa**
  - Chế độ **Tuỳ chỉnh**: kéo thanh trượt chỉnh cao độ giọng (±8%),
    âm trầm và âm cao (±8 dB)
  - **Nghe thử ngay**: hai nút *Nghe tiếng gốc* và *Nghe sau khi chỉnh* cắt luôn một
    đoạn của cảnh đầu tiên để so sánh, không phải ghép cả video mới biết nghe thế nào
- **Mỗi biến thể lệch tiếng một chút khác nhau** (cao độ ±1.2%, âm trầm/âm cao ±0.8 dB
  quanh mức đã chọn) — các bản đăng lên nhiều page không còn giống nhau về âm thanh

### ⚙️ Kỹ thuật
- Đổi cao độ bằng `asetrate` rồi bù `atempo` để tiếng **không bị lệch khỏi hình**
  (đo thực tế: lệch 0.034 giây trên video 23 giây)
- Kiểm chứng trên video thật: tiếng bản ghép dịch cao độ +2.65% so với clip gốc,
  tương quan phổ giảm còn 0.980

### 🔧 Sửa lỗi nhỏ
- **Windows: trình duyệt mở quá sớm** — mở ngay khi máy chủ chưa kịp khởi động nên
  hiện lỗi "không kết nối được", người dùng phải tự bấm F5. Nay đợi 4 giây như bản Mac.
- Việt hoá các thông báo còn sót tiếng Anh trong `start.bat` cho khớp với bản Mac.

---

## [2026-08-21c] — Chống nhận diện cho video ghép (QUAN TRỌNG)

### 🔧 Sửa lỗi nghiêm trọng
- **Video ghép ở bước 5 mang theo dấu vết của video gốc**: FFmpeg mặc định chép
  metadata từ clip đầu vào sang video ghép, nên video tải từ TikTok để lại nguyên
  **ID video gốc** (`comment: vid:...`), mã băm nội bộ (`vid_md5`) và nhãn `aigc_info`
  trong file xuất ra. Nền tảng chỉ cần đọc metadata là biết video lấy từ đâu.
  → Nay bản ghép được **xoá sạch metadata** và gắn thông tin giả trông tự nhiên
  (tên file, ngày tạo lùi ngẫu nhiên trong 21 ngày, tên phần mềm dựng).

### ✨ Tăng cường bước nhân bản
Bổ sung các kỹ thuật mà trang Tạo Biến Thể đã có nhưng Video Studio còn thiếu:
- **Lệch tốc độ ±1%** — đổi toàn bộ mốc thời gian khung hình và âm thanh
  (video 20 giây chỉ lệch 0.2 giây, mắt thường không nhận ra)
- **Đổi khung hình/giây** giữa các bản (24 / 25 / 29.97 / 30)
- **Xoay màu nhẹ ±2°**
- **Ngày tạo file giả** cho từng bản (trước đây chỉ có tên file giả)

---

## [2026-08-21b] — Sửa lỗi "Không tìm thấy clip cho cảnh"

### 🔧 Sửa lỗi
- **Video Studio báo "Không tìm thấy clip cho cảnh #N" dù màn hình không có cảnh đó**:
  khi một clip bị xoá khỏi kho, các cảnh đang dùng clip đó bị **ẩn khỏi giao diện**
  nhưng vẫn nằm trong dự án, khiến bước ghép luôn thất bại mà người dùng không biết
  cảnh nào gây lỗi. Nay:
  - Cảnh lỗi **hiện rõ** với viền đỏ và nút xoá riêng
  - Có dải cảnh báo ở đầu bước 2, kèm nút **"Xoá N cảnh lỗi"** xử lý một lần
  - Thông báo lỗi khi ghép nói rõ phải làm gì
- **Nguyên nhân gốc**: xoá clip có gỡ cảnh khỏi dự án nhưng **không lưu vào database**,
  nên mở lại dự án là cảnh lỗi quay về. Nay đã lưu.
- **Thời lượng thành phẩm hiển thị sai**: cộng cả các cảnh lỗi vào tổng
  (ví dụ hiện 24.1s trong khi video thật chỉ 20.0s). Nay chỉ tính cảnh ghép được.

---

## [2026-08-21] — Video Studio + Spy v2 + Giao diện mới (v3.5)

### ✨ Tính năng mới: Video Studio
Module mới trong menu — dùng để **scale 1 nội dung lên nhiều kênh**:
- **Cắt cảnh**: upload video A và video B, kéo thanh trượt 2 đầu để chọn đúng đoạn cần lấy
  (VD: lấy giây 3→6 của video A), hoặc bấm "Lấy toàn bộ clip"
- **Ghép nhiều cảnh** theo thứ tự, đổi vị trí bằng nút ↑ ↓
- **20 hiệu ứng chuyển cảnh**: mờ dần, trượt lên/xuống, gạt ngang, mở vòng tròn, vỡ điểm ảnh...
  chỉnh được độ dài từng hiệu ứng
- **Chữ trên màn hình**: nhiều dòng chữ, chọn vị trí / cỡ / màu / kiểu (đổ bóng, viền, nền khối),
  hẹn giờ hiện–ẩn. Chữ dài **tự xuống dòng** cho vừa khung hình
- **Nhạc nền**: giữ tiếng gốc, thay bằng nhạc, trộn cả hai, hoặc tắt tiếng
- **Nhân bản hàng loạt**: từ bản ghép, render tới **200 biến thể**, mỗi bản một bộ màu
  (12 bộ: Ấm, Lạnh, Rực rỡ, Điện ảnh, Hoài cổ...) và một bài nhạc khác nhau, kèm spoof
  chống trùng lặp (đổi khung, vi chỉnh màu, dịch pixel, xoá metadata)
- **Xuất biến thể ra máy**: chép vào thư mục tự chọn (có bộ duyệt ổ đĩa/thư mục),
  tải gộp một file `.zip`, hoặc tải lẻ từng bản bằng nút ⤓ trên video.
  Thư mục xuất tự đặt theo tên dự án + ngày giờ, và có nút mở thẳng bằng File Explorer.
  Dự án render nhiều lượt sẽ được **đánh số lại liên tục** khi xuất để không bản nào bị ghi đè
- **Đăng thẳng lên Fanpage**: mỗi page nhận một biến thể **khác nhau**, có hẹn giờ và giãn cách
- **Lưu dự án**: đóng tool mở lại vẫn còn timeline và các bản đã render

### 🔧 Sửa lỗi Spy Đối Thủ
- **Bấm Sync hoặc đổi sắp xếp bị mất kênh đang chọn** → đã sửa (lỗi vòng đời trang làm xoá lựa chọn)
- **"Mới nhất" sắp xếp sai**: trước đây dựa vào ngày đăng dạng chữ, video không có ngày bị lẫn lộn.
  Giờ dùng mốc thời gian chính xác tới từng giây
- **Không biết video nào mới, chỉ số tăng bao nhiêu** → giờ có:
  - Nhãn **MỚI** trên video vừa xuất hiện, nhãn **VƯỢT TRỘI** cho video hơn gấp đôi trung bình kênh
  - Mức tăng views so với lần sync trước (VD: ▲ 80)
  - Bảng tổng hợp sau mỗi lần sync: bao nhiêu video mới, video nào tăng mạnh nhất
  - Thanh thống kê kênh: tổng views, views trung bình, cao nhất, tỉ lệ tương tác
- Thêm sắp xếp **Tăng nhanh nhất** và **Tương tác cao nhất**, thêm ô tìm kiếm theo tiêu đề
- Thêm nút **Sync tất cả kênh** một lượt
- Thêm nút **→ Studio**: tải video về và đưa thẳng vào Video Studio để cắt ghép

### 💄 Giao diện
- Làm lại toàn bộ design system: nền phân tầng rõ, bỏ hiệu ứng phát sáng gây rối mắt,
  bóng đổ và khoảng cách nhất quán
- **Sửa lỗi nút không có định kiểu**: `btn-outline` được dùng khắp app nhưng chưa từng có CSS —
  các nút này trước đây hiển thị trần trụi
- Tiêu đề trang có khu vực nút hành động riêng, thẻ video Spy to và rõ chỉ số hơn
- Thêm định kiểu còn thiếu cho bảng, chip, form nhiều cột, trạng thái rỗng
- Bố cục co giãn theo màn hình nhỏ

### ⚙️ Kỹ thuật
- Tách vòng đời trang thành `setup()` / `reset()` / `init()` — sửa luôn lỗi trang Tạo Biến Thể
  đăng ký trùng lặp bộ lắng nghe WebSocket mỗi lần chuyển trang
- Thêm bảng `studio_assets`, `studio_projects`, `studio_renders`
- Thêm cột theo dõi tăng trưởng cho `spy_videos` (tự động migrate, không mất dữ liệu cũ)

---

## [2026-04-17] — Telegram Alert Fix + Dashboard Upgrade

### 🔧 Sửa lỗi
- **Telegram Bot Alert không gửi được**: Token bot bị mask (7 ký tự) → cần nhập lại token đầy đủ (46 ký tự) ở Settings → Telegram
- **Publish Reel bị "Confirm Identity"**: Page "Useful Gadgets" bị Facebook chặn yêu cầu xác minh danh tính → cần vào Facebook app xác minh trên điện thoại
- **Error message trống khi publish thất bại**: Đã fix — giờ ghi log đầy đủ lỗi vào `data/app.log` và database

### ✨ Tính năng mới
- **File logging**: Toàn bộ log server giờ lưu vào `data/app.log` để debug dễ hơn
- **Publish fallback**: Nếu `video_reels` bị chặn → tự động thử `/videos` endpoint
- **Dashboard: Card "Pages chưa đăng hôm nay"**: Hiển thị danh sách page chưa đăng bài trong ngày. Có progress bar, nút "Mở FB" cho từng page, chevron toggle expand/collapse

---

## [2026-04-15] — Image-Enhanced Auto Comments

### ✨ Tính năng mới
- **Comment kèm ảnh sản phẩm**: Khi publish reel, có thể thêm URL ảnh để comment đầu tiên kèm hình ảnh
- **UI Content Studio**: Thêm trường nhập "Link ảnh comment" trong form publish
- **Database**: Thêm cột `comment_image_url` vào bảng `posts`

---

## [2026-04-08] — Multi-Platform Publishing

### ✨ Tính năng mới  
- **Đa nền tảng**: Hỗ trợ publish lên Pinterest và YouTube ngoài Facebook
- **AI Caption**: Tự động tạo caption bằng AI (OpenAI GPT)
- **Content Spinning**: Mỗi page có caption riêng biệt tránh trùng lặp
- **Viral Monitoring**: Tự động theo dõi views, gửi alert Telegram khi video đạt 10K/100K/1M views
- **Daily Report**: Báo cáo tổng hợp hàng ngày qua Telegram lúc 8:00 sáng

---

## [2026-04-01] — Core Platform

### ✨ Tính năng mới
- **Video Downloader**: Tải video từ TikTok, Instagram, Facebook
- **Video Spoofer**: Thay đổi metadata video để tránh bị phát hiện trùng lặp
- **Duplicate Checker**: Kiểm tra video có bị trùng không
- **Account & Page Management**: Quản lý nhiều tài khoản Facebook, page
- **Scheduler**: Lên lịch đăng bài tự động
- **License System**: Hệ thống bản quyền phần mềm
