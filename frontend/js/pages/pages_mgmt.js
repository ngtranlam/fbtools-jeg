// Fanpage Management — Click to view video details
const PagesPage = {
    async render() {
        let pages = [];
        try {
            const res = await API.get('/api/pages');
            pages = res.pages || [];
        } catch (e) { /* empty */ }

        return `
            <div class="page-header">
                <h1 class="page-title">📄 Fanpage Management</h1>
                <p class="page-subtitle">${pages.length} Fanpages managed</p>
            </div>

            <div class="filter-bar">
                <input type="text" id="pageSearch" class="form-input search-input" placeholder="🔍 Search Fanpage..." oninput="PagesPage.filterPages()">
            </div>

            <div class="pages-table-wrapper" id="pagesTableWrapper">
                ${pages.length ? `
                    <table class="data-table" id="pagesTable">
                        <thead>
                            <tr>
                                <th>Fanpage</th>
                                <th>Account</th>
                                <th>Followers</th>
                                <th>Posts</th>
                                <th>Total Views</th>
                                <th>Store URL</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${pages.map(p => this.renderPageRow(p)).join('')}
                        </tbody>
                    </table>
                ` : `
                    <div class="empty-state">
                        <div class="empty-state-icon">📄</div>
                        <div class="empty-state-title">No Fanpages yet</div>
                        <div class="empty-state-desc">Go to "Accounts" → "Find Pages" to auto-detect Fanpages</div>
                    </div>
                `}
            </div>

            <!-- Video Detail Panel (hidden by default) -->
            <div id="videoDetailPanel" class="card" style="display:none; margin-top:24px;">
                <div class="card-header">
                    <h3 class="card-title" id="videoDetailTitle">📹 Videos</h3>
                    <div class="header-actions">
                        <select class="form-input form-input-sm" id="videoSortSelect" onchange="PagesPage.sortVideos(this.value)" style="width:auto;">
                            <option value="views_count">Most Views</option>
                            <option value="likes_count">Most Likes</option>
                            <option value="comments_count">Most Comments</option>
                            <option value="posted_at">Latest</option>
                        </select>
                        <button class="btn btn-xs btn-outline" onclick="document.getElementById('videoDetailPanel').style.display='none'">✕ Close</button>
                    </div>
                </div>
                <div class="card-body" id="videoDetailBody">
                    <div class="empty-mini">Loading...</div>
                </div>
            </div>
        `;
    },

    renderPageRow(p) {
        const statusClass = p.status === 'active' ? 'status-active' : 'status-paused';
        const statusText = p.status === 'active' ? 'Active' : 'Paused';

        return `
            <tr data-page-id="${p.id}" class="page-row" style="cursor:pointer;" onclick="PagesPage.showVideos(${p.id}, '${(p.page_name || '').replace(/'/g, "\\'")}')">
                <td class="page-name-cell">
                    <div class="page-info">
                        ${p.avatar_url ? `<img src="${p.avatar_url}" class="page-avatar" alt="">` : '<div class="page-avatar-placeholder">📄</div>'}
                        <div>
                            <div class="page-name">${p.page_name}</div>
                            <div class="page-category">${p.category || ''}</div>
                        </div>
                    </div>
                </td>
                <td>${p.account_name}</td>
                <td>${(p.followers_count || 0).toLocaleString()}</td>
                <td>${p.posts_count || 0}</td>
                <td class="views-cell">${DashboardPage.formatNumber(p.total_views || 0)}</td>
                <td>
                    ${p.store_url
                        ? `<a href="${p.store_url}" target="_blank" class="store-link" title="${p.store_url}" onclick="event.stopPropagation()">🔗 Link</a>`
                        : `<button class="btn btn-xs btn-outline" onclick="event.stopPropagation(); PagesPage.editStoreUrl(${p.id})">+ Add</button>`
                    }
                </td>
                <td><span class="status-pill ${statusClass}">${statusText}</span></td>
                <td>
                    <div class="row-actions" onclick="event.stopPropagation()">
                        <button class="btn btn-xs btn-outline" onclick="PagesPage.checkPermissions(${p.id})" title="Kiểm tra quyền đăng bài">Quyền</button>
                        <button class="btn btn-xs btn-outline" onclick="PagesPage.editPage(${p.id})" title="Settings">⚙️</button>
                        <button class="btn btn-xs btn-outline" onclick="PagesPage.toggleStatus(${p.id}, '${p.status}')" title="${p.status === 'active' ? 'Pause' : 'Activate'}">
                            ${p.status === 'active' ? '⏸️' : '▶️'}
                        </button>
                    </div>
                </td>
            </tr>
        `;
    },

    // ========== VIDEO DETAIL PANEL ==========
    _currentPageId: null,

    async showVideos(pageId, pageName) {
        this._currentPageId = pageId;
        const panel = document.getElementById('videoDetailPanel');
        const title = document.getElementById('videoDetailTitle');
        const body = document.getElementById('videoDetailBody');

        panel.style.display = 'block';
        title.textContent = `📹 ${pageName} — Videos`;
        body.innerHTML = '<div class="empty-mini">⏳ Loading videos...</div>';
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        try {
            const sortBy = document.getElementById('videoSortSelect')?.value || 'views_count';
            const res = await API.get(`/api/pages/${pageId}/videos?sort_by=${sortBy}`);
            const videos = res.videos || [];

            if (!videos.length) {
                body.innerHTML = '<div class="empty-mini">No published videos yet on this page.</div>';
                return;
            }

            body.innerHTML = `
                <div class="video-detail-summary" style="margin-bottom:16px; display:flex; gap:16px; flex-wrap:wrap;">
                    <div class="stat-mini"><strong>${videos.length}</strong> videos</div>
                    <div class="stat-mini">👁 <strong>${this._fmtNum(videos.reduce((s,v) => s + (v.views_count||0), 0))}</strong> total views</div>
                    <div class="stat-mini">❤ <strong>${this._fmtNum(videos.reduce((s,v) => s + (v.likes_count||0), 0))}</strong> total likes</div>
                    <div class="stat-mini">💬 <strong>${this._fmtNum(videos.reduce((s,v) => s + (v.comments_count||0), 0))}</strong> total comments</div>
                </div>
                <table class="data-table compact">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Caption</th>
                            <th>Posted</th>
                            <th>👁 Views</th>
                            <th>❤ Likes</th>
                            <th>💬 Comments</th>
                            <th>↗ Shares</th>
                            <th>Status</th>
                            <th>Link</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${videos.map((v, i) => `
                            <tr>
                                <td>${i + 1}</td>
                                <td style="max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${(v.caption||'').replace(/"/g, '&quot;')}">${v.caption || '—'}</td>
                                <td style="white-space:nowrap;">${v.posted_at ? new Date(v.posted_at).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'}) : '—'}</td>
                                <td class="views-cell"><strong>${this._fmtNum(v.views_count || 0)}</strong></td>
                                <td>${this._fmtNum(v.likes_count || 0)}</td>
                                <td>${this._fmtNum(v.comments_count || 0)}</td>
                                <td>${this._fmtNum(v.shares_count || 0)}</td>
                                <td>${this._viralBadge(v.viral_level)}</td>
                                <td>${v.fb_post_id ? `<a href="https://www.facebook.com/${v.fb_post_id}" target="_blank" class="btn btn-xs btn-outline" onclick="event.stopPropagation()">↗ FB</a>` : '—'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (e) {
            body.innerHTML = `<div class="empty-mini" style="color:var(--danger);">Error: ${e.message}</div>`;
        }
    },

    async sortVideos(sortBy) {
        if (this._currentPageId) {
            const title = document.getElementById('videoDetailTitle')?.textContent?.replace('📹 ', '').split(' — ')[0] || 'Page';
            await this.showVideos(this._currentPageId, title);
        }
    },

    _fmtNum(n) {
        if (!n) return '0';
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return String(n);
    },

    _viralBadge(level) {
        const map = {
            catching: '<span class="viral-badge catching" style="font-size:11px;">🟡 10K+</span>',
            viral: '<span class="viral-badge viral" style="font-size:11px;">🟠 100K+</span>',
            super_viral: '<span class="viral-badge super-viral" style="font-size:11px;">🔴 1M+</span>',
        };
        return map[level] || '<span style="color:var(--text-muted); font-size:11px;">—</span>';
    },

    // ========== EXISTING FEATURES ==========
    filterPages() {
        const query = document.getElementById('pageSearch').value.toLowerCase();
        document.querySelectorAll('.page-row').forEach(row => {
            const name = row.querySelector('.page-name')?.textContent.toLowerCase() || '';
            row.style.display = name.includes(query) ? '' : 'none';
        });
    },

    editStoreUrl(pageId) {
        Modal.open(`
            <h3>Add Store URL</h3>
            <form onsubmit="PagesPage.submitStoreUrl(event, ${pageId})">
                <div class="form-group">
                    <label>Store URL</label>
                    <input type="url" id="storeUrlInput" class="form-input" placeholder="https://yourstore.com/product" required>
                    <small class="form-hint">Product link will be auto-commented when video goes viral</small>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-outline" onclick="Modal.close()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save</button>
                </div>
            </form>
        `);
    },

    async submitStoreUrl(e, pageId) {
        e.preventDefault();
        try {
            await API.put(`/api/pages/${pageId}`, {
                store_url: document.getElementById('storeUrlInput').value.trim(),
            });
            Toast.success('Store URL updated!');
            Modal.close();
            App.refreshPage();
        } catch (e) {
            Toast.error('Error: ' + e.message);
        }
    },

    /** Hỏi Facebook xem Page này có đủ quyền đăng bài chưa. */
    async checkPermissions(pageId) {
        Toast.info('Đang kiểm tra quyền...');
        try {
            const res = await API.get(`/api/pages/${pageId}/diagnose-permissions`);
            const thieu = /THIẾU quyền/.test(res.detail || '');
            const noiDung = (res.detail || 'Không có thông tin')
                .replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));
            Modal.open(`
                <h3 class="modal-title">${thieu ? 'Page đang thiếu quyền' : 'Kết quả kiểm tra quyền'}</h3>
                <pre class="fb-error-box">${noiDung}</pre>
                <div class="modal-actions">
                    <button class="btn btn-outline" onclick="Modal.close()">Đóng</button>
                    <button class="btn btn-primary" onclick="Modal.close(); App.navigate('accounts')">
                        Sang mục Tài Khoản
                    </button>
                </div>
            `);
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    editPage(pageId) {
        Modal.open(`
            <h3>Fanpage Settings</h3>
            <form onsubmit="PagesPage.submitEdit(event, ${pageId})">
                <div class="form-group">
                    <label>Store URL</label>
                    <input type="url" id="editStoreUrl" class="form-input" placeholder="https://yourstore.com/product">
                </div>
                <div class="form-group">
                    <label>Comment Templates (one per line, use {store_url} as placeholder)</label>
                    <textarea id="editCommentTemplates" class="form-input" rows="5" placeholder="Check this out at {store_url}"></textarea>
                    <small class="form-hint">Leave empty to use the 30 default templates</small>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-outline" onclick="Modal.close()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save</button>
                </div>
            </form>
        `);
    },

    async submitEdit(e, pageId) {
        e.preventDefault();
        const templates = document.getElementById('editCommentTemplates').value.trim();
        try {
            await API.put(`/api/pages/${pageId}`, {
                store_url: document.getElementById('editStoreUrl').value.trim() || null,
                comment_templates: templates ? templates.split('\n').filter(t => t.trim()) : null,
            });
            Toast.success('Updated!');
            Modal.close();
            App.refreshPage();
        } catch (e) {
            Toast.error('Error: ' + e.message);
        }
    },

    async toggleStatus(pageId, currentStatus) {
        const newStatus = currentStatus === 'active' ? 'paused' : 'active';
        try {
            await API.put(`/api/pages/${pageId}`, { status: newStatus });
            Toast.success(newStatus === 'active' ? 'Activated' : 'Paused');
            App.refreshPage();
        } catch (e) {
            Toast.error('Error: ' + e.message);
        }
    },

    init() {},
};
