# 📖 MocLan Viral Hub — Hướng Dẫn Sử Dụng

> **Phiên bản:** 3.5 | **Cập nhật:** 22/08/2026
> **Hỗ trợ:** Liên hệ Admin để được hướng dẫn

---

## 📋 Mục Lục

1. [Giới Thiệu](#-giới-thiệu)
2. [Yêu Cầu Hệ Thống](#-yêu-cầu-hệ-thống)
3. [Cài Đặt](#-cài-đặt)
4. [Kích Hoạt License](#-kích-hoạt-license)
5. [Dashboard — Tổng Quan](#-dashboard--tổng-quan)
6. [Tài Khoản — Quản Lý Kết Nối](#-tài-khoản--quản-lý-kết-nối)
7. [Fanpage — Quản Lý Page](#-fanpage--quản-lý-page)
8. [Tải Video — Download](#-tải-video--download)
9. [Video Studio — Cắt Ghép & Nhân Bản](#-video-studio--cắt-ghép--nhân-bản)
10. [Tạo Biến Thể — Spoof Video](#-tạo-biến-thể--spoof-video)
11. [Content Studio — Đăng Bài](#-content-studio--đăng-bài)
12. [Kiểm Tra Trùng Lặp](#-kiểm-tra-trùng-lặp)
13. [Spy Đối Thủ](#-spy-đối-thủ)
14. [Unified Inbox](#-unified-inbox)
15. [Phân Tích](#-phân-tích)
16. [Cài Đặt](#-cài-đặt-1)
17. [FAQ & Xử Lý Lỗi](#-faq--xử-lý-lỗi)
18. [Quy Định Sử Dụng](#-quy-định-sử-dụng)

---

## 🚀 Giới Thiệu

**MocLan Viral Hub** là hệ thống quản lý nội dung video và Fanpage Facebook toàn diện, bao gồm:

- 🔍 **Spy đối thủ** — Theo dõi kênh TikTok, YouTube, Douyin; bắt video mới và video đang lên
- ⬇️ **Tải video** — Download từ 5 nền tảng (TikTok, YouTube, Facebook, Instagram, Douyin)
- 🎬 **Video Studio** — Cắt cảnh, ghép clip, chuyển cảnh, chữ, nhạc → nhân ra tới 200 bản khác nhau
- 🎭 **Tạo biến thể** — Spoof video với 16+ biến đổi (crop, brightness, speed, codec...)
- 📤 **Content Studio** — Soạn caption, spin nội dung AI, lên lịch đăng Reels
- ✅ **Kiểm tra trùng lặp** — So sánh perceptual hash giữa các video
- 📊 **Phân tích** — Dashboard engagement, viral tracking
- 💬 **Unified Inbox** — Quản lý comment từ tất cả Page

---

## 💻 Yêu Cầu Hệ Thống

| Thành phần | Tối thiểu | Khuyến nghị |
|------------|-----------|-------------|
| **Hệ điều hành** | Windows 10 64-bit / macOS 12+ | Windows 11 / macOS 14+ |
| **RAM** | 8 GB | 16 GB |
| **Ổ cứng trống** | 20 GB | 50 GB+ (video chiếm nhiều dung lượng) |
| **CPU** | 4 nhân | 8 nhân trở lên |
| **Python** | 3.11+ (phải tự cài) | — |
| **FFmpeg** | Bắt buộc (phải tự cài) | — |
| **Kết nối** | Internet ổn định | — |

> Render video rất nặng CPU. Máy 4 nhân render 100 biến thể có thể mất hơn 1 tiếng.

---

## 📦 Cài Đặt

Xem hướng dẫn cài đặt chi tiết trong file đi kèm gói của bạn:

| Bạn dùng máy gì | Đọc file này |
|-----------------|--------------|
| 🪟 **Windows** | `CAI-DAT-WINDOWS.md` |
| 🍎 **Mac** | `CAI-DAT-MAC.md` |

Tóm tắt: cài **Python 3.11+** và **FFmpeg**, sau đó chạy file khởi động
(`start.bat` trên Windows, `start.command` trên Mac). Lần đầu tool tự cài
thư viện trong 3–5 phút, rồi trình duyệt tự mở tại **http://localhost:8000**.

> ⚠️ Cửa sổ đen (Command Prompt / Terminal) phải **luôn mở** trong lúc dùng tool.
> Đóng cửa sổ đó là tool tắt.

---

## 🔐 Kích Hoạt License

### Lần đầu sử dụng

1. Mở tool → Màn hình kích hoạt sẽ hiện lên
2. **Liên hệ Admin** để nhận License Key
3. Dán key vào ô nhập → Bấm **"Kích Hoạt"**
4. Tool sẽ gắn với máy của bạn (không thể copy sang máy khác)

### Key hết hạn (mỗi 7 ngày)

1. Tool sẽ hiển thị: *"License đã hết hạn"*
2. **Dữ liệu KHÔNG bị mất** — tất cả Page, video, tài khoản vẫn còn nguyên
3. Liên hệ Admin → nhận key mới → nhập lại
4. Tiếp tục sử dụng bình thường

### ⚠️ Lưu ý quan trọng

- **KHÔNG chia sẻ key** cho người khác
- **KHÔNG copy tool** sang máy cá nhân — key chỉ hoạt động trên máy đã kích hoạt
- Nếu đổi máy, phải liên hệ Admin để được cấp key mới

---

## 📊 Dashboard — Tổng Quan

Trang chủ hiển thị:

- **Tổng số Page** đang quản lý
- **Video đã tải** trong thư viện
- **Biến thể đã tạo** (spoof)
- **Viral videos** — video đạt ngưỡng engagement cao
- **Biểu đồ** engagement theo thời gian

### Card "Pages chưa đăng hôm nay" (MỚI)

Card cảnh báo nằm trên Dashboard, hiển thị:
- Số page **chưa đăng bài** trong ngày (VD: "7/23 page chưa đăng")
- **Progress bar** xanh — bao nhiêu page đã đăng rồi
- Bấm **mũi tên ▼** để mở danh sách chi tiết
- Mỗi page có nút **"Mở FB"** → mở Fanpage trên trình duyệt để đăng bài thủ công
- Card tự cập nhật khi refresh trang

> **Mục đích:** Giúp nhân sự dễ dàng theo dõi page nào chưa đăng và can thiệp nhanh.

---

## 👥 Tài Khoản — Quản Lý Kết Nối

### Thêm tài khoản Facebook

Vào **Tài Khoản** → tab "Facebook" → **"+ Thêm tài khoản Facebook"**.
Chọn một trong hai kiểu token:

| Kiểu token | Hạn dùng | Nên dùng khi |
|---|---|---|
| **Người dùng hệ thống (System User)** ⭐ | **Vĩnh viễn** | Có Business Manager — khuyên dùng |
| Tài khoản cá nhân | 60 ngày | Không có Business Manager |

---

#### ⭐ Cách 1 — Token System User (vĩnh viễn, nên dùng)

Token này **không bao giờ hết hạn**, khỏi cảnh cứ 60 ngày lại đi gia hạn cho
từng tài khoản.

1. Vào **business.facebook.com** → **Cài đặt doanh nghiệp**
2. **Người dùng → Người dùng hệ thống** → bấm **Thêm**, đặt tên,
   chọn vai trò **Quản trị viên**
3. Bấm **Thêm tài sản** → chọn **Trang** → tích các Fanpage cần quản lý →
   bật **Toàn quyền**
4. Bấm **Tạo mã truy cập mới**:
   - Chọn **App** của bạn
   - **Token Expiration: Never** ← **chỗ quan trọng nhất**, chọn sai là token
     vẫn hết hạn
   - Tích đủ quyền: `pages_show_list`, `pages_read_engagement`,
     `pages_manage_posts`, `pages_read_user_content`, `pages_manage_engagement`,
     `publish_video`, `read_insights`, `business_management`
5. **Copy token ngay** — token chỉ hiện đúng một lần, đóng cửa sổ đi là mất
6. Về tool, chọn **"Người dùng hệ thống (System User)"**, nhập Tên + dán token
   → **Xác thực & Quét Fanpage**

> App phải nằm trong Business thì bước 4 mới chọn được — thêm ở
> **Cài đặt doanh nghiệp → Tài khoản → Ứng dụng**.
>
> App ID / App Secret **không bắt buộc** với kiểu này. Nhập vào thì tool kiểm tra
> được hạn và quyền của token, nên vẫn khuyến khích nhập.

---

#### Cách 2 — Token tài khoản cá nhân (60 ngày)

1. Chọn **"Tài khoản cá nhân (Graph API Explorer)"**
2. Nhập **Tên**, **App ID**, **App Secret**
   *(developers.facebook.com → App → Settings → Basic)*
3. Bấm **Mở Graph API Explorer**, chọn App, tích đủ quyền,
   bấm **Generate Access Token**
4. Copy token `EAA...` dán vào ô, bấm **Xác thực & Tạo Long-Lived Token**

> ⚠️ **Phải nhập đủ App ID và App Secret.** Thiếu là token chỉ sống 1–2 tiếng,
> hôm sau đăng bài là lỗi ngay.

---

#### Sau khi thêm

- **"Kiểm tra token"** — xem còn bao nhiêu ngày, đang có những quyền gì.
  Token System User sẽ báo *"KHÔNG BAO GIỜ hết hạn"*.
- **"Cập nhật token"** — thay token mới, dữ liệu vẫn nguyên. Chuyển từ token
  60 ngày sang token System User cũng làm ở đây, không cần xoá tài khoản.
- Cấp thêm quyền cho Page rồi thì phải **quét lại Fanpage**, vì token Page được
  cấp tại thời điểm quét.

### Thêm YouTube / Pinterest
Quy trình tương tự, nhập API key tương ứng của từng nền tảng.

---

## 📺 Fanpage — Quản Lý Page

### Xem danh sách Page
- Vào **Fanpage** → xem tất cả Page đã kết nối
- Thông tin: tên, followers, số bài đăng, engagement

### Sync dữ liệu
- Bấm **"Sync"** trên từng Page → cập nhật metrics mới nhất
- Dữ liệu: likes, comments, shares, views

### Xem bài đăng
- Click vào Page → xem danh sách video đã đăng
- Thông tin engagement chi tiết từng video

---

## ⬇️ Tải Video — Download

### Tải từ link
1. Vào **Tải Video**
2. Dán link video vào ô nhập
3. Bấm **"Tải Về"**
4. Chờ tải xong → video xuất hiện trong thư viện

### Nền tảng hỗ trợ
| Nền tảng | Ví dụ URL |
|----------|-----------|
| **TikTok** | `https://www.tiktok.com/@user/video/123456` |
| **YouTube** | `https://www.youtube.com/watch?v=abcdef` |
| **Facebook** | `https://www.facebook.com/watch/?v=123` |
| **Instagram** | `https://www.instagram.com/reel/AbCdEf/` |
| **Douyin** | `https://www.douyin.com/video/123456789` |

### Upload từ máy
- Kéo thả file video vào vùng upload
- Hoặc bấm để chọn file (MP4, MOV, AVI, MKV)

---

## 🎬 Video Studio — Cắt Ghép & Nhân Bản

> **Mục đích:** Lấy vài giây hay của video người khác, ghép với video mình tự quay, thêm chữ và
> nhạc, rồi nhân ra hàng chục/hàng trăm bản khác nhau để đăng lên nhiều Fanpage mà không bị trùng.

### Ví dụ thực tế
> Video A dài 20s → chỉ lấy giây 3 đến 6.
> Video B tự quay dài 15s → lấy toàn bộ.
> Ghép lại thành 17.5s (hiệu ứng chuyển cảnh nuốt 0.5s), thêm chữ và nhạc.
> Render ra 100 bản khác nhau → chỉ định 100 Fanpage để đăng.

### Bước 1 — Nguồn clip
Kéo thả video vào ô upload (hoặc bấm để chọn file). Có thể tải nhiều file cùng lúc.

> **Mẹo:** Ở trang **Spy Đối Thủ**, bấm nút **→ Studio** trên video đối thủ để tải về
> và đưa thẳng vào đây, khỏi phải tải thủ công.

### Bước 2 — Cắt cảnh & ghép
1. Bấm **"+ Thêm cảnh"** dưới clip muốn dùng
2. Kéo **hai đầu thanh trượt** để chọn đoạn cần lấy — video bên trái tự nhảy tới đúng khung hình
3. Hoặc gõ số giây chính xác vào ô **"Từ giây ... đến ..."**
4. Bấm **"▶ Nghe thử đoạn"** để xem lại đúng đoạn vừa cắt
5. Bấm **"Lấy toàn bộ clip"** nếu muốn dùng cả video
6. Thêm cảnh thứ 2 (video B) — giữa hai cảnh sẽ hiện ô chọn **hiệu ứng chuyển cảnh**
7. Đổi thứ tự cảnh bằng nút **↑ ↓**, xoá cảnh bằng **✕**

**Khung hình:** chọn Reels/TikTok (9:16), Vuông (1:1), Feed dọc (4:5) hoặc Ngang (16:9).
**Cách lấp khung:** *Lấp đầy* (cắt viền — thường dùng), *Vừa khung* (viền đen), *Nền mờ phía sau*.

Góc phải hiện **thời lượng thành phẩm** cập nhật theo thời gian thực.
Rê chuột vào đó sẽ thấy phép tính chi tiết.

> ⚠️ **Vì sao thời lượng ngắn hơn tổng các cảnh?**
> Hiệu ứng chuyển cảnh **cho hai cảnh chồng lên nhau**, không phải chèn thêm thời gian.
> Trong 1 giây chuyển cảnh, cảnh trước mờ dần đi *đồng thời* cảnh sau hiện dần lên —
> nên 1 giây đó chỉ tính một lần.
>
> Ví dụ: 2 cảnh mỗi cảnh 10 giây, chuyển cảnh 1 giây → **10 + 10 − 1 = 19 giây**
> (không phải 21 giây).
>
> Mọi phần mềm dựng phim đều hoạt động như vậy. Muốn ra đúng 20 giây mà vẫn có hiệu ứng
> thì kéo một cảnh dài thêm 1 giây. Chọn *"Cắt thẳng"* thì không bị trừ.

### Bước 3 — Chữ trên màn hình
- Bấm **"+ Thêm dòng chữ"**, gõ nội dung (tiếng Việt có dấu bình thường)
- Chọn vị trí (Trên / Giữa / Dưới), cỡ chữ, màu, và kiểu: **Đổ bóng**, **Viền đen**, **Nền khối**
- Đặt **thời gian hiện–ẩn** để chữ chỉ xuất hiện ở đoạn cần thiết
- Chữ dài **tự động xuống dòng** cho vừa khung, không bị tràn ra ngoài

> ⚠️ Emoji có thể không hiển thị do hạn chế font của Windows — nên dùng chữ thường.

### Bước 4 — Âm thanh
| Chế độ | Dùng khi nào |
|--------|--------------|
| **Giữ tiếng gốc** | Video có lời thoại cần giữ |
| **Thay bằng nhạc nền** | Muốn bỏ hẳn tiếng gốc, dùng nhạc trending |
| **Trộn tiếng gốc + nhạc** | Giữ tiếng nhưng thêm nhạc nền phía sau |
| **Tắt tiếng** | Video im lặng, thêm nhạc sau bằng app khác |

Kéo thả file MP3 vào ô nhạc để thêm vào kho. Bấm vòng tròn bên trái bài nhạc để chọn.

### Tinh chỉnh tiếng gốc
Khi chọn **Giữ tiếng gốc** hoặc **Trộn**, sẽ hiện bảng tinh chỉnh. Việc này đổi cao độ và
âm sắc để tiếng không còn khớp với video gốc.

| Mức | Khi nào dùng |
|-----|--------------|
| **Giữ nguyên** | Không đổi gì — dễ bị đối chiếu với bản gốc nhất |
| **Nhẹ** | Gần như không nghe ra khác biệt |
| **Vừa** *(mặc định)* | Khuyên dùng — an toàn cho video có lời thoại |
| **Mạnh** | Giọng hơi khác, chỉ nên dùng cho video không có lời |
| **Tuỳ chỉnh** | Tự kéo cao độ (±8%), âm trầm, âm cao (±8 dB) |

Bấm **"▶ Nghe sau khi chỉnh"** và **"▶ Nghe tiếng gốc"** để so sánh ngay tại chỗ,
không cần ghép cả video.

Khi nhân bản ở bước 6, **mỗi bản còn được lệch thêm một chút khác nhau** — nên các
video đăng lên nhiều page không giống nhau về âm thanh.

> ⚠️ **Đổi nhạc xong phải bấm "Ghép lại"** ở bước 5. Các biến thể được tạo ra từ
> bản ghép, nên nếu không ghép lại thì chúng vẫn mang tiếng của bản ghép cũ.
> Tool sẽ hiện cảnh báo vàng nhắc điều này.
>
> 💡 Cách chắc chắn nhất vẫn là **thay hẳn bằng nhạc nền** và chọn nhiều bài ở bước 6.
> Tinh chỉnh tiếng gốc chỉ nên dùng khi bắt buộc phải giữ lời thoại trong video.

### Bước 5 — Ghép & xem trước
Bấm **"Ghép video & Xem trước"** → chờ xử lý → video thành phẩm hiện ngay bên dưới để xem lại.
**Phải làm bước này trước** thì mới nhân bản được.

### Bước 6 — Nhân bản hàng loạt
1. Nhập **số bản cần tạo** (1–200)
2. Chọn các **bộ màu** muốn dùng — mỗi bản sẽ lần lượt nhận một bộ khác nhau
   (Ấm, Lạnh, Rực rỡ, Điện ảnh, Hoài cổ, Nét căng, Dịu, Hoàng hôn, Bạc hà, Đậm nét, Chất phim)
3. Chọn **nhiều bài nhạc** — mỗi bản sẽ xoay vòng một bài khác nhau
4. Bấm **"Render N biến thể"** → theo dõi thanh tiến trình, video hiện dần bên dưới

Ngoài màu và nhạc, mỗi bản còn được tự động đổi khung hình nhẹ, vi chỉnh màu, dịch pixel và
xoá metadata gốc — để Facebook không nhận ra là cùng một video.

> ⏱️ Render mất khoảng **10–30 giây mỗi bản** tuỳ độ dài và cấu hình máy.
> 100 bản có thể mất 30–50 phút. Cứ để chạy nền, có thể chuyển sang trang khác.

### Xuất biến thể ra máy
Sau khi render xong, khung xuất file hiện ngay dưới nút Render:

| Cách | Dùng khi nào |
|------|--------------|
| **Xuất ra thư mục trên máy** | Lấy toàn bộ file để copy sang máy khác / USB / ổ cứng ngoài |
| **Tải tất cả (.zip)** | Gói một file duy nhất để gửi cho người khác |
| **Nút ⤓ trên từng video** | Chỉ cần vài bản lẻ — rê chuột vào video sẽ hiện nút tải |

**Xuất ra thư mục** là cách nhanh nhất (chép trực tiếp, không phải nén):
1. Bấm **"Xuất ra thư mục trên máy"**
2. Chọn ổ đĩa → bấm vào từng thư mục để đi sâu vào trong, dùng **"↑ Lên thư mục cha"** để lùi lại
3. Bấm **"Lưu vào đây"**

Tool tự tạo thư mục con đặt theo **tên dự án + ngày giờ** (VD: `Áo thun nam_21-08-2026_19h01`)
nên xuất nhiều lần không bị lẫn. Bỏ tích ô "Tạo thư mục con" nếu muốn chép thẳng vào thư mục đã chọn.

Xuất xong, bấm **"Mở thư mục"** để mở luôn bằng File Explorer.

> **Lưu ý:** Nếu một dự án render **nhiều lượt**, tất cả các bản đều được xuất và **đánh số lại
> liên tục** (v001, v002, v003...) — không bản nào bị ghi đè hay mất.

### Bước 7 — Đăng lên Fanpage

**Chọn biến thể muốn đăng:** lưới video hiện tất cả bản đã render, tích chọn bản nào
muốn dùng (mặc định chọn hết). Có nút *Chọn tất cả* / *Bỏ chọn* để thao tác nhanh.
1. Nhập caption, bình luận đầu tiên (tuỳ chọn)
2. Muốn hẹn giờ: chọn thời điểm bài đầu tiên + **giãn cách** giữa các page (phút)
3. Tích chọn các Fanpage → bấm **"Đăng lên các Fanpage đã chọn"**

**Mỗi Fanpage nhận một biến thể khác nhau**, xoay vòng qua danh sách đã render — nên các page
không bao giờ đăng trùng file giống hệt nhau.

Bảng kết quả hiện ngay bên dưới: page nào đã đăng, page nào hẹn giờ, page nào lỗi và lý do.

### Lưu dự án
Bấm **"Lưu"** để giữ lại timeline. Chọn dự án cũ ở ô thả xuống trên cùng để mở lại —
kể cả sau khi tắt tool, các bản đã render vẫn còn để đăng tiếp.

---

### Bước 6b — Ghép ngẫu nhiên (một video ra hàng chục bản)

> **Dùng khi nào:** có một clip dài (phỏng vấn, review, cảnh quay thô) và một
> đoạn thân. Thay vì đăng cùng một video lên nhiều Fanpage, mỗi bản lấy một đoạn
> khác nhau.

**Ví dụ:** video A dài 1 phút, video B dài 30 giây.
Render 20 bản → mỗi bản có 5–10 giây mở đầu lấy ở một chỗ khác trong video A,
và 10–15 giây thân lấy ở một chỗ khác trong video B. 20 bản là 20 cặp không trùng.

**Cách làm:**
1. Ở **bước 2**, xếp timeline: cảnh đầu lấy từ video A, cảnh sau là video B.
2. Xuống **bước 6**, tick **"Ghép ngẫu nhiên"**.
3. Phần **Cảnh mở đầu (hook)**:
   - **Lấy từ clip** — clip dài dùng làm nguồn mở đầu (video A)
   - **Thay mấy cảnh đầu** — 1 cảnh (chỉ hook) hoặc 2 cảnh (hook + cảnh 2)
   - **Độ dài mỗi cảnh** — mặc định 5 đến 10 giây
4. Muốn phần thân cũng đổi thì tick **"Phần thân cũng cắt ngẫu nhiên"**:
   - **Lấy từ clip** — để trống là dùng chính clip của cảnh thân (video B)
   - **Lấy bao nhiêu giây** — ví dụ 10 đến 15 giây
   *(không tick thì phần thân giữ nguyên đúng như bước 2)*
5. Bấm **"Xem trước N bản sẽ ghép"** để kiểm tra trước khi render.
6. Ưng rồi thì bấm **Render** như bình thường.

#### Xem trước — không phải render xong mới biết

- **Bảng xem trước** liệt kê từng bản: lấy đoạn nào, của clip nào, từ giây mấy
  đến giây mấy, thành phẩm dài bao nhiêu. Thanh màu cho thấy đoạn đó nằm ở đâu
  trong clip gốc.
- **"Ghép thử"** trên mỗi dòng ghép thật đúng một bản để xem tận mắt — vài giây
  là xong, khỏi chờ cả loạt.
- **🎲 Trộn lại** bốc lại toàn bộ nếu chưa ưng.

> Bảng xem trước **chính là bản sẽ render**, không phải phỏng đoán.

**Cần biết:**
- Các bản **không lấy trùng chỗ nhau**: tool chia clip thành từng vùng và xoay
  tua theo số thứ tự bản.
- Chọn 2 cảnh mở đầu thì hai đoạn **không chồng lên nhau**, vẫn đúng thứ tự thời gian.
- **Phần thân không bao giờ bị mất.** Timeline chỉ có mỗi video B thì hook được
  chèn thêm vào đầu chứ không xoá cảnh nào.
- ⏱ **Render lâu hơn** khi tắt, vì mỗi bản phải ghép lại từ đầu. Chất lượng không đổi.
- Clip nguồn quá ngắn so với độ dài đang đặt thì ô cấu hình báo ngay, chưa cần render.

---

### ⟲ Đảo ngược cảnh

Ở **bước 2**, mỗi cảnh có ô tích **⟲ Đảo ngược** — cảnh sẽ phát từ cuối về đầu.

**Ví dụ:** video B đang lấy từ giây 1 đến giây 8. Tích vào là phát từ giây 8
ngược về giây 1.

- Đảo **cả hình lẫn tiếng**, không có chuyện hình chạy ngược mà tiếng vẫn xuôi.
- Cảnh thân được cắt ngẫu nhiên ở bước 6 vẫn **giữ nguyên thiết lập đảo** đã tích.
- Là thêm một cách để các bản khác nhau mà không cần thêm clip mới.

> Đảo ngược phải nạp cả đoạn vào bộ nhớ nên **đoạn càng dài càng tốn RAM**.
> Đoạn 10–15 giây thì bình thường; đoạn vài phút trên máy 8GB có thể chậm.


## 🎭 Tạo Biến Thể — Spoof Video

### Mục đích
Tạo video "unique" từ video gốc để tránh phát hiện nội dung trùng lặp khi đăng lên Facebook.

### Cách sử dụng
1. Vào **Tạo Biến Thể**
2. Chọn video từ thư viện
3. Chọn **profile**:
   - **Light**: Ít biến đổi, giữ nguyên chất lượng
   - **Medium**: Cân bằng (khuyến nghị)
   - **Heavy**: Biến đổi nhiều, khác biệt cao
4. Chọn số biến thể (1-10)
5. Bấm **"Tạo Biến Thể"**
6. Chờ xử lý → xem kết quả

### Các biến đổi có sẵn
Crop, Brightness, Contrast, Saturation, Hue Shift, Speed, Scale, Bitrate, Framerate, Codec, Mirror, Rotation, Noise, Audio Pitch, Trim, Metadata Strip, Pixel Shift

---

## 📤 Content Studio — Đăng Bài

### Quy trình đăng Reels
1. Vào **Content Studio**
2. **Chọn Page** đích từ danh sách
3. **Chọn video** biến thể
4. **Soạn caption**:
   - Viết thủ công hoặc
   - Bấm **"✨ AI Tạo Caption"** để tạo tự động
5. **Spin nội dung** (tùy chọn): Tạo nhiều phiên bản caption
6. **Lên lịch** hoặc **đăng ngay**
7. Theo dõi trong hàng đợi (Queue)

### Tính năng AI
- Tạo caption tự động từ mô tả video
- Spin nội dung: sinh nhiều phiên bản khác nhau
- Gợi ý hashtag phổ biến

---

### ⏱ Hàng đợi đăng bài — vì sao bấm đăng mà bài chưa lên ngay

Từ bản này, **"Đăng ngay" không có nghĩa là tất cả bài lên cùng lúc.**

Đăng một video lên 20 Fanpage trong vài giây là dấu hiệu máy chạy tự động rõ nhất
với Facebook. Nên tool xếp các bài vào **hàng đợi**, đăng từng bài một, mỗi bài
cách nhau **ngẫu nhiên 60–120 giây**.

- Bấm đăng xong màn hình **trả về ngay**, không phải ngồi chờ.
- **Bảng nhỏ góc dưới bên phải** cho biết: đang đăng Page nào, còn bao nhiêu bài
  chờ, còn bao nhiêu giây tới bài kế, và ước tính bao lâu thì xong.
- Muốn dừng thì bấm **"Huỷ các bài còn chờ"** — bài đang đăng dở vẫn chạy nốt.
- **Không tắt tool** khi hàng đợi chưa xong, tắt là các bài còn lại không đăng nữa.

> Đăng 20 Page mất khoảng **20–40 phút**. Đây là chủ ý, không phải tool chậm.

Muốn đổi khoảng nghỉ thì sửa `data/config.json`:
`publish_delay_min` và `publish_delay_max` (đơn vị giây, tối thiểu 5).
**Không khuyến khích giảm** — nghỉ càng ngắn càng dễ bị Facebook để ý.

## ✅ Kiểm Tra Trùng Lặp

### Cách sử dụng
1. Vào **Kiểm Tra Trùng Lặp**
2. Chọn các video cần so sánh
3. Bấm **"Kiểm Tra"**
4. Xem kết quả:
   - ✅ **Unique** — video không trùng
   - ⚠️ **Cảnh báo** — có khả năng trùng (xem % tương đồng)
   - ❌ **Trùng lặp** — video giống nhau

### Export kết quả
- Bấm **"Xuất CSV"** để tải báo cáo

---

## 🔍 Spy Đối Thủ

### Thêm kênh theo dõi
1. Vào **Spy Đối Thủ**
2. Bấm **"+ Thêm Kênh"**
3. Dán URL kênh:
   - TikTok: `https://www.tiktok.com/@username`
   - YouTube: `https://www.youtube.com/@channel`
   - Facebook: `https://www.facebook.com/tenpage` hoặc `https://www.facebook.com/profile.php?id=...`
4. Đặt tên hiển thị (tùy chọn)
5. Bấm **"Thêm & Sync"**

### ⚠️ Facebook hoạt động khác TikTok / YouTube

| | TikTok / YouTube | Facebook |
|---|---|---|
| Lấy danh sách video | Tool **tự quét** kênh | **Phải tự dán link** từng video |
| Nút bấm | "Sync Data" | "+ Thêm video" và "Cập nhật chỉ số" |
| Chỉ số lấy được | views, likes, bình luận, chia sẻ | **giống hệt** |
| Theo dõi tăng views | Có | Có |

**Lý do:** Facebook không cho phép đọc danh sách bài đăng của trang người khác —
đây là giới hạn từ phía Facebook, không phải lỗi tool. Công cụ CrowdTangle mà giới
nghiên cứu hay dùng cũng đã bị Facebook đóng cửa từ tháng 8/2024.

### Cách theo dõi video Facebook
1. Thêm kênh Facebook như trên → tool tự mở ô dán link
2. Trên Facebook, mở video/reel của đối thủ → copy link
3. Dán vào ô, **mỗi dòng một link** (dán được nhiều link cùng lúc)
4. Bấm **"Thêm & Lấy chỉ số"**
5. Về sau bấm **"Cập nhật chỉ số"** để xem video nào đang tăng views

> Video phải ở chế độ **công khai** thì mới đọc được chỉ số.
> Link đã có sẵn sẽ tự động bỏ qua, không bị trùng.

### Tự động cập nhật (không cần bấm tay)
Góc trên phải có ô **"Tự cập nhật mỗi 3 giờ"** — bấm vào để chỉnh:

| Tuỳ chọn | Ý nghĩa |
|---|---|
| **Bật/tắt** | Cho tool chạy nền tự cập nhật hay không |
| **Cập nhật mỗi** | 1 / 2 / **3 (khuyên dùng)** / 6 / 12 / 24 giờ |
| **Báo Telegram khi tăng hơn** | Số views tăng thêm giữa 2 lần cập nhật. Để 0 nếu không muốn nhận báo |

Tool chạy nền, tự cập nhật chỉ số **tất cả kênh** đang theo dõi — kể cả kênh Facebook.
Video nào tăng vọt sẽ được **nhắn qua Telegram** kèm link, khỏi phải mở tool ngồi canh.

> ⚠️ Đừng đặt nhịp quá dày. Mỗi lượt phải gọi ra ngoài cho từng video, gọi liên tục
> dễ bị nền tảng chặn. **3 giờ** là mức an toàn.
> Muốn nhận báo Telegram thì phải cài Bot ở mục **Cài Đặt** trước.

### Sync thủ công khi cần gấp
- Bấm **"Sync Data"** → quét video mới nhất của kênh đó
- Bấm **"Sync tất cả kênh"** ở góc trên phải → quét toàn bộ kênh trong một lượt

Sau mỗi lần sync, hệ thống báo rõ:
- **Bao nhiêu video mới** — được gắn nhãn **MỚI** trên thẻ video
- **Video nào đang tăng mạnh nhất** — kèm số views tăng thêm so với lần sync trước (VD: ▲ 80)
- Danh sách tự nhảy về sắp xếp **"Mới đăng nhất"** khi phát hiện video mới

### Đọc thẻ video
| Thông tin | Ý nghĩa |
|-----------|---------|
| Nhãn **MỚI** | Video vừa xuất hiện ở lần sync này |
| Nhãn **VƯỢT TRỘI** | Views cao hơn gấp đôi mức trung bình của kênh — đáng reup |
| **▲ số** cạnh views | Tăng thêm bao nhiêu views kể từ lần sync trước |
| **tương tác %** | (Likes + bình luận + chia sẻ) / views — càng cao càng dễ viral |
| **Đăng x giờ trước** | Thời điểm đăng thật, chính xác tới từng giờ |

### Sắp xếp & tìm kiếm
- **Mới đăng nhất** — bắt trend sớm
- **Tăng nhanh nhất** — video đang lên trong khoảng giữa 2 lần sync
- **Views / Likes cao nhất** — video đã chứng minh hiệu quả
- **Tương tác cao nhất** — video có tỉ lệ tương tác tốt dù ít views
- Ô tìm kiếm lọc theo tiêu đề

### Tải video từ spy
- **"⬇ Tải về"** → thêm vào thư viện Tải Video
- **"→ Studio"** → tải về **và đưa thẳng vào Video Studio** để cắt ghép ngay

### Quy trình Reup hoàn chỉnh
```
Spy kênh → → Studio → Cắt ghép + nhạc + chữ → Nhân 100 bản → Đăng nhiều Fanpage
```
Hoặc cách cũ, giữ nguyên video gốc:
```
Spy kênh → Tải về → Tạo biến thể → Kiểm tra trùng lặp → Content Studio → Đăng Reels
```

---

## 💬 Unified Inbox

- Xem tất cả comment từ mọi Fanpage tại một nơi
- Lọc theo Page, trạng thái (đã đọc/chưa đọc)
- Trả lời comment trực tiếp

---

## 📈 Phân Tích

### Metrics theo dõi
- **Engagement rate** từng Page
- **Top video** theo views/likes/shares
- **Viral detection** — video vượt ngưỡng tự động
- **Trend** theo ngày/tuần/tháng

### Cảnh báo Telegram
- Khi có video viral → Thông báo Telegram tự động
- Cài đặt ngưỡng trong **Cài Đặt**

---

## ⚙️ Cài Đặt

### Telegram Bot
1. Vào **Cài Đặt** → Tab "Telegram"
2. Nhập **Bot Token** (tạo từ @BotFather)
3. Nhập **Chat ID** (nhận từ @userinfobot)
4. Bấm **"Lưu"** → Test kết nối

### Ngưỡng Viral
- **Views threshold**: Số views để đánh dấu viral (VD: 10,000)
- **Likes threshold**: Số likes tối thiểu
- **Auto-check interval**: Thời gian kiểm tra tự động (phút)

---

## ❓ FAQ & Xử Lý Lỗi

### "License đã hết hạn"
→ Liên hệ Admin lấy key mới. **Dữ liệu không mất.**

### "License không khớp với máy này"
→ Bạn đang dùng tool trên máy khác. Tool chỉ chạy trên máy đã kích hoạt.

### Spy TikTok báo "Unable to extract secondary user ID" hoặc "Unexpected response"
TikTok đổi cấu trúc trang liên tục, bản `yt-dlp` cũ sẽ không quét được nữa.
Khắc phục: mở Command Prompt / Terminal tại thư mục tool và chạy:

    venv\Scripts\python -m pip install -U yt-dlp        (Windows)
    venv/bin/python -m pip install -U yt-dlp             (Mac)

Rồi khởi động lại tool. Nếu vẫn lỗi, báo Admin.

### Đăng bài báo "Ứng dụng Facebook thiếu quyền đăng bài lên Page"
Đã cấp full quyền cho token mà vẫn báo thiếu? Vào **Fanpage** → bấm nút **"Quyền"**
ở Page đang lỗi. Tool hỏi thẳng Facebook và cho biết chính xác:

- **Nếu báo THIẾU quyền:** token của Page được cấp *tại thời điểm quét Fanpage*.
  Cấp thêm quyền cho ứng dụng sau đó mà không quét lại thì Page vẫn giữ token cũ.
  → Vào **Tài Khoản** → **"Cập nhật token"** (nút này tự quét lại toàn bộ Page).
- **Nếu báo ĐÃ CÓ đủ quyền:** vấn đề ở phía ứng dụng Facebook —
  thường là App đang ở chế độ **Development** (chỉ đăng được lên Page mà bạn là
  quản trị viên), hoặc chưa qua **App Review** cho `pages_manage_posts`.

### Đăng bài báo "Session has expired" / "Error validating access token" (lỗi 190)
Token Facebook đã chết. **Đây là lỗi hay gặp nhất.**

**Nguyên nhân thường gặp:** token lấy từ Graph API Explorer chỉ sống **1–2 tiếng**.
Muốn có token dùng được **60 ngày** thì bắt buộc phải nhập cả **App ID** và **App Secret**
— thiếu một trong hai là token sẽ chết ngay hôm sau.

**Kiểm tra trước:** bấm **"Kiểm tra token"** — tool hỏi thẳng Facebook và hiện bảng:

| Dòng | Ý nghĩa |
|---|---|
| **Còn lại** | Token sống được bao lâu nữa |
| **Loại token** | *NGẮN HẠN (1-2 tiếng)* hay *Dài hạn* |
| **Có App Secret** | Ghi *CHƯA* nghĩa là đã tìm ra nguyên nhân |

**Cách sửa:**
1. Vào **Tài Khoản** → bấm **"Cập nhật token"** ở tài khoản đang lỗi
2. Dán **User Access Token** mới
3. Nhập đủ **App ID** và **App Secret** (lấy ở Facebook Developer → Settings → Basic)
4. Bấm **"Cập nhật & Quét lại Page"**

> ⚠️ **Quan trọng:** mỗi Fanpage có token riêng, được cấp dựa trên token tài khoản
> lúc quét. Chỉ đổi token tài khoản mà **không quét lại Page** thì các Page vẫn dùng
> token cũ đã chết → đăng vẫn lỗi. Nút "Cập nhật & Quét lại Page" đã làm cả hai việc.

Muốn kiểm tra trước khi đăng: bấm **"Kiểm tra token"** — tool hỏi thẳng Facebook
và cho biết token còn sống không, còn bao nhiêu ngày.

### "Tải video thất bại"
→ Kiểm tra:
- Link hợp lệ?
- Internet ổn định?
- Thử link khác cùng nền tảng

### "FFmpeg not found"
→ FFmpeg chưa cài hoặc chưa thêm vào PATH:
```bash
# Kiểm tra
ffmpeg -version

# Nếu chưa có:
# 1. Tải FFmpeg từ https://ffmpeg.org/download.html
# 2. Giải nén → copy vào C:\ffmpeg\
# 3. Thêm C:\ffmpeg\bin vào PATH
```

### "Lỗi kết nối server"
→ Đảm bảo `start.bat` đang chạy. Tải lại trang: **Ctrl + F5**

### "Video không tạo được biến thể"
→ Kiểm tra file gốc có bị hỏng không. Thử tải lại video.

### Video Studio: "Ghép video thất bại"
→ Thường do một clip bị lỗi hoặc quá ngắn:
- Mỗi cảnh phải dài **ít nhất 0.3 giây**
- Hiệu ứng chuyển cảnh không được dài hơn cảnh ngắn nhất — giảm độ dài hiệu ứng xuống 0.3s
- Thử xoá clip đó và tải lên lại
- Xem chi tiết lỗi trong `data/app.log`

### Video Studio: "Ghép video thất bại — FFmpeg trên máy này thiếu bộ lọc ..."
→ Bản FFmpeg đang cài là **bản rút gọn**, thiếu bộ lọc mà tool cần. Hay gặp nhất là
`drawtext` — bộ lọc viết chữ lên video, chỉ có ở bản FFmpeg đầy đủ. Máy vẫn ghép
được video bình thường cho tới lúc dùng đến tính năng đó thì mới lộ ra.

Cách sửa:
- **Windows:** tải `ffmpeg-release-full.7z` ở https://www.gyan.dev/ffmpeg/builds/,
  giải nén, thay thư mục FFmpeg cũ, rồi **đóng hẳn tool và mở lại**.
- **Mac:** chạy `brew reinstall ffmpeg` rồi mở lại tool.

Kiểm tra nhanh máy có `drawtext` chưa — mở Command Prompt và gõ:
```
ffmpeg -hide_banner -filters | findstr drawtext
```
Máy Mac thì thay `findstr` bằng `grep`. Không ra dòng nào nghĩa là đang thiếu.

### Video Studio: "Cảnh #N đang dùng một clip đã bị xoá khỏi kho"
→ Dự án có cảnh trỏ tới clip không còn trong kho (thường do đã xoá clip đó đi).
Lên **bước 2**, sẽ thấy dải cảnh báo đỏ — bấm **"Xoá N cảnh lỗi"** là ghép được ngay.
Nếu vẫn muốn giữ cảnh đó thì tải lại clip lên rồi thêm cảnh mới.

### Video Studio: "Chưa ghép video base"
→ Phải bấm **"Ghép video & Xem trước"** (bước 5) xong mới nhân bản được ở bước 6.

### Video Studio: chữ tiếng Việt bị lỗi font
→ Tool dùng font Segoe UI của Windows. Nếu máy thiếu font, chữ có thể hiện sai —
liên hệ Admin. **Emoji không hiển thị được** là bình thường, hãy dùng chữ thường.

### Video Studio: render quá lâu
→ Bình thường mỗi bản mất 10–30 giây. Nếu render 100 bản, cứ để chạy nền và làm việc khác —
tiến trình vẫn tiếp tục. Không tắt tool giữa chừng.

### Video Studio: mất các bản đã render sau khi tắt tool
→ Không mất. Mở lại trang **Video Studio**, chọn tên dự án ở ô thả xuống trên cùng —
timeline và toàn bộ bản render sẽ hiện lại.

---

## 📜 Quy Định Sử Dụng

### ✅ Được phép
- Sử dụng tool trên máy công ty đã được cấp key
- Tải, spoof, đăng video theo quy trình làm việc

### ❌ Không được phép
- **KHÔNG** chia sẻ License Key cho bất kỳ ai
- **KHÔNG** copy tool về máy cá nhân
- **KHÔNG** sửa đổi mã nguồn
- **KHÔNG** sử dụng tool ngoài mục đích công việc

### ⚠️ Vi phạm
- Key sẽ bị vô hiệu hóa
- Admin sẽ không cấp key mới

---

> 📞 **Hỗ trợ kỹ thuật:** Liên hệ Admin
> 🔄 **Cập nhật tool:** Admin sẽ cài đặt phiên bản mới khi có
