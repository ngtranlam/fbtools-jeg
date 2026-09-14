// JEG Social Tools — Tổng Quan Dashboard
const DashboardPage = {
    async render() {
        // Fetch all stats in parallel
        let pageStats = {}, analytics = {}, storage = {}, notPosted = {}, oldVideos = [], oldJobs = [];
        try { pageStats = await API.get('/api/pages/stats'); } catch (e) { pageStats = {}; }
        try { analytics = await API.get('/api/posts/analytics?days=7'); } catch (e) { analytics = {}; }
        try { storage = await API.get('/api/settings/storage'); } catch (e) { storage = {}; }
        try { notPosted = await API.get('/api/pages/not-posted-today'); } catch (e) { notPosted = {}; }
        try {
            const vRes = await API.listVideos();
            oldVideos = vRes.videos || [];
        } catch (e) { /* empty */ }
        try {
            const jRes = await API.listJobs();
            oldJobs = jRes.jobs || [];
        } catch (e) { /* empty */ }

        const totalVariants = oldJobs.reduce((sum, j) => sum + (j.variants?.length || 0), 0);

        const topPages = (analytics.top_pages || []).slice(0, 5);
        const topViral = (analytics.top_viral || []).slice(0, 5);
        const notPostedPages = notPosted.pages || [];
        const notPostedCount = notPosted.not_posted_count || 0;
        const totalActive = notPosted.total_active || 0;
        const postedCount = totalActive - notPostedCount;

        return `
            <div class="page-header">
                <h1 class="page-title">🚀 JEG Social Tools</h1>
                <p class="page-subtitle">Bảng điều khiển hệ thống quản lý Fanpage</p>
            </div>

            <!-- Viral Stats Row -->
            <div class="stats-grid stats-grid-5">
                <div class="stat-card stat-glow-teal">
                    <div class="stat-icon teal">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    </div>
                    <div>
                        <div class="stat-value">${pageStats.active_pages || 0}</div>
                        <div class="stat-label">Pages hoạt động</div>
                    </div>
                </div>

                <div class="stat-card stat-glow-blue">
                    <div class="stat-icon blue">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    </div>
                    <div>
                        <div class="stat-value">${this.formatNumber(pageStats.total_views || 0)}</div>
                        <div class="stat-label">Tổng lượt xem</div>
                    </div>
                </div>

                <div class="stat-card stat-glow-yellow">
                    <div class="stat-icon amber">🟡</div>
                    <div>
                        <div class="stat-value">${pageStats.catching_count || 0}</div>
                        <div class="stat-label">Cắn View (>10K)</div>
                    </div>
                </div>

                <div class="stat-card stat-glow-orange">
                    <div class="stat-icon" style="background: rgba(249, 115, 22, 0.15); color: #f97316;">🟠</div>
                    <div>
                        <div class="stat-value">${pageStats.viral_count || 0}</div>
                        <div class="stat-label">Viral (>100K)</div>
                    </div>
                </div>

                <div class="stat-card stat-glow-red">
                    <div class="stat-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">🔴</div>
                    <div>
                        <div class="stat-value">${pageStats.super_viral_count || 0}</div>
                        <div class="stat-label">Siêu Viral (>1M)</div>
                    </div>
                </div>
            </div>

            <!-- Secondary Stats -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon teal">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                    </div>
                    <div>
                        <div class="stat-value">${oldVideos.length}</div>
                        <div class="stat-label">Video đã tải</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon amber">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
                    </div>
                    <div>
                        <div class="stat-value">${totalVariants}</div>
                        <div class="stat-label">Biến thể đã tạo</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon blue">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <div>
                        <div class="stat-value">${pageStats.total_posts || 0}</div>
                        <div class="stat-label">Bài đã đăng</div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(168, 85, 247, 0.15); color: #a855f7;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                    </div>
                    <div>
                        <div class="stat-value">${storage.total_size_gb || 0} GB</div>
                        <div class="stat-label">Dung lượng sử dụng</div>
                    </div>
                </div>
            </div>

            <!-- Pages Not Posted Today -->
            <div class="card not-posted-card" id="not-posted-today-card">
                <div class="card-header" id="not-posted-toggle" style="cursor: pointer;">
                    <h3 class="card-title">
                        ${notPostedCount > 0
                            ? `⚠️ Pages chưa đăng hôm nay — <span class="not-posted-count">${notPostedCount}</span>/${totalActive}`
                            : `✅ Tất cả pages đã đăng hôm nay — ${totalActive}/${totalActive}`
                        }
                    </h3>
                    ${notPostedCount > 0 ? `
                        <div class="not-posted-progress-wrap">
                            <div class="not-posted-progress">
                                <div class="not-posted-progress-bar" style="width: ${totalActive > 0 ? (postedCount / totalActive * 100) : 0}%"></div>
                            </div>
                            <span class="not-posted-ratio">${postedCount}/${totalActive} đã đăng</span>
                        </div>
                        <svg class="not-posted-chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                    ` : ''}
                </div>
                ${notPostedCount > 0 ? `
                    <div class="card-body not-posted-list" id="not-posted-list" style="display: none;">
                        <table class="data-table compact">
                            <thead>
                                <tr>
                                    <th>Tên Page</th>
                                    <th>Tài khoản</th>
                                    <th>Followers</th>
                                    <th>Fanpage</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${notPostedPages.map(p => `
                                    <tr>
                                        <td class="page-name-cell">
                                            <span class="not-posted-dot"></span>
                                            ${p.page_name}
                                        </td>
                                        <td class="account-cell">${p.account_name}</td>
                                        <td>${this.formatNumber(p.followers_count)}</td>
                                        <td>
                                            ${p.fb_url
                                                ? `<a href="${p.fb_url}" target="_blank" rel="noopener" class="fb-link-btn">
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                                                    Mở FB
                                                   </a>`
                                                : '<span class="text-muted">—</span>'
                                            }
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ` : ''}
            </div>

            <!-- Two columns: Top Pages + Top Viral -->
            <div class="dashboard-grid-two">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🏆 Top Pages (7 ngày)</h3>
                    </div>
                    <div class="card-body">
                        ${topPages.length ? `
                            <table class="data-table compact">
                                <thead><tr><th>Page</th><th>Bài đăng</th><th>Lượt xem</th></tr></thead>
                                <tbody>
                                    ${topPages.map((p, i) => `
                                        <tr>
                                            <td><span class="rank-badge rank-${i + 1}">#${i + 1}</span> ${p.page_name}</td>
                                            <td>${p.post_count}</td>
                                            <td class="views-cell">${this.formatNumber(p.total_views)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        ` : '<div class="empty-mini">Chưa có dữ liệu</div>'}
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🔥 Video đang Viral</h3>
                    </div>
                    <div class="card-body">
                        ${topViral.length ? `
                            <table class="data-table compact viral-table">
                                <thead><tr>
                                    <th>Video</th>
                                    <th>Mức độ</th>
                                    <th>Lượt xem</th>
                                    <th>Ngày đăng</th>
                                </tr></thead>
                                <tbody>
                                    ${topViral.map(v => {
                                        const caption = (v.caption || '').replace(/\n/g, ' ').substring(0, 50);
                                        const title = caption || 'Video không có tiêu đề';
                                        const fbLink = v.fb_post_id ? `https://facebook.com/${v.fb_post_id}` : '';
                                        const postedDate = v.posted_at ? new Date(v.posted_at).toLocaleDateString('vi-VN') : '—';
                                        return `
                                        <tr>
                                            <td class="viral-video-cell">
                                                <div class="viral-video-info">
                                                    <span class="viral-page-name">${v.page_name}</span>
                                                    ${fbLink 
                                                        ? `<a href="${fbLink}" target="_blank" rel="noopener" class="viral-video-link" title="${title}">${title.length > 45 ? title + '…' : title} <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a>`
                                                        : `<span class="viral-video-link no-link">${title}</span>`
                                                    }
                                                </div>
                                            </td>
                                            <td>${this.viralBadge(v.viral_level)}</td>
                                            <td class="views-cell">${this.formatNumber(v.views_count)}</td>
                                            <td class="date-cell">${postedDate}</td>
                                        </tr>`;
                                    }).join('')}
                                </tbody>
                            </table>
                        ` : '<div class="empty-mini">Chưa có video viral</div>'}
                    </div>
                </div>
            </div>
        `;
    },

    formatNumber(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return n.toString();
    },

    viralBadge(level) {
        const map = {
            catching: '<span class="viral-badge catching">🟡 Cắn View</span>',
            viral: '<span class="viral-badge viral">🟠 Viral</span>',
            super_viral: '<span class="viral-badge super-viral">🔴 Siêu Viral</span>',
        };
        return map[level] || '';
    },

    init() {
        // Toggle not-posted list on click
        const toggle = document.getElementById('not-posted-toggle');
        const list = document.getElementById('not-posted-list');
        const chevron = toggle?.querySelector('.not-posted-chevron');
        if (toggle && list) {
            toggle.addEventListener('click', () => {
                const isHidden = list.style.display === 'none';
                list.style.display = isHidden ? 'block' : 'none';
                if (chevron) chevron.style.transform = isHidden ? 'rotate(180deg)' : '';
            });
        }
    },
};
