// API client for Video Spoofer Pro
const API = {
    BASE: '',

    async request(method, path, data = null) {
        const opts = {
            method,
            headers: {},
        };
        if (data && !(data instanceof FormData)) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(data);
        } else if (data instanceof FormData) {
            opts.body = data;
        }
        const res = await fetch(`${this.BASE}${path}`, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            let msg = err.detail || err.message || err.error || 'Request failed';
            if (typeof msg === 'object') msg = msg.message || msg.error || JSON.stringify(msg);

            // "Not Found" trần trụi nghĩa là máy chủ không có đường dẫn này —
            // gần như luôn do đã cập nhật tool nhưng chưa khởi động lại, khiến
            // giao diện mới gọi vào máy chủ vẫn đang chạy mã nguồn cũ.
            if (res.status === 404 && /^not found$/i.test(String(msg).trim())) {
                msg = 'Máy chủ chưa có tính năng này.\n'
                    + 'Hãy ĐÓNG hẳn tool (đóng cửa sổ đen / Terminal) rồi mở lại '
                    + 'bằng start.bat (Mac: start.command), sau đó bấm Ctrl + F5.';
            }
            throw new Error(msg);
        }
        return res.json();
    },

    get(path) { return this.request('GET', path); },
    post(path, data) { return this.request('POST', path, data); },
    put(path, data) { return this.request('PUT', path, data); },
    del(path) { return this.request('DELETE', path); },
    delete(path) { return this.request('DELETE', path); },

    // ── Videos ──
    downloadVideo(url) { return this.post('/api/videos/download', { url }); },

    uploadVideo(file) {
        const fd = new FormData();
        fd.append('file', file);
        return this.post('/api/videos/upload', fd);
    },

    listVideos() { return this.get('/api/videos/'); },
    getVideo(id) { return this.get(`/api/videos/${id}`); },
    deleteVideo(id) { return this.del(`/api/videos/${id}`); },

    // ── Spoof ──
    startSpoof(data) { return this.post('/api/spoof/', data); },
    listJobs() { return this.get('/api/spoof/jobs'); },
    getJob(id) { return this.get(`/api/spoof/jobs/${id}`); },
    getProfiles() { return this.get('/api/spoof/profiles'); },

    // ── Export ──
    exportVariants(jobId, exportPath) {
        return this.post('/api/spoof/export', { job_id: jobId, export_path: exportPath });
    },
    browseFolders(path = '') {
        return this.get(`/api/spoof/export/browse?path=${encodeURIComponent(path)}`);
    },

    // ── Check ──
    checkUniqueness(paths) { return this.post('/api/check/', { video_paths: paths }); },
    checkJob(jobId) { return this.get(`/api/check/job/${jobId}`); },

    // ── Metadata ──
    getMetadata(id) { return this.get(`/api/metadata/${id}`); },
    updateMetadata(id, metadata) { return this.put(`/api/metadata/${id}`, { video_id: id, metadata }); },
    stripMetadata(id) { return this.post(`/api/metadata/strip/${id}`); },
};
