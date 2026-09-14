// Trang Tải Video — Tải từ link + Upload file
const DownloaderPage = {
    downloading: false,

    async render() {
        let videos = [];
        try {
            const res = await API.listVideos();
            videos = res.videos || [];
        } catch (e) { /* empty */ }

        return `
            <div class="page-header">
                <h1 class="page-title">Tải Video</h1>
                <p class="page-subtitle">Tải video từ link hoặc upload file từ máy tính</p>
            </div>

            <div class="grid-2">
                <!-- URL Download -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🔗 Tải Từ Link</h3>
                    </div>
                    <p style="color: var(--text-secondary); font-size: var(--text-sm); margin-bottom: var(--space-4)">
                        Dán link TikTok, Facebook, YouTube hoặc Instagram
                    </p>
                    <div class="input-group mb-4">
                        <input type="text" id="downloadUrl" placeholder="https://www.tiktok.com/@user/video/..." style="font-family: var(--font-mono); font-size: var(--text-sm)">
                        <button class="btn btn-primary" id="downloadBtn" onclick="DownloaderPage.handleDownload()">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Tải Về
                        </button>
                    </div>
                    <label class="radio-chip ${this.autoToStudio ? 'active' : ''}" style="margin-bottom:16px">
                        <input type="checkbox" ${this.autoToStudio ? 'checked' : ''}
                               onchange="DownloaderPage.setAutoToStudio(this.checked); App.refreshPage()">
                        Tải xong tự chuyển sang Video Studio
                    </label>
                    <div id="downloadProgress" style="display:none">
                        ${Progress.create('download')}
                    </div>
                    <div class="flex gap-2 mt-4">
                        <span class="platform-icon platform-youtube">YouTube</span>
                        <span class="platform-icon platform-tiktok">TikTok</span>
                        <span class="platform-icon platform-facebook">Facebook</span>
                        <span class="platform-icon platform-instagram">Instagram</span>
                    </div>
                </div>

                <!-- File Upload -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">📁 Upload Từ Máy Tính</h3>
                    </div>
                    <div class="upload-zone" id="uploadZone">
                        <div class="upload-zone-icon">
                            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                        </div>
                        <div class="upload-zone-title">Kéo thả file video vào đây</div>
                        <div class="upload-zone-subtitle">hoặc bấm để chọn file — MP4, MOV, AVI, MKV</div>
                        <input type="file" id="uploadInput" accept="video/*" onchange="DownloaderPage.handleUpload(event)">
                    </div>
                    <div id="uploadProgress" style="display:none; margin-top: var(--space-4)">
                        ${Progress.create('upload')}
                    </div>
                </div>
            </div>

            <!-- Video Library -->
            <div class="card mt-6">
                <div class="card-header">
                    <h3 class="card-title">📚 Thư Viện Video (${videos.length})</h3>
                    ${videos.length > 0 ? `<button class="btn btn-sm btn-secondary" onclick="DownloaderPage.refreshList()">Làm mới</button>` : ''}
                </div>

                ${videos.length > 0 ? `
                    <div class="video-list" id="videoList">
                        ${videos.map(v => DownloaderPage.renderVideoItem(v)).join('')}
                    </div>
                ` : `
                    <div class="empty-state">
                        <div class="empty-state-icon">📂</div>
                        <div class="empty-state-title">Chưa có video nào</div>
                        <div class="empty-state-desc">Tải từ link hoặc upload file để bắt đầu</div>
                    </div>
                `}
            </div>
        `;
    },

    renderVideoItem(v) {
        return `
            <div class="video-item" id="video-${v.id}">
                ${VideoPlayer.createThumbnail(v.filepath)}
                <div class="video-info">
                    <div class="video-name">${v.title || v.filename}</div>
                    <div class="video-meta">
                        <span class="platform-icon platform-${v.platform}">${v.platform}</span>
                        <span>${formatDuration(v.duration)}</span>
                        <span>${v.width}×${v.height}</span>
                        <span>${formatFileSize(v.filesize)}</span>
                    </div>
                </div>
                <div class="video-actions">
                    <button class="btn btn-sm btn-accent"
                            onclick='event.stopPropagation(); DownloaderPage.sendToStudio(${JSON.stringify(v).replace(/'/g, "&#39;")}, { navigate: true })'
                            title="Đưa video này sang Video Studio để cắt ghép">
                        → Studio
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); App.navigate('spoofer')" title="Tạo biến thể">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/></svg>
                        Tạo Biến Thể
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); DownloaderPage.deleteVideo('${v.id}')" title="Xóa">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            </div>
        `;
    },

    /** Bật/tắt việc tự đưa video sang Video Studio sau khi tải xong.
     *  Lưu vào trình duyệt để lần sau vẫn nhớ lựa chọn. */
    get autoToStudio() {
        return localStorage.getItem('autoToStudio') !== '0';
    },

    setAutoToStudio(on) {
        localStorage.setItem('autoToStudio', on ? '1' : '0');
        Toast.info(on
            ? 'Tải xong sẽ tự chuyển sang Video Studio'
            : 'Tải xong sẽ ở lại trang này');
    },

    /** Đưa một video vào kho Video Studio (và chuyển tab nếu cần). */
    async sendToStudio(video, { navigate = false } = {}) {
        try {
            Toast.info('Đang đưa vào Video Studio...');
            const res = await API.post('/api/studio/assets/import', {
                filepath: video.filepath,
                name: video.title || '',
            });

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Không đưa được vào Studio');
                return false;
            }

            Toast.success(`Đã thêm "${res.asset.name}" vào Video Studio`);

            if (navigate) {
                // Mở Studio và giữ nguyên dự án đang làm dở — clip vừa thêm nằm
                // sẵn trong kho ở bước 1, người dùng tự quyết định dùng hay không
                await App.navigate('studio');
                Toast.info('Clip đã có trong kho ở bước 1 — bấm "+ Thêm cảnh" để dùng');
            } else {
                await App.refreshPage();
            }
            return true;
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            return false;
        }
    },

    async handleDownload() {
        const input = document.getElementById('downloadUrl');
        const url = input.value.trim();
        if (!url) { Toast.warning('Vui lòng nhập link video'); return; }

        const btn = document.getElementById('downloadBtn');
        btn.disabled = true;
        document.getElementById('downloadProgress').style.display = 'block';

        try {
            Toast.info('Đang bắt đầu tải...');
            const res = await API.downloadVideo(url);
            Toast.success(`Đã tải: ${res.video.title}`);
            input.value = '';

            if (this.autoToStudio) {
                await this.sendToStudio(res.video, { navigate: true });
            } else {
                await App.refreshPage();
            }
        } catch (e) {
            Toast.error(`Tải thất bại: ${e.message}`);
        } finally {
            btn.disabled = false;
        }
    },

    async handleUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        document.getElementById('uploadProgress').style.display = 'block';
        Progress.update('upload', 50, 'Đang upload...');

        try {
            const res = await API.uploadVideo(file);
            Progress.update('upload', 100, 'Upload hoàn tất!');
            Toast.success(`Đã upload: ${res.video.title}`);

            if (this.autoToStudio) {
                await this.sendToStudio(res.video, { navigate: true });
            } else {
                await App.refreshPage();
            }
        } catch (e) {
            Toast.error(`Upload thất bại: ${e.message}`);
        }
    },

    async deleteVideo(id) {
        Modal.confirm('Xóa Video', 'Bạn có chắc muốn xóa video này không?', async () => {
            try {
                await API.deleteVideo(id);
                Toast.success('Đã xóa video');
                await App.refreshPage();
            } catch (e) {
                Toast.error(`Xóa thất bại: ${e.message}`);
            }
        });
    },

    async refreshList() {
        await App.refreshPage();
        Toast.info('Đã làm mới danh sách');
    },

    init() {
        const zone = document.getElementById('uploadZone');
        if (!zone) return;

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('video/')) {
                const input = document.getElementById('uploadInput');
                const dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;
                DownloaderPage.handleUpload({ target: { files: [file] } });
            } else {
                Toast.warning('Vui lòng thả file video');
            }
        });

        WS.on('download_progress', (data) => {
            const progDiv = document.getElementById('downloadProgress');
            if (progDiv) progDiv.style.display = 'block';
            const pct = data.progress || 0;
            Progress.update('download', pct, data.message || '');

            if (data.status === 'completed') {
                setTimeout(() => App.refreshPage(), 1000);
            }
        });
    },
};
