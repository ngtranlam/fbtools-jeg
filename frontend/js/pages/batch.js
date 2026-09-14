// Trang Xử Lý Hàng Loạt
const BatchPage = {
    async render() {
        let videos = [];
        let jobs = [];
        try {
            const vRes = await API.listVideos();
            videos = vRes.videos || [];
        } catch (e) { /* empty */ }
        try {
            const jRes = await API.listJobs();
            jobs = jRes.jobs || [];
        } catch (e) { /* empty */ }

        const running = jobs.filter(j => j.status === 'running');
        const pending = jobs.filter(j => j.status === 'pending');
        const completed = jobs.filter(j => j.status === 'completed');
        const failed = jobs.filter(j => j.status === 'failed');

        return `
            <div class="page-header">
                <h1 class="page-title">Xử Lý Hàng Loạt</h1>
                <p class="page-subtitle">Xử lý nhiều video cùng lúc</p>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon blue"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
                    <div><div class="stat-value">${pending.length}</div><div class="stat-label">Đang chờ</div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon amber"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/></svg></div>
                    <div><div class="stat-value">${running.length}</div><div class="stat-label">Đang xử lý</div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon green"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
                    <div><div class="stat-value">${completed.length}</div><div class="stat-label">Hoàn thành</div></div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: var(--error-dim); color: var(--error)"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></div>
                    <div><div class="stat-value">${failed.length}</div><div class="stat-label">Thất bại</div></div>
                </div>
            </div>

            <!-- Batch Start -->
            <div class="card mb-6">
                <div class="card-header">
                    <h3 class="card-title">Tạo Biến Thể Hàng Loạt</h3>
                    <button class="btn btn-sm btn-primary" onclick="BatchPage.startBatch()">Bắt Đầu</button>
                </div>
                <p style="color: var(--text-secondary); font-size: var(--text-sm); margin-bottom: var(--space-4)">
                    Chọn nhiều video để xử lý cùng cài đặt.
                </p>
                <div class="video-list" id="batchVideoList">
                    ${videos.map(v => `
                        <div class="video-item" onclick="this.classList.toggle('selected')" data-id="${v.id}">
                            ${VideoPlayer.createThumbnail(v.filepath)}
                            <div class="video-info">
                                <div class="video-name">${v.title || v.filename}</div>
                                <div class="video-meta">
                                    <span>${formatDuration(v.duration)}</span>
                                    <span>${formatFileSize(v.filesize)}</span>
                                </div>
                            </div>
                            <input type="checkbox" style="width:18px; height:18px; accent-color: var(--accent)">
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- All Jobs -->
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Tất Cả Công Việc (${jobs.length})</h3>
                    <button class="btn btn-sm btn-secondary" onclick="App.refreshPage()">Làm Mới</button>
                </div>
                ${jobs.length > 0 ? `
                    <div class="video-list">
                        ${jobs.map(j => `
                            <div class="video-item">
                                <div class="video-thumb" style="background: ${j.status === 'completed' ? 'var(--success-dim)' : j.status === 'running' ? 'var(--warning-dim)' : j.status === 'failed' ? 'var(--error-dim)' : 'var(--bg-primary)'}; color: ${j.status === 'completed' ? 'var(--success)' : j.status === 'running' ? 'var(--warning)' : 'var(--error)'}">
                                    ${j.status === 'completed' ? '✅' : j.status === 'running' ? '🔄' : j.status === 'failed' ? '❌' : '⏳'}
                                </div>
                                <div class="video-info">
                                    <div class="video-name">Mã ${j.job_id}</div>
                                    <div class="video-meta">
                                        <span class="badge ${j.status === 'completed' ? 'badge-green' : j.status === 'running' ? 'badge-amber' : 'badge-red'}">${j.status === 'completed' ? 'hoàn thành' : j.status === 'running' ? 'đang xử lý' : 'thất bại'}</span>
                                        <span>${j.completed_variants}/${j.num_variants} biến thể</span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="empty-state">
                        <div class="empty-state-icon">📦</div>
                        <div class="empty-state-title">Chưa có công việc nào</div>
                    </div>
                `}
            </div>
        `;
    },

    async startBatch() {
        const selected = document.querySelectorAll('#batchVideoList .video-item.selected');
        if (selected.length === 0) {
            Toast.warning('Vui lòng chọn ít nhất một video');
            return;
        }

        const videoIds = Array.from(selected).map(el => el.dataset.id);
        Toast.info(`Đang bắt đầu xử lý ${videoIds.length} video...`);

        for (const id of videoIds) {
            try {
                await API.startSpoof({
                    video_id: id,
                    num_variants: 5,
                    profile: 'medium',
                });
            } catch (e) {
                Toast.error(`Thất bại cho ${id}: ${e.message}`);
            }
        }

        Toast.success(`Đã bắt đầu xử lý ${videoIds.length} video`);
        setTimeout(() => App.refreshPage(), 1000);
    },

    init() {},
};
