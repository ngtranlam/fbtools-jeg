// MocLan Viral Hub — Global helpers
function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return '--:--';
    const s = Math.round(Number(seconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    return `${m}:${String(sec).padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = Number(bytes);
    while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

// MocLan Viral Hub — Main entry point and router
//
// Vòng đời của một trang:
//   setup()  — chạy MỘT lần lúc khởi động (đăng ký WebSocket, listener toàn cục)
//   reset()  — khi người dùng chuyển TỚI trang này từ trang khác (làm mới state)
//   init()   — sau MỖI lần render (gắn sự kiện cho DOM vừa dựng)
//
// refreshPage() chỉ vẽ lại, KHÔNG gọi reset() — nhờ vậy các thao tác như
// "Sync Data" hay đổi bộ lọc không làm mất lựa chọn hiện tại của người dùng.
//: Phải trùng với BUILD trong backend/main.py. Lệch nhau nghĩa là đã cập nhật
//: mã nguồn nhưng chưa khởi động lại tool.
const APP_BUILD = '2026.09.09';

const App = {
    currentPage: 'dashboard',
    _rendered: null,

    pages: {
        dashboard: DashboardPage,
        accounts: AccountsPage,
        pages_mgmt: PagesPage,
        downloader: DownloaderPage,
        studio: StudioPage,
        spoofer: SpooferPage,
        content_studio: ContentStudioPage,
        checker: CheckerPage,
        batch: BatchPage,
        analytics: AnalyticsPage,
        settings: SettingsPage,
        spy: SpyPage,
        inbox: InboxPage,
    },

    async init() {
        Toast.init();
        Modal.init();
        WS.connect();
        if (typeof QueuePanel !== "undefined") QueuePanel.setup();

        // Cảnh báo sớm nếu máy chủ chạy mã cũ, trước khi người dùng bấm phải
        // tính năng mới rồi nhận thông báo "Not Found" khó hiểu
        this.checkBuildMatch();

        // Đăng ký listener toàn cục một lần duy nhất
        Object.values(this.pages).forEach(page => {
            if (page.setup) page.setup();
        });

        // Hash-based routing
        window.addEventListener('hashchange', () => this.handleRoute());
        this.handleRoute();
    },

    /** Đối chiếu phiên bản giao diện với máy chủ, cảnh báo nếu lệch. */
    async checkBuildMatch() {
        try {
            const res = await fetch('/api/health');
            const info = await res.json();

            if (info.build && info.build !== APP_BUILD) {
                this.showBuildWarning(info.build);
            }
        } catch (e) {
            // Máy chủ chưa sẵn sàng — bỏ qua, phần khác sẽ báo lỗi kết nối
        }
    },

    showBuildWarning(serverBuild) {
        const bar = document.createElement('div');
        bar.className = 'build-warning';
        bar.innerHTML = `
            <div class="build-warning-text">
                <strong>Cần khởi động lại tool.</strong>
                Giao diện đã cập nhật (${APP_BUILD}) nhưng máy chủ vẫn đang chạy
                bản cũ (${serverBuild}). Một số nút sẽ báo lỗi
                <em>"Máy chủ chưa có tính năng này"</em>.
                <br>
                Cách sửa: <strong>đóng hẳn cửa sổ đen / Terminal</strong> của tool,
                mở lại bằng <strong>start.bat</strong> (Mac: <strong>start.command</strong>),
                rồi bấm <strong>Ctrl + F5</strong>.
            </div>
            <button class="btn btn-xs btn-outline" onclick="this.parentElement.remove()">Đã hiểu</button>
        `;
        document.body.appendChild(bar);
    },

    handleRoute() {
        const hash = location.hash.replace('#', '') || 'dashboard';
        this.navigate(hash, false);
    },

    async navigate(page, pushHash = true, { keepState = false } = {}) {
        if (!this.pages[page]) page = 'dashboard';
        const mod = this.pages[page];
        this.currentPage = page;

        if (pushHash) location.hash = page;

        // Update nav
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.page === page);
        });

        // Chỉ làm mới state khi thực sự đổi trang, không phải khi vẽ lại
        if (!keepState && this._rendered !== page && mod.reset) {
            mod.reset();
        }

        // Render page
        const main = document.getElementById('mainContent');
        try {
            main.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
            const html = await mod.render();
            main.innerHTML = html;
            this._rendered = page;

            // Post-render init
            if (mod.init) mod.init();
        } catch (e) {
            console.error('Page render error:', e);
            main.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <div class="empty-state-title">Lỗi tải trang</div>
                    <div class="empty-state-desc">${e.message}</div>
                </div>
            `;
        }
    },

    /** Vẽ lại trang hiện tại nhưng giữ nguyên state (lựa chọn, bộ lọc...). */
    async refreshPage() {
        await this.navigate(this.currentPage, false, { keepState: true });
    },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
