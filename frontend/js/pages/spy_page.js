// Spy Đối Thủ — theo dõi kênh TikTok / YouTube, phát hiện video mới và video đang lên
const SpyPage = {
    channels: [],
    selectedChannel: null,
    videos: [],
    stats: {},
    sortBy: 'published_at',
    sortOrder: 'desc',
    keyword: '',
    lastSync: null,
    autoSync: null,

    // ── Vòng đời ──────────────────────────────────────────
    reset() {
        this.selectedChannel = null;
        this.videos = [];
        this.stats = {};
        this.sortBy = 'published_at';
        this.sortOrder = 'desc';
        this.keyword = '';
        this.lastSync = null;
    },

    async render() {
        await this.loadChannels();

        // Giữ lại tham chiếu kênh đang chọn sau khi tải lại danh sách
        if (this.selectedChannel) {
            const fresh = this.channels.find(c => c.id === this.selectedChannel.id);
            this.selectedChannel = fresh || null;
        }

        return `
            <div class="page-header">
                <div class="page-header-main">
                    <h1 class="page-title">Spy Đối Thủ</h1>
                    <p class="page-subtitle">Theo dõi kênh TikTok / YouTube — bắt video mới và video đang lên</p>
                </div>
                <div class="page-header-actions">
                    ${this._renderAutoSyncChip()}
                    <button class="btn btn-outline" onclick="SpyPage.syncAll()" id="syncAllBtn">
                        Sync tất cả kênh
                    </button>
                    <button class="btn btn-primary" onclick="SpyPage.showAddModal()">
                        + Thêm Kênh
                    </button>
                </div>
            </div>

            <div class="spy-layout">
                ${this._renderChannelSidebar()}
                <div class="spy-main" id="spyMain">
                    ${this.selectedChannel ? this._renderChannelView() : this._renderNoChannel()}
                </div>
            </div>
        `;
    },

    init() {
        const search = document.getElementById('spySearch');
        if (search) {
            search.value = this.keyword;
            search.addEventListener('input', (e) => {
                this.keyword = e.target.value;
                this._repaintGrid();
            });
        }
    },

    // ── Sidebar danh sách kênh ────────────────────────────
    _renderChannelSidebar() {
        return `
            <aside class="spy-sidebar card">
                <div class="card-header">
                    <h3 class="card-title">Kênh Theo Dõi</h3>
                    <span class="badge">${this.channels.length}</span>
                </div>
                <div class="card-body spy-channel-list">
                    ${this.channels.length ? this.channels.map(ch => `
                        <button class="spy-channel-item ${this.selectedChannel?.id === ch.id ? 'active' : ''}"
                                onclick="SpyPage.selectChannel(${ch.id})">
                            <div class="spy-channel-avatar">
                                ${ch.avatar_url
                                    ? `<img src="${this._attr(ch.avatar_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
                                    : `<span class="spy-platform-icon">${this._platformIcon(ch.platform)}</span>`}
                            </div>
                            <div class="spy-channel-info">
                                <div class="spy-channel-name">${this._esc(ch.channel_name)}</div>
                                <div class="spy-channel-meta">
                                    <span class="spy-platform-badge ${ch.platform}">${this._platformLabel(ch.platform)}</span>
                                    ${ch.followers_count ? `<span>${this._num(ch.followers_count)} follow</span>` : ''}
                                </div>
                                <div class="spy-channel-sync">
                                    ${ch.videos_count || 0} video
                                    · ${ch.last_synced_at ? this._timeAgo(ch.last_synced_at) : 'chưa sync'}
                                    ${ch.last_sync_new > 0 ? `<span class="spy-new-dot">+${ch.last_sync_new} mới</span>` : ''}
                                </div>
                            </div>
                            <span class="spy-delete-btn" title="Xoá kênh"
                                  onclick="event.stopPropagation(); SpyPage.deleteChannel(${ch.id})">✕</span>
                        </button>
                    `).join('') : `
                        <div class="empty-mini">
                            <p>Chưa theo dõi kênh nào</p>
                            <button class="btn btn-sm btn-primary" onclick="SpyPage.showAddModal()">+ Thêm kênh đầu tiên</button>
                        </div>
                    `}
                </div>
            </aside>
        `;
    },

    _renderNoChannel() {
        return `
            <div class="empty-state">
                <div class="empty-state-icon">🕵️</div>
                <div class="empty-state-title">Chọn kênh để xem video</div>
                <div class="empty-state-desc">
                    Chọn một kênh ở cột bên trái, hoặc thêm kênh mới để bắt đầu theo dõi đối thủ.
                </div>
            </div>
        `;
    },

    // ── Khu vực chính ─────────────────────────────────────
    _renderChannelView() {
        const ch = this.selectedChannel;
        const s = this.stats || {};

        return `
            <div class="spy-channel-header card">
                <div class="spy-channel-head-top">
                    <div class="spy-channel-identity">
                        <div class="spy-channel-avatar lg">
                            ${ch.avatar_url
                                ? `<img src="${this._attr(ch.avatar_url)}" alt="" referrerpolicy="no-referrer">`
                                : `<span class="spy-platform-icon">${this._platformIcon(ch.platform)}</span>`}
                        </div>
                        <div>
                            <h2 class="spy-channel-title">
                                ${this._esc(ch.channel_name)}
                                <span class="spy-platform-badge ${ch.platform}">${this._platformLabel(ch.platform)}</span>
                            </h2>
                            <div class="spy-channel-subline">
                                ${ch.followers_count ? `${this._num(ch.followers_count)} người theo dõi · ` : ''}
                                Sync lần cuối: ${ch.last_synced_at ? this._timeAgo(ch.last_synced_at) : 'chưa sync'}
                            </div>
                        </div>
                    </div>
                    <div class="spy-head-actions">
                        ${this._isManual(ch.platform) ? `
                            <button class="btn btn-primary" onclick="SpyPage.showAddVideosModal()">
                                + Thêm video
                            </button>
                        ` : ''}
                        <button class="btn btn-accent" onclick="SpyPage.syncChannel()" id="syncBtn">
                            <span class="sync-icon">⟳</span>
                            ${this._isManual(ch.platform) ? 'Cập nhật chỉ số' : 'Sync Data'}
                        </button>
                    </div>
                </div>

                ${this._isManual(ch.platform) ? `
                    <div class="spy-manual-note">
                        <strong>Kênh Facebook hoạt động khác TikTok/YouTube.</strong>
                        Facebook không cho phép quét danh sách video của trang người khác,
                        nên anh/chị hãy <strong>dán link từng video hoặc reel</strong> muốn theo dõi
                        bằng nút <em>"+ Thêm video"</em>. Tool sẽ lo phần cập nhật chỉ số và
                        báo video nào đang tăng views.
                    </div>
                ` : ''}

                <div class="spy-stat-row">
                    ${this._stat('Video đã lưu', this._num(s.total || 0))}
                    ${this._stat('Tổng views', this._num(s.total_views || 0))}
                    ${this._stat('Views trung bình', this._num(s.avg_views || 0))}
                    ${this._stat('Cao nhất', this._num(s.max_views || 0))}
                    ${this._stat('Tương tác TB', (s.avg_engagement || 0) + '%')}
                    ${this._stat('Mới lần sync này', this._num(s.new_count || 0),
                                 s.new_count > 0 ? 'positive' : '')}
                </div>

                ${this.lastSync ? this._renderSyncSummary() : ''}
            </div>

            <div class="spy-toolbar card">
                <input type="text" class="form-input spy-search" id="spySearch"
                       placeholder="Tìm theo tiêu đề video...">
                <div class="spy-toolbar-right">
                    <label class="spy-sort-label">Sắp xếp</label>
                    <select class="form-input form-input-sm" onchange="SpyPage.changeSort(this.value)">
                        <option value="published_at" ${this.sortBy === 'published_at' ? 'selected' : ''}>Mới đăng nhất</option>
                        <option value="views_delta" ${this.sortBy === 'views_delta' ? 'selected' : ''}>Tăng nhanh nhất</option>
                        <option value="views_count" ${this.sortBy === 'views_count' ? 'selected' : ''}>Views cao nhất</option>
                        <option value="likes_count" ${this.sortBy === 'likes_count' ? 'selected' : ''}>Likes cao nhất</option>
                        <option value="engagement_rate" ${this.sortBy === 'engagement_rate' ? 'selected' : ''}>Tương tác cao nhất</option>
                        <option value="duration" ${this.sortBy === 'duration' ? 'selected' : ''}>Thời lượng</option>
                    </select>
                </div>
            </div>

            <div class="spy-video-grid" id="spyVideoGrid">
                ${this._renderCards()}
            </div>
        `;
    },

    _renderSyncSummary() {
        const r = this.lastSync;
        const risers = r.top_risers || [];
        if (!r.new_videos && !risers.length) {
            return `<div class="spy-sync-summary muted">${
                this._esc(r.message || 'Lần sync gần nhất: không có video mới, chỉ số chưa đổi.')
            }</div>`;
        }
        return `
            <div class="spy-sync-summary">
                <strong>${r.manual ? 'Kết quả cập nhật:' : 'Kết quả sync:'}</strong>
                ${r.new_videos ? `<span class="chip chip-success">${r.new_videos} video mới</span>` : ''}
                ${r.updated_videos ? `<span class="chip">${r.updated_videos} video cập nhật chỉ số</span>` : ''}
                ${risers.length ? `
                    <div class="spy-risers">
                        <span class="spy-risers-label">Tăng mạnh nhất:</span>
                        ${risers.slice(0, 3).map(v => `
                            <span class="chip chip-up" title="${this._attr(v.title)}">
                                +${this._num(v.views_delta)} views · ${this._esc(this._truncate(v.title, 32))}
                            </span>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    },

    _stat(label, value, tone = '') {
        return `
            <div class="spy-stat ${tone}">
                <div class="spy-stat-value">${value}</div>
                <div class="spy-stat-label">${label}</div>
            </div>
        `;
    },

    _renderCards() {
        const kw = this.keyword.trim().toLowerCase();
        const list = kw
            ? this.videos.filter(v => (v.title || '').toLowerCase().includes(kw))
            : this.videos;

        if (!list.length) {
            const manual = this._isManual(this.selectedChannel?.platform);
            const emptyMsg = this.videos.length
                ? 'Không có video nào khớp từ khoá.'
                : (manual
                    ? 'Chưa có video nào. Bấm "+ Thêm video" và dán link reel/video Facebook muốn theo dõi.'
                    : 'Chưa có video. Bấm "Sync Data" để tải danh sách video mới nhất.');
            return `
                <div class="empty-mini spy-empty-videos">
                    <p>${emptyMsg}</p>
                    ${!this.videos.length && manual ? `
                        <button class="btn btn-sm btn-primary" onclick="SpyPage.showAddVideosModal()">
                            + Thêm video
                        </button>
                    ` : ''}
                </div>
            `;
        }

        return list.map(v => this._card(v)).join('');
    },

    _card(v) {
        const delta = v.views_delta || 0;
        const published = v.published_at ? new Date(v.published_at) : null;

        return `
            <article class="spy-video-card ${v.reupped ? 'reupped' : ''} ${v.is_new ? 'is-new' : ''}">
                <div class="spy-video-thumb" onclick="SpyPage.previewVideo('${this._attr(v.video_url)}')">
                    ${v.thumbnail_url
                        ? `<img src="${this._attr(v.thumbnail_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
                        : '<div class="spy-thumb-placeholder">🎬</div>'}
                    <div class="spy-thumb-overlay"><span class="spy-play">▶</span></div>
                    ${v.duration ? `<span class="spy-video-duration">${this._dur(v.duration)}</span>` : ''}
                    <div class="spy-badges">
                        ${v.is_new ? '<span class="spy-badge new">MỚI</span>' : ''}
                        ${v.is_outperformer ? '<span class="spy-badge hot">VƯỢT TRỘI</span>' : ''}
                        ${v.reupped ? '<span class="spy-badge done">ĐÃ REUP</span>' : ''}
                    </div>
                </div>

                <div class="spy-video-info">
                    <h4 class="spy-video-title" title="${this._attr(v.title)}">
                        ${this._esc(v.title || 'Không có tiêu đề')}
                    </h4>

                    <div class="spy-video-metrics">
                        <div class="spy-metric primary">
                            <span class="spy-metric-value">${this._num(v.views_count)}</span>
                            <span class="spy-metric-label">views</span>
                            ${delta > 0 ? `<span class="spy-delta up">▲ ${this._num(delta)}</span>` : ''}
                        </div>
                        <div class="spy-metric">
                            <span class="spy-metric-value">${this._num(v.likes_count)}</span>
                            <span class="spy-metric-label">likes</span>
                        </div>
                        <div class="spy-metric">
                            <span class="spy-metric-value">${this._num(v.comments_count)}</span>
                            <span class="spy-metric-label">bình luận</span>
                        </div>
                        <div class="spy-metric">
                            <span class="spy-metric-value">${(v.engagement_rate || 0).toFixed(1)}%</span>
                            <span class="spy-metric-label">tương tác</span>
                        </div>
                    </div>

                    <div class="spy-video-date">
                        ${published
                            ? `Đăng ${this._timeAgo(v.published_at)} · ${published.toLocaleDateString('vi-VN')}`
                            : 'Không rõ ngày đăng'}
                    </div>
                </div>

                <div class="spy-video-actions">
                    <button class="btn btn-xs btn-primary" ${v.reupped ? 'disabled' : ''}
                            onclick="SpyPage.reupVideo('${this._attr(v.video_url)}', this, false)">
                        ${v.reupped ? 'Đã tải' : '⬇ Tải về'}
                    </button>
                    <button class="btn btn-xs btn-accent"
                            onclick="SpyPage.reupVideo('${this._attr(v.video_url)}', this, true)"
                            title="Tải về và đưa thẳng vào Video Studio để cắt ghép">
                        → Studio
                    </button>
                    <a href="${this._attr(v.video_url)}" target="_blank" rel="noopener"
                       class="btn btn-xs btn-outline">Xem gốc</a>
                </div>
            </article>
        `;
    },

    /** Vẽ lại riêng lưới video — giữ nguyên ô tìm kiếm và vị trí cuộn. */
    _repaintGrid() {
        const grid = document.getElementById('spyVideoGrid');
        if (grid) grid.innerHTML = this._renderCards();
    },

    // ── Dữ liệu ───────────────────────────────────────────
    async loadChannels() {
        try {
            const res = await API.get('/api/spy/channels');
            this.channels = res.channels || [];
        } catch (e) {
            this.channels = [];
        }

        try {
            const opts = await API.get('/api/spy/platforms');
            this.autoSync = opts.auto_sync || null;
        } catch (e) {
            this.autoSync = null;
        }
    },

    async loadVideos(channelId) {
        try {
            const res = await API.get(
                `/api/spy/channels/${channelId}/videos` +
                `?sort_by=${this.sortBy}&order=${this.sortOrder}&limit=200`
            );
            this.videos = res.videos || [];
            this.stats = res.stats || {};
        } catch (e) {
            this.videos = [];
            this.stats = {};
        }
    },

    async selectChannel(channelId) {
        this.selectedChannel = this.channels.find(c => c.id === channelId) || null;
        this.lastSync = null;
        this.keyword = '';
        if (this.selectedChannel) await this.loadVideos(channelId);
        App.refreshPage();
    },

    async changeSort(value) {
        this.sortBy = value;
        if (!this.selectedChannel) return;
        await this.loadVideos(this.selectedChannel.id);
        this._repaintGrid();
    },

    // ── Hành động ─────────────────────────────────────────
    async syncChannel() {
        if (!this.selectedChannel) return;
        const channelId = this.selectedChannel.id;

        const btn = document.getElementById('syncBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="sync-icon spinning">⟳</span> Đang sync...';
        }

        try {
            const res = await API.post(`/api/spy/channels/${channelId}/sync`);
            if (res.status !== 'ok') {
                Toast.error(res.error || 'Sync thất bại');
                return;
            }

            this.lastSync = res;
            if (res.manual) {
                // Facebook: không có khái niệm "video mới", chỉ làm mới chỉ số link đã lưu
                Toast.success(res.message || `Đã cập nhật ${res.updated_videos} video`);
                if (res.top_risers?.length) this.sortBy = 'views_delta';
            } else if (res.new_videos > 0) {
                Toast.success(`Có ${res.new_videos} video mới! (${res.updated_videos} video cập nhật chỉ số)`);
                // Ưu tiên xem video mới đăng ngay sau khi sync
                this.sortBy = 'published_at';
            } else {
                Toast.info(`Không có video mới. Đã cập nhật chỉ số ${res.updated_videos} video.`);
            }

            await this.loadChannels();
            this.selectedChannel = this.channels.find(c => c.id === channelId) || null;
            await this.loadVideos(channelId);
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi sync: ' + e.message);
        } finally {
            if (btn && document.body.contains(btn)) {
                btn.disabled = false;
                btn.innerHTML = '<span class="sync-icon">⟳</span> Sync Data';
            }
        }
    },

    async syncAll() {
        if (!this.channels.length) {
            Toast.error('Chưa có kênh nào để sync');
            return;
        }

        const btn = document.getElementById('syncAllBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Đang sync tất cả...'; }

        try {
            Toast.info(`Đang sync ${this.channels.length} kênh, vui lòng đợi...`);
            const res = await API.post('/api/spy/sync-all');
            const failed = (res.channels || []).filter(c => c.error);

            if (res.total_new > 0) {
                Toast.success(`Tổng cộng ${res.total_new} video mới trên ${res.channels.length} kênh`);
            } else {
                Toast.info('Đã sync xong — không có video mới.');
            }
            if (failed.length) {
                Toast.error(`${failed.length} kênh sync lỗi: ${failed.map(c => c.channel_name).join(', ')}`);
            }

            await this.loadChannels();
            if (this.selectedChannel) await this.loadVideos(this.selectedChannel.id);
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        } finally {
            if (btn && document.body.contains(btn)) {
                btn.disabled = false;
                btn.textContent = 'Sync tất cả kênh';
            }
        }
    },

    _renderAutoSyncChip() {
        const a = this.autoSync;
        if (!a) return '';

        const hours = a.interval_minutes >= 60
            ? `${(a.interval_minutes / 60).toFixed(a.interval_minutes % 60 ? 1 : 0)} giờ`
            : `${a.interval_minutes} phút`;

        return `
            <button class="auto-sync-chip ${a.enabled ? 'on' : 'off'}"
                    onclick="SpyPage.showAutoSyncModal()"
                    title="Bấm để chỉnh tự động cập nhật">
                <span class="auto-dot"></span>
                ${a.enabled ? `Tự cập nhật mỗi ${hours}` : 'Tự cập nhật: đang tắt'}
            </button>
        `;
    },

    showAutoSyncModal() {
        const a = this.autoSync || { enabled: true, interval_minutes: 180, alert_views_delta: 5000 };
        Modal.open(`
            <h3 class="modal-title">Tự động cập nhật kênh đối thủ</h3>
            <p class="form-hint" style="margin-bottom:16px">
                Tool chạy nền, tự cập nhật chỉ số tất cả kênh đang theo dõi —
                không cần mở trang này bấm tay. Có video tăng mạnh sẽ báo qua Telegram.
            </p>

            <div class="form-group">
                <label class="radio-chip ${a.enabled ? 'active' : ''}" style="width:100%">
                    <input type="checkbox" id="autoSyncEnabled" ${a.enabled ? 'checked' : ''}>
                    Bật tự động cập nhật
                </label>
            </div>

            <div class="form-group">
                <label>Cập nhật mỗi</label>
                <select class="form-input" id="autoSyncInterval">
                    ${[
                        [60, '1 giờ'], [120, '2 giờ'], [180, '3 giờ (khuyên dùng)'],
                        [360, '6 giờ'], [720, '12 giờ'], [1440, '24 giờ'],
                    ].map(([v, label]) => `
                        <option value="${v}" ${a.interval_minutes === v ? 'selected' : ''}>${label}</option>
                    `).join('')}
                </select>
                <small class="form-hint">
                    Đặt quá dày dễ bị nền tảng chặn vì phải gọi ra ngoài cho từng video.
                    3 giờ là mức an toàn.
                </small>
            </div>

            <div class="form-group">
                <label>Báo Telegram khi video tăng hơn</label>
                <input type="number" class="form-input" id="autoSyncThreshold"
                       min="0" step="1000" value="${a.alert_views_delta}">
                <small class="form-hint">
                    Số views tăng thêm giữa hai lần cập nhật. Để 0 nếu không muốn nhận báo.
                    Cần cài Telegram Bot ở mục Cài Đặt trước.
                </small>
            </div>

            <div class="modal-actions">
                <button class="btn btn-outline" onclick="Modal.close()">Huỷ</button>
                <button class="btn btn-primary" onclick="SpyPage.saveAutoSync()" id="saveAutoBtn">Lưu</button>
            </div>
        `);
    },

    async saveAutoSync() {
        const enabled = document.getElementById('autoSyncEnabled')?.checked ?? true;
        const interval = +(document.getElementById('autoSyncInterval')?.value || 180);
        const threshold = +(document.getElementById('autoSyncThreshold')?.value || 0);

        const btn = document.getElementById('saveAutoBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Đang lưu...'; }

        try {
            const res = await API.put('/api/spy/auto-sync', {
                enabled, interval_minutes: interval, alert_views_delta: threshold,
            });
            this.autoSync = res.auto_sync;
            Modal.close();
            Toast.success(enabled
                ? `Đã bật — tool sẽ tự cập nhật mỗi ${interval >= 60 ? (interval / 60) + ' giờ' : interval + ' phút'}`
                : 'Đã tắt tự động cập nhật');
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (btn) { btn.disabled = false; btn.textContent = 'Lưu'; }
        }
    },

    /** Nền tảng phải dán link thủ công (không quét được danh sách). */
    _isManual(platform) {
        return platform === 'facebook';
    },

    _platformLabel(platform) {
        return { tiktok: 'TikTok', youtube: 'YouTube', facebook: 'Facebook' }[platform] || platform;
    },

    _platformIcon(platform) {
        return { tiktok: '♪', youtube: '▶', facebook: 'f' }[platform] || '●';
    },

    showAddVideosModal() {
        if (!this.selectedChannel) return;
        Modal.open(`
            <h3 class="modal-title">Thêm video vào "${this._esc(this.selectedChannel.channel_name)}"</h3>
            <div class="form-group">
                <label>Dán link video / reel — mỗi dòng một link</label>
                <textarea id="spyVideoUrls" class="form-input" rows="7"
                          placeholder="https://www.facebook.com/reel/1234567890&#10;https://www.facebook.com/watch/?v=1234567890&#10;https://fb.watch/AbCdEf/"></textarea>
                <small class="form-hint">
                    Video phải ở chế độ <strong>công khai</strong> thì mới đọc được chỉ số.
                    Dán được nhiều link cùng lúc. Link đã có sẵn sẽ tự bỏ qua.
                </small>
            </div>
            <div class="modal-actions">
                <button class="btn btn-outline" onclick="Modal.close()">Huỷ</button>
                <button class="btn btn-primary" onclick="SpyPage.addVideos()" id="addVideosBtn">
                    Thêm & Lấy chỉ số
                </button>
            </div>
        `);
    },

    async addVideos() {
        const raw = document.getElementById('spyVideoUrls')?.value || '';
        const urls = raw.split('\n').map(s => s.trim()).filter(Boolean);

        if (!urls.length) {
            Toast.error('Chưa dán link nào');
            return;
        }

        const btn = document.getElementById('addVideosBtn');
        if (btn) { btn.disabled = true; btn.textContent = `Đang đọc ${urls.length} link...`; }

        try {
            const res = await API.post(
                `/api/spy/channels/${this.selectedChannel.id}/videos`, { urls }
            );

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Thêm video thất bại');
                if (btn) { btn.disabled = false; btn.textContent = 'Thêm & Lấy chỉ số'; }
                return;
            }

            Modal.close();
            if (res.added) Toast.success(`Đã thêm ${res.added} video`);
            if (res.skipped) Toast.info(`${res.skipped} link đã có sẵn nên bỏ qua`);
            if (res.failed) {
                Toast.error(`${res.failed} link không đọc được — kiểm tra video có công khai không`);
            }
            if (!res.added && !res.skipped) {
                Toast.error('Không thêm được video nào');
            }

            await this.loadChannels();
            this.selectedChannel = this.channels.find(c => c.id === this.selectedChannel.id) || null;
            await this.loadVideos(this.selectedChannel.id);
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (btn) { btn.disabled = false; btn.textContent = 'Thêm & Lấy chỉ số'; }
        }
    },

    showAddModal() {
        Modal.open(`
            <h3 class="modal-title">Thêm Kênh Spy</h3>
            <div class="form-group">
                <label>URL Kênh (TikTok / YouTube / Facebook)</label>
                <input type="text" id="spyUrl" class="form-input"
                       placeholder="https://www.tiktok.com/@username">
                <small class="form-hint">Dán link trang kênh, không phải link 1 video lẻ.</small>
            </div>
            <div class="spy-platform-help">
                <div><strong>TikTok / YouTube</strong> — tool tự quét danh sách video mới của kênh.</div>
                <div><strong>Facebook</strong> — Facebook không cho quét trang người khác, nên sau khi
                     thêm kênh, anh/chị tự dán link từng video muốn theo dõi. Tool lo phần cập nhật chỉ số.</div>
            </div>
            <div class="form-group">
                <label>Tên hiển thị (tuỳ chọn)</label>
                <input type="text" id="spyChannelName" class="form-input" placeholder="Để trống sẽ tự nhận diện">
            </div>
            <div class="modal-actions">
                <button class="btn btn-outline" onclick="Modal.close()">Huỷ</button>
                <button class="btn btn-primary" onclick="SpyPage.addChannel()">Thêm & Sync</button>
            </div>
        `);
    },

    async addChannel() {
        const url = document.getElementById('spyUrl').value.trim();
        const name = document.getElementById('spyChannelName').value.trim();

        if (!url) {
            Toast.error('Nhập URL kênh');
            return;
        }

        try {
            Toast.info('Đang thêm kênh...');
            const res = await API.post('/api/spy/channels', { channel_url: url, channel_name: name });
            if (res.status !== 'ok') {
                Toast.error(res.error || 'Lỗi thêm kênh');
                return;
            }

            Modal.close();
            const channelId = res.channel.id;
            const platform = res.channel.platform;

            await this.loadChannels();
            this.selectedChannel = this.channels.find(c => c.id === channelId) || null;

            if (this._isManual(platform)) {
                // Facebook: chưa có gì để quét, mở luôn ô dán link cho đỡ mất bước
                Toast.success('Đã thêm kênh Facebook. Giờ dán link video muốn theo dõi.');
                await this.loadVideos(channelId);
                App.refreshPage();
                setTimeout(() => this.showAddVideosModal(), 400);
                return;
            }

            Toast.success('Đã thêm kênh. Đang tải danh sách video...');
            const syncRes = await API.post(`/api/spy/channels/${channelId}/sync`);
            if (syncRes.status === 'ok') {
                this.lastSync = syncRes;
                Toast.success(`Đã tải ${syncRes.new_videos} video từ kênh này`);
            } else {
                Toast.error(syncRes.error || 'Sync thất bại');
            }

            await this.loadVideos(channelId);
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    async deleteChannel(channelId) {
        if (!confirm('Xoá kênh này và toàn bộ video đã lưu?')) return;
        try {
            await API.delete(`/api/spy/channels/${channelId}`);
            Toast.success('Đã xoá kênh');
            if (this.selectedChannel?.id === channelId) {
                this.selectedChannel = null;
                this.videos = [];
                this.stats = {};
            }
            await this.loadChannels();
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    async reupVideo(videoUrl, btn, toStudio) {
        const original = btn ? btn.textContent : '';
        if (btn) { btn.disabled = true; btn.textContent = 'Đang tải...'; }

        try {
            const res = await API.post('/api/spy/reup', {
                video_url: videoUrl,
                to_studio: !!toStudio,
            });

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Tải video thất bại');
                if (btn) { btn.disabled = false; btn.textContent = original; }
                return;
            }

            if (toStudio && res.studio_asset) {
                Toast.success('Đã đưa video vào Video Studio — sang đó để cắt ghép.');
            } else if (toStudio) {
                Toast.success('Đã tải video, nhưng chưa đưa được vào Studio. Kiểm tra Tải Video.');
            } else {
                Toast.success('Đã tải video về thư viện.');
            }
            if (btn) btn.textContent = '✓ Xong';
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (btn) { btn.disabled = false; btn.textContent = original; }
        }
    },

    previewVideo(url) {
        window.open(url, '_blank', 'noopener');
    },

    // ── Tiện ích ──────────────────────────────────────────
    _esc(str) {
        return String(str ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    },

    _attr(str) {
        return this._esc(str);
    },

    _truncate(str, len) {
        const s = String(str ?? '');
        return s.length > len ? s.slice(0, len) + '…' : s;
    },

    _num(num) {
        const n = Number(num) || 0;
        if (n >= 1000000) return (n / 1000000).toFixed(1).replace('.0', '') + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1).replace('.0', '') + 'K';
        return String(n);
    },

    _dur(seconds) {
        const s = Math.round(Number(seconds) || 0);
        if (!s) return '';
        const m = Math.floor(s / 60);
        return `${m}:${String(s % 60).padStart(2, '0')}`;
    },

    _timeAgo(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        if (isNaN(d)) return '';
        const diff = Math.floor((Date.now() - d.getTime()) / 1000);
        if (diff < 0) return 'sắp tới';
        if (diff < 60) return 'vừa xong';
        if (diff < 3600) return Math.floor(diff / 60) + ' phút trước';
        if (diff < 86400) return Math.floor(diff / 3600) + ' giờ trước';
        if (diff < 2592000) return Math.floor(diff / 86400) + ' ngày trước';
        return Math.floor(diff / 2592000) + ' tháng trước';
    },
};
