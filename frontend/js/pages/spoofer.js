// Trang Tạo Biến Thể — tạo video variants
const SpooferPage = {
    selectedVideo: null,
    selectedProfile: 'medium',
    numVariants: 5,

    async render() {
        let videos = [];
        let profiles = [];
        let jobs = [];
        try {
            const vRes = await API.listVideos();
            videos = vRes.videos || [];
        } catch (e) { /* empty */ }
        try {
            const pRes = await API.getProfiles();
            profiles = pRes.profiles || [];
        } catch (e) { /* empty */ }
        try {
            const jRes = await API.listJobs();
            jobs = jRes.jobs || [];
        } catch (e) { /* empty */ }

        return `
            <div class="page-header">
                <h1 class="page-title">Tạo Biến Thể Video</h1>
                <p class="page-subtitle">Tạo các phiên bản khác nhau để vượt qua kiểm tra trùng lặp</p>
            </div>

            <div class="grid-2">
                <!-- Left: Config -->
                <div>
                    <!-- Step 1: Select Video -->
                    <div class="card mb-6">
                        <div class="card-header">
                            <h3 class="card-title">① Chọn Video</h3>
                        </div>
                        ${videos.length > 0 ? `
                            <div class="video-list" id="spoofVideoList">
                                ${videos.map(v => `
                                    <div class="video-item ${this.selectedVideo === v.id ? 'selected' : ''}"
                                         onclick="SpooferPage.selectVideo('${v.id}')" id="spoof-vid-${v.id}">
                                        ${VideoPlayer.createThumbnail(v.filepath)}
                                        <div class="video-info">
                                            <div class="video-name">${v.title || v.filename}</div>
                                            <div class="video-meta">
                                                <span class="platform-icon platform-${v.platform}">${v.platform}</span>
                                                <span>${formatDuration(v.duration)}</span>
                                                <span>${v.width}×${v.height}</span>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div class="empty-state">
                                <div class="empty-state-icon">📹</div>
                                <div class="empty-state-title">Chưa có video nào</div>
                                <div class="empty-state-desc">
                                    <button class="btn btn-primary mt-4" onclick="App.navigate('downloader')">Đi tải video</button>
                                </div>
                            </div>
                        `}
                    </div>

                    <!-- Step 2: Configuration -->
                    <div class="card mb-6">
                        <div class="card-header">
                            <h3 class="card-title">② Cài Đặt</h3>
                        </div>

                        <!-- Number of variants -->
                        <div class="form-group">
                            <label class="input-label">Số lượng biến thể: <strong id="variantCountLabel">${this.numVariants}</strong></label>
                            <input type="range" class="range-slider" min="1" max="10" value="${this.numVariants}"
                                   oninput="SpooferPage.numVariants = this.value; document.getElementById('variantCountLabel').textContent = this.value">
                            <div class="flex justify-between" style="font-size: var(--text-xs); color: var(--text-muted)">
                                <span>1</span><span>5</span><span>10</span>
                            </div>
                        </div>

                        <hr class="divider">

                        <!-- Transform Profile -->
                        <div class="form-group">
                            <label class="input-label">Chế độ biến đổi</label>
                            <div class="profile-grid">
                                ${profiles.map(p => `
                                    <div class="profile-card ${this.selectedProfile === p.id ? 'selected' : ''}"
                                         onclick="SpooferPage.selectProfile('${p.id}')">
                                        <div class="profile-card-name">${p.id === 'light' ? '🌿' : p.id === 'medium' ? '⚡' : '🔥'} ${p.name}</div>
                                        <div class="profile-card-desc">${p.description}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <hr class="divider">

                        <!-- Upscale -->
                        <div class="flex items-center justify-between">
                            <div>
                                <div style="font-weight: 500">Nâng Cấp Độ Phân Giải (FFmpeg Lanczos)</div>
                                <div style="font-size: var(--text-xs); color: var(--text-secondary)">Tăng 2x — miễn phí, không cần GPU</div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="upscaleToggle">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>

                    <!-- Start Button -->
                    <button class="btn btn-primary btn-lg w-full" id="startSpoofBtn" onclick="SpooferPage.startSpoof()"
                            ${!this.selectedVideo ? 'disabled' : ''}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        Bắt Đầu Tạo Biến Thể
                    </button>
                </div>

                <!-- Right: Results -->
                <div>
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">③ Kết Quả</h3>
                        </div>

                        <div id="spoofResults">
                            ${jobs.length > 0 ? SpooferPage.renderJobs(jobs) : `
                                <div class="empty-state">
                                    <div class="empty-state-icon">🎬</div>
                                    <div class="empty-state-title">Chưa có biến thể nào</div>
                                    <div class="empty-state-desc">Chọn video và bấm tạo biến thể để xem kết quả</div>
                                </div>
                            `}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Folder Picker Modal -->
            <div id="folderPickerModal" class="modal-overlay" style="display:none">
                <div class="modal-content" style="max-width: 600px">
                    <div class="modal-header">
                        <h3>📁 Chọn Thư Mục Lưu</h3>
                        <button class="btn-icon" onclick="SpooferPage.closeFolderPicker()">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="flex items-center gap-2 mb-4">
                            <button class="btn btn-sm btn-secondary" onclick="SpooferPage.folderGoUp()" id="folderUpBtn">⬆ Lên</button>
                            <input type="text" class="input" id="folderPathInput" placeholder="Nhập đường dẫn thư mục..."
                                   style="flex: 1" onkeydown="if(event.key==='Enter') SpooferPage.navigateFolder(this.value)">
                            <button class="btn btn-sm btn-secondary" onclick="SpooferPage.navigateFolder(document.getElementById('folderPathInput').value)">→ Đi</button>
                        </div>
                        <div id="folderList" style="max-height: 350px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-md);">
                            <div class="empty-state" style="padding: var(--space-6)">
                                <div class="spinner"></div>
                                <div class="empty-state-title">Đang tải...</div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer" style="display: flex; gap: var(--space-3); justify-content: flex-end; padding-top: var(--space-4); border-top: 1px solid var(--border-color);">
                        <button class="btn btn-secondary" onclick="SpooferPage.closeFolderPicker()">Hủy</button>
                        <button class="btn btn-primary" id="folderSelectBtn" onclick="SpooferPage.confirmExport()">
                            📥 Lưu Vào Đây
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    renderJobs(jobs) {
        return jobs.map(j => `
            <div class="card mb-4" style="padding: var(--space-4)">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <span class="badge ${j.status === 'completed' ? 'badge-green' : j.status === 'running' ? 'badge-amber' : j.status === 'failed' ? 'badge-red' : 'badge-blue'}">
                            ${j.status === 'completed' ? 'HOÀN THÀNH' : j.status === 'running' ? 'ĐANG XỬ LÝ' : j.status === 'failed' ? 'THẤT BẠI' : 'CHỜ'}
                        </span>
                        <span style="font-size: var(--text-xs); color: var(--text-secondary); margin-left: var(--space-2)">
                            Mã: ${j.job_id}
                        </span>
                    </div>
                    <span style="font-size: var(--text-xs); color: var(--text-secondary)">
                        ${j.completed_variants}/${j.num_variants} biến thể
                    </span>
                </div>

                ${j.status === 'running' ? Progress.create(`job-${j.job_id}`) : ''}

                ${j.variants && j.variants.length > 0 ? `
                    <div class="variant-grid" style="margin-top: var(--space-3)">
                        ${j.variants.map(v => `
                            <div class="variant-card">
                                <video controls preload="metadata" style="width:100%; aspect-ratio: 9/16; object-fit: contain; background: #000;">
                                    <source src="/media/variants/${j.job_id}/${v.filename}" type="video/mp4">
                                </video>
                                <div class="variant-card-info">
                                    <div class="variant-card-title">${v.id}</div>
                                    <div class="variant-card-meta">
                                        ${v.transforms_applied.slice(0, 4).map(t => `<span class="badge badge-teal">${t}</span>`).join('')}
                                        ${v.transforms_applied.length > 4 ? `<span class="badge badge-blue">+${v.transforms_applied.length - 4}</span>` : ''}
                                    </div>
                                    <div style="font-size: var(--text-xs); color: var(--text-secondary); margin-top: var(--space-2)">
                                        ${v.width}×${v.height} · ${formatFileSize(v.filesize)}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="mt-4 flex gap-3" style="flex-wrap: wrap">
                        <button class="btn btn-sm btn-secondary" onclick="SpooferPage.checkUniqueness('${j.job_id}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                            Kiểm Tra Trùng Lặp
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="SpooferPage.openFolderPicker('${j.job_id}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Xuất Ra Thư Mục
                        </button>
                    </div>
                ` : ''}
            </div>
        `).join('');
    },

    selectVideo(id) {
        this.selectedVideo = id;
        document.querySelectorAll('#spoofVideoList .video-item').forEach(el => el.classList.remove('selected'));
        const el = document.getElementById(`spoof-vid-${id}`);
        if (el) el.classList.add('selected');
        const btn = document.getElementById('startSpoofBtn');
        if (btn) btn.disabled = false;
    },

    selectProfile(id) {
        this.selectedProfile = id;
        document.querySelectorAll('.profile-card').forEach(el => el.classList.remove('selected'));
        event.currentTarget.classList.add('selected');
    },

    async startSpoof() {
        if (!this.selectedVideo) { Toast.warning('Vui lòng chọn video'); return; }

        const btn = document.getElementById('startSpoofBtn');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div> Đang xử lý...';

        try {
            const upscale = document.getElementById('upscaleToggle')?.checked || false;
            const res = await API.startSpoof({
                video_id: this.selectedVideo,
                num_variants: parseInt(this.numVariants),
                profile: this.selectedProfile,
                upscale: upscale,
                upscale_factor: 2,
            });
            Toast.success(`Đã bắt đầu tạo biến thể: ${res.job.job_id}`);
        } catch (e) {
            Toast.error(`Tạo biến thể thất bại: ${e.message}`);
            btn.disabled = false;
            btn.innerHTML = '▶ Bắt Đầu Tạo Biến Thể';
        }
    },

    async checkUniqueness(jobId) {
        Toast.info('Đang kiểm tra trùng lặp...');
        try {
            const res = await API.checkJob(jobId);
            App.navigate('checker');
            window._lastReport = res.report;
        } catch (e) {
            Toast.error(`Kiểm tra thất bại: ${e.message}`);
        }
    },

    // ── Folder Picker ──────────────────────────────
    _exportJobId: null,
    _currentBrowsePath: '',

    openFolderPicker(jobId) {
        this._exportJobId = jobId;
        const modal = document.getElementById('folderPickerModal');
        if (modal) {
            modal.style.display = 'flex';
            this.loadFolders('');
        }
    },

    closeFolderPicker() {
        const modal = document.getElementById('folderPickerModal');
        if (modal) modal.style.display = 'none';
    },

    async loadFolders(path) {
        this._currentBrowsePath = path;
        const pathInput = document.getElementById('folderPathInput');
        if (pathInput) pathInput.value = path;

        const list = document.getElementById('folderList');
        list.innerHTML = '<div style="padding: var(--space-6); text-align: center"><div class="spinner"></div></div>';

        try {
            const res = await API.browseFolders(path);
            const folders = res.folders || [];

            if (folders.length === 0) {
                list.innerHTML = `
                    <div style="padding: var(--space-6); text-align: center; color: var(--text-secondary)">
                        📂 Thư mục trống — Bạn có thể lưu vào đây
                    </div>
                `;
                return;
            }

            list.innerHTML = folders.map(f => `
                <div class="folder-item" onclick="SpooferPage.navigateFolder('${f.path.replace(/\\/g, '\\\\')}')"
                     style="padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--border-color);
                            cursor: pointer; display: flex; align-items: center; gap: var(--space-3);
                            transition: background 0.15s;">
                    <span style="font-size: 1.2em">${f.type === 'drive' ? '💾' : '📁'}</span>
                    <span style="flex: 1; font-size: var(--text-sm)">${f.name}</span>
                    <span style="color: var(--text-muted); font-size: var(--text-xs)">→</span>
                </div>
            `).join('');

            list.querySelectorAll('.folder-item').forEach(el => {
                el.addEventListener('mouseenter', () => el.style.background = 'var(--bg-tertiary)');
                el.addEventListener('mouseleave', () => el.style.background = 'transparent');
            });
        } catch (e) {
            list.innerHTML = `<div style="padding: var(--space-6); text-align: center; color: var(--text-error)">❌ ${e.message}</div>`;
        }
    },

    navigateFolder(path) {
        if (path) this.loadFolders(path);
    },

    folderGoUp() {
        if (!this._currentBrowsePath) return;
        const parts = this._currentBrowsePath.replace(/\\/g, '/').split('/');
        parts.pop();
        const parent = parts.join('/') || parts.join('\\');
        if (parent.length <= 2) {
            this.loadFolders('');
        } else {
            this.loadFolders(parent);
        }
    },

    async confirmExport() {
        const path = document.getElementById('folderPathInput')?.value;
        if (!path) {
            Toast.warning('Vui lòng nhập hoặc chọn thư mục');
            return;
        }
        if (!this._exportJobId) return;

        const btn = document.getElementById('folderSelectBtn');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner"></div> Đang xuất...';

        try {
            const res = await API.exportVariants(this._exportJobId, path);
            Toast.success(`Đã xuất ${res.exported_count} biến thể vào ${res.export_path}`);
            this.closeFolderPicker();
        } catch (e) {
            Toast.error(`Xuất thất bại: ${e.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📥 Lưu Vào Đây';
        }
    },

    setup() {
        WS.on('spoof_progress', (data) => {
            if (data.status === 'processing') {
                const pct = (data.current / data.total) * 100;
                Progress.update(`job-${data.job_id}`, pct, data.message);
            } else if (data.status === 'completed') {
                Toast.success(data.message || 'Tất cả biến thể đã tạo xong!');
                setTimeout(() => App.refreshPage(), 500);
            } else if (data.status === 'failed') {
                Toast.error(data.message || 'Tạo biến thể thất bại');
                setTimeout(() => App.refreshPage(), 500);
            }
        });
    },
};
