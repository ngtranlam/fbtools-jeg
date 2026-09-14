// Phân tích & Theo dõi Bài Đăng
const AnalyticsPage = {
    async render() {
        let posts = [], analytics = {};
        try {
            const res = await API.get('/api/posts?limit=50');
            posts = res.posts || [];
        } catch (e) { /* empty */ }
        try {
            analytics = await API.get('/api/posts/analytics?days=7');
        } catch (e) { analytics = {}; }

        const dailyStats = analytics.daily_stats || [];

        return `
            <div class="page-header">
                <h1 class="page-title">📊 Phân Tích & Theo Dõi</h1>
                <p class="page-subtitle">Theo dõi hiệu suất Reels và video viral</p>
            </div>

            <!-- Mini Chart -->
            <div class="card" style="margin-bottom: 1.5rem;">
                <div class="card-header">
                    <h3 class="card-title">📈 Lượt xem theo ngày (7 ngày)</h3>
                </div>
                <div class="card-body">
                    <div class="mini-chart" id="viewsChart">
                        ${dailyStats.length ? this.renderBarChart(dailyStats) : '<div class="empty-mini">Chưa có dữ liệu</div>'}
                    </div>
                </div>
            </div>

            <!-- Filter -->
            <div class="filter-bar">
                <select id="filterStatus" class="form-input filter-select" onchange="AnalyticsPage.filterPosts()">
                    <option value="">Tất cả trạng thái</option>
                    <option value="posted">Đã đăng</option>
                    <option value="scheduled">Đã lên lịch</option>
                    <option value="failed">Thất bại</option>
                </select>
                <select id="filterViral" class="form-input filter-select" onchange="AnalyticsPage.filterPosts()">
                    <option value="">Tất cả mức độ</option>
                    <option value="catching">🟡 Cắn View</option>
                    <option value="viral">🟠 Viral</option>
                    <option value="super_viral">🔴 Siêu Viral</option>
                </select>
            </div>

            <!-- Posts Table -->
            <div class="card">
                <div class="card-body" style="padding: 0;">
                    <table class="data-table" id="postsTable">
                        <thead>
                            <tr>
                                <th>Page</th>
                                <th>Trạng thái</th>
                                <th>Views</th>
                                <th>Likes</th>
                                <th>Comments</th>
                                <th>Shares</th>
                                <th>Viral</th>
                                <th>Ngày đăng</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${posts.map(p => this.renderPostRow(p)).join('')}
                        </tbody>
                    </table>
                    ${!posts.length ? '<div class="empty-mini" style="padding: 2rem;">Chưa có bài đăng</div>' : ''}
                </div>
            </div>
        `;
    },

    renderBarChart(data) {
        if (!data.length) return '';
        const maxViews = Math.max(...data.map(d => d.views || 0), 1);

        return `
            <div class="bar-chart">
                ${data.map(d => {
                    const height = Math.max(((d.views || 0) / maxViews) * 100, 4);
                    const label = new Date(d.day).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
                    return `
                        <div class="bar-column">
                            <div class="bar-value">${DashboardPage.formatNumber(d.views || 0)}</div>
                            <div class="bar" style="height: ${height}%"></div>
                            <div class="bar-label">${label}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    },

    renderPostRow(p) {
        const statusMap = {
            posted: '<span class="status-pill status-active">Đã đăng</span>',
            scheduled: '<span class="status-pill status-pending">Lên lịch</span>',
            failed: '<span class="status-pill status-error">Thất bại</span>',
            draft: '<span class="status-pill status-paused">Nháp</span>',
        };
        const viralMap = {
            catching: '<span class="viral-badge catching">🟡 Cắn View</span>',
            viral: '<span class="viral-badge viral">🟠 Viral</span>',
            super_viral: '<span class="viral-badge super-viral">🔴 Siêu Viral</span>',
            none: '',
        };

        return `
            <tr data-status="${p.status}" data-viral="${p.viral_level}">
                <td class="page-name-cell">
                    <div class="page-info">
                        ${p.avatar_url ? `<img src="${p.avatar_url}" class="page-avatar-sm">` : '📄'}
                        <span>${p.page_name}</span>
                    </div>
                </td>
                <td>${statusMap[p.status] || p.status}</td>
                <td class="views-cell">${(p.views_count || 0).toLocaleString()}</td>
                <td>${(p.likes_count || 0).toLocaleString()}</td>
                <td>${(p.comments_count || 0).toLocaleString()}</td>
                <td>${(p.shares_count || 0).toLocaleString()}</td>
                <td>${viralMap[p.viral_level] || ''}</td>
                <td>${p.posted_at ? new Date(p.posted_at).toLocaleDateString('vi-VN') : p.scheduled_at ? new Date(p.scheduled_at).toLocaleDateString('vi-VN') : '-'}</td>
            </tr>
        `;
    },

    filterPosts() {
        const status = document.getElementById('filterStatus').value;
        const viral = document.getElementById('filterViral').value;
        document.querySelectorAll('#postsTable tbody tr').forEach(row => {
            const matchStatus = !status || row.dataset.status === status;
            const matchViral = !viral || row.dataset.viral === viral;
            row.style.display = matchStatus && matchViral ? '' : 'none';
        });
    },

    init() {},
};
