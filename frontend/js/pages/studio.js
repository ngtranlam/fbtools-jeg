// Video Studio — cắt cảnh, ghép clip, chuyển cảnh, text, nhạc → render hàng loạt → đăng Fanpage
const StudioPage = {
    options: { transitions: [], looks: [], canvas_presets: [] },
    videoAssets: [],
    audioAssets: [],
    pages: [],
    projects: [],

    project: null,
    timeline: null,
    baseUrl: '',
    baseDuration: 0,
    baseStale: false,
    hookPlan: null,
    hookPlanError: '',
    hookPreview: null,
    hookPreviewBusy: 0,
    selectedRenders: null,

    batchJob: null,
    renders: [],
    selectedLooks: [],
    selectedMusic: [],
    batchCount: 20,
    lastExportPath: '',

    // ── Vòng đời ──────────────────────────────────────────
    setup() {
        WS.on('studio_batch', (data) => {
            if (!this.batchJob || data.job_id !== this.batchJob.job_id) return;

            if (data.status === 'processing') {
                // data.current là bản ĐANG làm, chưa xong — phần trăm tính theo số bản đã hoàn tất
                this._updateBatchProgress(data.current - 1, data.total, data.message);
            } else if (data.status === 'variant_done') {
                this.renders.push(data.render);
                this._updateBatchProgress(data.current, data.total,
                    `Đã xong ${data.current}/${data.total} biến thể`);
                this._repaintRenders();
            } else if (data.status === 'completed' || data.status === 'failed') {
                this.batchJob.status = data.status;
                if (data.status === 'completed') {
                    Toast.success(data.message || 'Render xong!');
                } else {
                    Toast.error('Render thất bại. Xem log tại data/app.log');
                }
                this._updateBatchProgress(data.current, data.total, data.message || '');
                // Vẽ lại cả trang để mở bước 7 (chọn Fanpage) khi đã có bản render
                if (App.currentPage === 'studio') App.refreshPage();
            }
        });

        WS.on('studio_compose', (data) => {
            if (data.status === 'processing') {
                this._setComposeStatus('Đang ghép video, vui lòng đợi...', 'working');
            }
        });
    },

    reset() {
        this.project = null;
        // Vào lại trang thì vẫn mở dự án gần nhất; chỉ nút "Dự án mới" mới bật cờ này
        this._startedBlank = false;
        this.timeline = this._blankTimeline();
        this.baseUrl = '';
        this.baseDuration = 0;
        this.baseStale = false;
        this.hookPlan = null;
        this.hookPlanError = '';
        this.hookPreview = null;
        this.hookPreviewBusy = 0;
        this.batchJob = null;
        this.selectedRenders = null;   // null = chọn tất cả
        this.renders = [];
        this.selectedLooks = ['warm', 'cool', 'vivid', 'cinematic'];
        this.selectedMusic = [];
        this.batchCount = 20;
    },

    _blankTimeline() {
        return {
            canvas: { width: 1080, height: 1920, fps: 30, fit: 'cover' },
            segments: [],
            transitions: [],
            texts: [],
            audio: {
                mode: 'original',
                asset_id: null,
                volume: 1.0,
                original_volume: 1.0,
                // Mặc định chỉnh tiếng gốc ở mức vừa — giữ nguyên 100% là dễ bị
                // đối chiếu vân tay âm thanh với video gốc nhất.
                tune: { preset: 'medium' },
            },
            // Hook ngau nhien: moi ban render lay mot doan khac nhau cua clip
            // nguon lam mo dau, phan than giu nguyen.
            hook: {
                enabled: false,
                asset_id: null,
                scenes: 1,
                min_len: 5,
                max_len: 10,
                // Cùng mã trộn thì bảng xem trước và bản render thật ra y hệt nhau
                seed: 0,
                body: { enabled: false, asset_id: null, min_len: 10, max_len: 15 },
            },
        };
    },

    async render() {
        if (!this.timeline) this.reset();
        await this._loadAll();

        return `
            <div class="page-header">
                <div class="page-header-main">
                    <h1 class="page-title">Video Studio</h1>
                    <p class="page-subtitle">
                        Cắt cảnh → ghép clip → chuyển cảnh + chữ + nhạc → nhân bản hàng loạt → đăng nhiều Fanpage
                    </p>
                </div>
                <div class="page-header-actions">
                    ${(this.projects || []).length ? `
                        <select class="form-input studio-project-select"
                                onchange="StudioPage.loadProject(+this.value)">
                            ${this.projects.map(p => `
                                <option value="${p.id}" ${this.project?.id === p.id ? 'selected' : ''}>
                                    ${this._esc(p.name)}${p.render_count ? ` (${p.render_count} bản)` : ''}
                                </option>
                            `).join('')}
                        </select>
                    ` : ''}
                    <input type="text" class="form-input studio-name-input" id="projectName"
                           value="${this._attr(this.project?.name || 'Dự án mới')}"
                           placeholder="Tên dự án">
                    <button class="btn btn-outline" onclick="StudioPage.saveProject()">Lưu</button>
                    <button class="btn btn-ghost" onclick="StudioPage.newProject()">+ Dự án mới</button>
                </div>
            </div>

            <div class="studio-wrap">
                ${this._renderSourcesStep()}
                ${this._renderTimelineStep()}
                ${this._renderTextStep()}
                ${this._renderAudioStep()}
                ${this._renderComposeStep()}
                ${this._renderBatchStep()}
                ${this._renderPublishStep()}
            </div>
        `;
    },

    init() {
        this._wireUploadZone('videoDropZone', 'video');
        this._wireUploadZone('audioDropZone', 'audio');
    },

    async _loadAll() {
        const [opts, assets, pages, projects] = await Promise.all([
            API.get('/api/studio/options').catch(() => null),
            API.get('/api/studio/assets').catch(() => null),
            API.get('/api/pages?status=active').catch(() => null),
            API.get('/api/studio/projects?limit=30').catch(() => null),
        ]);

        if (opts) this.options = opts;
        if (assets) {
            const all = assets.assets || [];
            this.videoAssets = all.filter(a => a.kind === 'video');
            this.audioAssets = all.filter(a => a.kind === 'audio');
        }
        if (pages) this.pages = pages.pages || [];
        if (projects) this.projects = projects.projects || [];

        // Khôi phục dự án gần nhất khi mới vào trang (hoặc sau khi tải lại trình duyệt).
        // Các bản render nằm trong DB, không chỉ trong bộ nhớ trình duyệt — nhờ vậy
        // đóng tab giữa chừng vẫn quay lại đăng bài được.
        //
        // Không tự nạp khi người dùng vừa bấm "Dự án mới": nếu nạp, dự án cũ sẽ đè
        // lên timeline trống và nút đó coi như vô tác dụng.
        if (!this.project && !this._startedBlank && this.projects?.length) {
            await this.loadProject(this.projects[0].id, { silent: true });
        }
    },

    /** Nạp một dự án đã lưu: timeline, video base và toàn bộ bản đã render. */
    async loadProject(projectId, { silent = false } = {}) {
        try {
            const res = await API.get(`/api/studio/projects/${projectId}`);
            const p = res.project;
            if (!p) return;

            this.project = { id: p.id, name: p.name };
            this._startedBlank = false;
            this.timeline = this._normalizeTimeline(p.timeline);
            this.baseUrl = p.base_url ? `${p.base_url}?t=${Date.now()}` : '';
            this.baseDuration = p.base_duration || 0;
            this.baseStale = !!p.base_stale;

            const rendersRes = await API.get(`/api/studio/renders?project_id=${projectId}`);
            this.renders = rendersRes.renders || [];
            this.selectedRenders = null;   // dự án khác thì chọn hết cho gọn
            this.batchJob = this.renders.length
                ? { job_id: this.renders[this.renders.length - 1].job_id, status: 'completed' }
                : null;

            if (!silent) {
                Toast.success(`Đã mở dự án "${p.name}" — ${this.renders.length} bản đã render`);
                App.refreshPage();
            }
        } catch (e) {
            if (!silent) Toast.error('Không mở được dự án: ' + e.message);
        }
    },

    /** Điền đủ các khoá còn thiếu để timeline cũ vẫn dùng được với bản mới. */
    _normalizeTimeline(tl) {
        const blank = this._blankTimeline();
        if (!tl || typeof tl !== 'object') return blank;
        return {
            canvas: { ...blank.canvas, ...(tl.canvas || {}) },
            segments: tl.segments || [],
            transitions: tl.transitions || [],
            texts: tl.texts || [],
            audio: { ...blank.audio, ...(tl.audio || {}) },
            hook: { ...blank.hook, ...(tl.hook || {}),
                    body: { ...blank.hook.body, ...((tl.hook || {}).body || {}) } },
        };
    },

    newProject() {
        this.reset();
        this._startedBlank = true;   // chặn việc tự nạp lại dự án cũ đè lên
        Toast.info('Đã tạo dự án mới — thêm clip và cảnh để bắt đầu');
        App.refreshPage();
    },

    // ══ Bước 1: Nguồn clip ════════════════════════════════
    _renderSourcesStep() {
        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">1</span> Nguồn clip</h3>
                    <span class="badge">${this.videoAssets.length} clip</span>
                </div>
                <div class="card-body">
                    <div class="studio-drop-zone" id="videoDropZone">
                        <div class="drop-icon">🎬</div>
                        <div class="drop-title">Kéo thả video vào đây</div>
                        <div class="drop-hint">Hoặc bấm để chọn file — MP4, MOV, MKV, AVI, WEBM</div>
                        <input type="file" id="videoFileInput" accept="video/*" multiple hidden>
                    </div>

                    ${this.videoAssets.length ? `
                        <div class="studio-asset-grid">
                            ${this.videoAssets.map(a => `
                                <div class="studio-asset">
                                    <video src="${a.media_url}" preload="metadata" muted
                                           onclick="this.paused ? this.play() : this.pause()"></video>
                                    <div class="studio-asset-info">
                                        <div class="studio-asset-name" title="${this._attr(a.name)}">${this._esc(a.name)}</div>
                                        <div class="studio-asset-meta">
                                            ${this._dur(a.duration)} · ${a.width}×${a.height}
                                            ${a.has_audio ? '' : ' · <span class="muted">không tiếng</span>'}
                                        </div>
                                    </div>
                                    <div class="studio-asset-actions">
                                        <button class="btn btn-xs btn-primary"
                                                onclick="StudioPage.addSegment(${a.id})">+ Thêm cảnh</button>
                                        <button class="btn btn-xs btn-ghost"
                                                onclick="StudioPage.deleteAsset(${a.id})" title="Xoá clip">✕</button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : `<div class="empty-mini"><p>Chưa có clip nào. Tải video A và video B lên để bắt đầu.</p></div>`}
                </div>
            </section>
        `;
    },

    // ══ Bước 2: Timeline ══════════════════════════════════
    _renderTimelineStep() {
        const total = this._totalDuration();

        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">2</span> Cắt cảnh & ghép</h3>
                    <div class="header-actions">
                        <span class="badge ${total > 0 ? 'badge-accent' : ''}"
                              title="${this._attr(this._durationExplain())}">
                            Thành phẩm: ${total.toFixed(1)}s
                        </span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="studio-canvas-row">
                        <div class="form-group inline">
                            <label>Khung hình</label>
                            <select class="form-input form-input-sm" onchange="StudioPage.setCanvas(this.value)">
                                ${(this.options.canvas_presets || []).map(p => `
                                    <option value="${p.id}"
                                        ${this.timeline.canvas.width === p.width && this.timeline.canvas.height === p.height ? 'selected' : ''}>
                                        ${p.name}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="form-group inline">
                            <label>Cách lấp khung</label>
                            <select class="form-input form-input-sm" onchange="StudioPage.setFit(this.value)">
                                <option value="cover" ${this.timeline.canvas.fit === 'cover' ? 'selected' : ''}>Lấp đầy (cắt viền)</option>
                                <option value="contain" ${this.timeline.canvas.fit === 'contain' ? 'selected' : ''}>Vừa khung (viền đen)</option>
                                <option value="blur" ${this.timeline.canvas.fit === 'blur' ? 'selected' : ''}>Nền mờ phía sau</option>
                            </select>
                        </div>
                    </div>

                    ${this._renderBrokenBanner()}

                    ${this.timeline.segments.length
                        ? this.timeline.segments.map((s, i) => this._renderSegment(s, i)).join('')
                        : `<div class="empty-mini"><p>Chưa có cảnh nào. Bấm "+ Thêm cảnh" ở clip phía trên.</p></div>`}
                </div>
            </section>
        `;
    },

    _renderSegment(seg, i) {
        const asset = this.videoAssets.find(a => a.id === seg.asset_id);

        // Clip đã bị xoá khỏi kho: phải hiện ra để người dùng biết mà xử lý.
        // Nếu ẩn đi, cảnh vẫn nằm trong timeline và làm bước ghép thất bại
        // với thông báo khó hiểu về một cảnh không nhìn thấy trên màn hình.
        if (!asset) return this._renderBrokenSegment(seg, i);

        const dur = asset.duration || 0;
        const start = seg.start ?? 0;
        const end = seg.end ?? dur;
        const trans = this.timeline.transitions[i - 1] || { type: 'fade', duration: 0.5 };

        return `
            ${i > 0 ? `
                <div class="studio-transition-row">
                    <span class="transition-connector"></span>
                    <div class="transition-controls">
                        <label>Chuyển cảnh</label>
                        <select class="form-input form-input-sm"
                                onchange="StudioPage.setTransition(${i - 1}, 'type', this.value)">
                            ${(this.options.transitions || []).map(t => `
                                <option value="${t.id}" ${trans.type === t.id ? 'selected' : ''}
                                        title="${this._attr(t.desc)}">${t.name}</option>
                            `).join('')}
                        </select>
                        <label>Dài</label>
                        <input type="number" class="form-input form-input-sm num" min="0.1" max="2.5" step="0.1"
                               value="${trans.duration}"
                               onchange="StudioPage.setTransition(${i - 1}, 'duration', this.value)">
                        <span class="unit">giây</span>
                        ${trans.type !== 'none' ? `
                            <span class="trans-shrink"
                                  title="Hiệu ứng cho hai cảnh chồng lên nhau trong ${trans.duration} giây, nên tổng thời lượng ngắn đi bấy nhiêu">
                                video ngắn đi ${Number(trans.duration).toFixed(1)}s
                            </span>
                        ` : ''}
                    </div>
                    <span class="transition-connector"></span>
                </div>
            ` : ''}

            <div class="studio-segment" data-seg="${i}">
                <div class="segment-preview">
                    <video id="segVideo${i}" src="${asset.media_url}" preload="metadata"
                           playsinline></video>
                </div>

                <div class="segment-body">
                    <div class="segment-head">
                        <span class="segment-index">Cảnh ${i + 1}</span>
                        <span class="segment-source" title="${this._attr(asset.name)}">${this._esc(asset.name)}</span>
                        <span class="segment-length" id="segLen${i}">${(end - start).toFixed(1)}s</span>
                        <div class="segment-head-actions">
                            ${i > 0 ? `<button class="btn btn-xs btn-ghost" onclick="StudioPage.moveSegment(${i}, -1)" title="Lên trước">↑</button>` : ''}
                            ${i < this.timeline.segments.length - 1 ? `<button class="btn btn-xs btn-ghost" onclick="StudioPage.moveSegment(${i}, 1)" title="Xuống sau">↓</button>` : ''}
                            <button class="btn btn-xs btn-ghost danger" onclick="StudioPage.removeSegment(${i})" title="Xoá cảnh">✕</button>
                        </div>
                    </div>

                    <div class="trim-slider">
                        <div class="trim-track">
                            <div class="trim-range" id="trimRange${i}"
                                 style="left:${dur ? (start / dur * 100) : 0}%;
                                        width:${dur ? ((end - start) / dur * 100) : 100}%"></div>
                        </div>
                        <input type="range" class="trim-handle start" min="0" max="${dur}" step="0.05"
                               value="${start}" id="trimStart${i}"
                               oninput="StudioPage.onTrim(${i}, 'start', this.value)">
                        <input type="range" class="trim-handle end" min="0" max="${dur}" step="0.05"
                               value="${end}" id="trimEnd${i}"
                               oninput="StudioPage.onTrim(${i}, 'end', this.value)">
                    </div>

                    <div class="segment-controls">
                        <div class="trim-inputs">
                            <label>Từ giây</label>
                            <input type="number" class="form-input form-input-sm num" min="0" max="${dur}" step="0.1"
                                   value="${start.toFixed(1)}" id="trimStartNum${i}"
                                   onchange="StudioPage.onTrim(${i}, 'start', this.value, true)">
                            <label>đến</label>
                            <input type="number" class="form-input form-input-sm num" min="0" max="${dur}" step="0.1"
                                   value="${end.toFixed(1)}" id="trimEndNum${i}"
                                   onchange="StudioPage.onTrim(${i}, 'end', this.value, true)">
                            <span class="unit">/ ${dur.toFixed(1)}s</span>
                        </div>
                        <div class="segment-buttons">
                            <button class="btn btn-xs btn-outline" onclick="StudioPage.playSegment(${i})">▶ Nghe thử đoạn</button>
                            <button class="btn btn-xs btn-outline" onclick="StudioPage.takeWholeClip(${i})">Lấy toàn bộ clip</button>
                            <label class="seg-reverse ${seg.reverse ? 'on' : ''}"
                                   title="Phát cảnh này từ cuối về đầu">
                                <input type="checkbox" ${seg.reverse ? 'checked' : ''}
                                       onchange="StudioPage.toggleReverse(${i}, this.checked)">
                                ⟲ Đảo ngược
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /** Bật/tắt phát ngược cho một cảnh. */
    toggleReverse(i, on) {
        const seg = this.timeline.segments[i];
        if (!seg) return;
        if (on) seg.reverse = true; else delete seg.reverse;

        const card = document.querySelectorAll('.segment-card')[i];
        const label = card?.querySelector('.seg-reverse');
        if (label) label.classList.toggle('on', !!on);

        this.saveProject(true);
        this._markStale();
    },

    /** Bản ghép ở bước 5 giờ đã cũ — hiện cảnh báo ngay, khỏi đợi tải lại trang. */
    _markStale() {
        if (!this.baseUrl || this.baseStale) return;
        this.baseStale = true;

        const box = document.getElementById('staleWarn');
        if (box) box.innerHTML = this._renderStaleWarning();

        const btn = document.getElementById('composeBtn');
        if (btn) btn.textContent = 'Ghép lại (có thay đổi chưa áp dụng)';
    },

    _renderBrokenBanner() {
        const broken = this._brokenSegments();
        if (!broken.length) return '';

        return `
            <div class="broken-banner">
                <div>
                    <strong>Có ${broken.length} cảnh không ghép được</strong>
                    — cảnh ${broken.map(b => b.i + 1).join(', ')} dùng clip đã bị xoá khỏi kho.
                    Xoá các cảnh này thì mới ghép video được.
                </div>
                <button class="btn btn-sm btn-primary" onclick="StudioPage.removeBrokenSegments()">
                    Xoá ${broken.length} cảnh lỗi
                </button>
            </div>
        `;
    },

    _renderBrokenSegment(seg, i) {
        return `
            ${i > 0 ? '<div class="studio-transition-row"><span class="transition-connector"></span></div>' : ''}
            <div class="studio-segment broken">
                <div class="segment-preview broken-thumb">⚠</div>
                <div class="segment-body">
                    <div class="segment-head">
                        <span class="segment-index">Cảnh ${i + 1}</span>
                        <span class="segment-source">Clip đã bị xoá khỏi kho</span>
                        <div class="segment-head-actions">
                            <button class="btn btn-xs btn-ghost danger"
                                    onclick="StudioPage.removeSegment(${i})" title="Xoá cảnh này">✕</button>
                        </div>
                    </div>
                    <p class="broken-note">
                        Cảnh này dùng một clip không còn trong kho nữa, nên không ghép được.
                        Hãy <strong>xoá cảnh này</strong>, hoặc tải lại clip đó lên rồi thêm cảnh mới.
                    </p>
                </div>
            </div>
        `;
    },

    /** Số cảnh đang trỏ tới clip đã bị xoá. */
    _brokenSegments() {
        return (this.timeline.segments || [])
            .map((s, i) => ({ seg: s, i }))
            .filter(({ seg }) => !this.videoAssets.some(a => a.id === seg.asset_id));
    },

    /** Xoá hết các cảnh lỗi rồi lưu lại dự án. */
    async removeBrokenSegments() {
        const broken = this._brokenSegments();
        if (!broken.length) return;

        // Xoá từ cuối lên để chỉ số các cảnh phía trước không bị lệch
        broken.map(b => b.i).sort((a, b) => b - a).forEach(i => this._spliceSegment(i));

        await this.saveProject(true);
        Toast.success(`Đã xoá ${broken.length} cảnh lỗi. Giờ có thể ghép video.`);
        App.refreshPage();
    },

    // ══ Bước 3: Text on screen ════════════════════════════
    _renderTextStep() {
        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">3</span> Chữ trên màn hình</h3>
                    <button class="btn btn-sm btn-outline" onclick="StudioPage.addText()">+ Thêm dòng chữ</button>
                </div>
                <div class="card-body">
                    ${this.timeline.texts.length ? this.timeline.texts.map((t, i) => `
                        <div class="studio-text-row">
                            <div class="text-row-main">
                                <input type="text" class="form-input" placeholder="Nội dung chữ hiển thị..."
                                       value="${this._attr(t.text)}"
                                       oninput="StudioPage.setText(${i}, 'text', this.value)">
                            </div>
                            <div class="text-row-opts">
                                <div class="form-group inline">
                                    <label>Vị trí</label>
                                    <select class="form-input form-input-sm" onchange="StudioPage.setText(${i}, 'position', this.value)">
                                        <option value="top" ${t.position === 'top' ? 'selected' : ''}>Trên</option>
                                        <option value="center" ${t.position === 'center' ? 'selected' : ''}>Giữa</option>
                                        <option value="bottom" ${t.position === 'bottom' ? 'selected' : ''}>Dưới</option>
                                    </select>
                                </div>
                                <div class="form-group inline">
                                    <label>Cỡ chữ</label>
                                    <input type="number" class="form-input form-input-sm num" min="16" max="200" step="2"
                                           value="${t.size}" onchange="StudioPage.setText(${i}, 'size', this.value)">
                                </div>
                                <div class="form-group inline">
                                    <label>Kiểu</label>
                                    <select class="form-input form-input-sm" onchange="StudioPage.setText(${i}, 'style', this.value)">
                                        <option value="shadow" ${t.style === 'shadow' ? 'selected' : ''}>Đổ bóng</option>
                                        <option value="outline" ${t.style === 'outline' ? 'selected' : ''}>Viền đen</option>
                                        <option value="box" ${t.style === 'box' ? 'selected' : ''}>Nền khối</option>
                                    </select>
                                </div>
                                <div class="form-group inline">
                                    <label>Màu</label>
                                    <input type="color" class="form-input form-input-sm color"
                                           value="${t.color}" onchange="StudioPage.setText(${i}, 'color', this.value)">
                                </div>
                                <div class="form-group inline">
                                    <label>Hiện từ</label>
                                    <input type="number" class="form-input form-input-sm num" min="0" step="0.5"
                                           value="${t.start}" onchange="StudioPage.setText(${i}, 'start', this.value)">
                                    <label>đến</label>
                                    <input type="number" class="form-input form-input-sm num" min="0" step="0.5"
                                           value="${t.end}" onchange="StudioPage.setText(${i}, 'end', this.value)">
                                    <span class="unit">giây</span>
                                </div>
                                <button class="btn btn-xs btn-ghost danger" onclick="StudioPage.removeText(${i})">✕</button>
                            </div>
                        </div>
                    `).join('') : `<div class="empty-mini"><p>Chưa có chữ nào. Chữ dài sẽ tự xuống dòng cho vừa khung hình.</p></div>`}
                    <p class="form-hint">Hỗ trợ tiếng Việt có dấu. Emoji có thể không hiển thị do hạn chế của font hệ thống.</p>
                </div>
            </section>
        `;
    },

    // ══ Bước 4: Nhạc nền ══════════════════════════════════
    _renderAudioStep() {
        const audio = this.timeline.audio;
        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">4</span> Âm thanh</h3>
                    <span class="badge">${this.audioAssets.length} bài nhạc</span>
                </div>
                <div class="card-body">
                    <div class="audio-mode-row">
                        ${[
                            ['original', 'Giữ tiếng gốc'],
                            ['music', 'Thay bằng nhạc nền'],
                            ['mix', 'Trộn tiếng gốc + nhạc'],
                            ['mute', 'Tắt tiếng'],
                        ].map(([val, label]) => `
                            <label class="radio-chip ${audio.mode === val ? 'active' : ''}">
                                <input type="radio" name="audioMode" value="${val}"
                                       ${audio.mode === val ? 'checked' : ''}
                                       onchange="StudioPage.setAudioMode('${val}')">
                                ${label}
                            </label>
                        `).join('')}
                    </div>

                    ${this._renderAudioTune()}

                    <div class="studio-drop-zone compact" id="audioDropZone">
                        <div class="drop-title">Kéo thả file nhạc vào đây</div>
                        <div class="drop-hint">MP3, M4A, WAV — dùng làm nhạc nền và để đổi nhạc từng biến thể</div>
                        <input type="file" id="audioFileInput" accept="audio/*" multiple hidden>
                    </div>

                    ${this.audioAssets.length ? `
                        <div class="audio-list">
                            ${this.audioAssets.map(a => `
                                <div class="audio-item ${audio.asset_id === a.id ? 'selected' : ''}">
                                    <button class="audio-pick" onclick="StudioPage.pickMusic(${a.id})"
                                            title="Dùng làm nhạc nền cho bản ghép">
                                        ${audio.asset_id === a.id ? '●' : '○'}
                                    </button>
                                    <div class="audio-meta">
                                        <div class="audio-name">${this._esc(a.name)}</div>
                                        <div class="audio-dur">${this._dur(a.duration)}</div>
                                    </div>
                                    <audio src="${a.media_url}" controls preload="none"></audio>
                                    <button class="btn btn-xs btn-ghost" onclick="StudioPage.deleteAsset(${a.id})">✕</button>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </section>
        `;
    },

    /** Bảng tinh chỉnh tiếng gốc — chỉ có ý nghĩa khi tiếng gốc còn được dùng. */
    _renderAudioTune() {
        const mode = this.timeline.audio.mode;
        if (mode === 'music' || mode === 'mute') return '';

        const tune = this.timeline.audio.tune || { preset: 'medium' };
        const presets = this.options.audio_tune_presets || [];
        const active = presets.find(p => p.id === tune.preset);
        const isCustom = tune.preset === 'custom';
        const vals = isCustom ? tune : (active || { pitch: 0, bass: 0, treble: 0 });

        return `
            <div class="audio-tune">
                <div class="audio-tune-head">
                    <div>
                        <strong>Tinh chỉnh tiếng gốc</strong>
                        <div class="form-hint" style="margin-top:2px">
                            Đổi cao độ và âm sắc để tiếng không còn khớp với bản gốc.
                            Mỗi biến thể sẽ được lệch thêm một chút khác nhau.
                        </div>
                    </div>
                </div>

                <div class="tune-preset-row">
                    ${presets.map(p => `
                        <label class="radio-chip ${tune.preset === p.id ? 'active' : ''}" title="${this._attr(p.desc)}">
                            <input type="radio" name="tunePreset" ${tune.preset === p.id ? 'checked' : ''}
                                   onchange="StudioPage.setTunePreset('${p.id}')">
                            ${p.name}
                        </label>
                    `).join('')}
                    <label class="radio-chip ${isCustom ? 'active' : ''}">
                        <input type="radio" name="tunePreset" ${isCustom ? 'checked' : ''}
                               onchange="StudioPage.setTunePreset('custom')">
                        Tuỳ chỉnh
                    </label>
                </div>

                ${active ? `<p class="tune-desc">${this._esc(active.desc)}</p>` : ''}

                ${isCustom ? `
                    <div class="tune-sliders">
                        ${this._tuneSlider('pitch', 'Cao độ giọng', vals.pitch, -8, 8, 0.5, '%')}
                        ${this._tuneSlider('bass', 'Âm trầm', vals.bass, -8, 8, 0.5, 'dB')}
                        ${this._tuneSlider('treble', 'Âm cao', vals.treble, -8, 8, 0.5, 'dB')}
                    </div>
                ` : `
                    <div class="tune-values">
                        <span>Cao độ <b>${vals.pitch > 0 ? '+' : ''}${vals.pitch}%</b></span>
                        <span>Âm trầm <b>${vals.bass > 0 ? '+' : ''}${vals.bass} dB</b></span>
                        <span>Âm cao <b>${vals.treble > 0 ? '+' : ''}${vals.treble} dB</b></span>
                    </div>
                `}

                <div class="tune-preview">
                    <button class="btn btn-sm btn-outline" onclick="StudioPage.previewAudio(true)">
                        ▶ Nghe tiếng gốc
                    </button>
                    <button class="btn btn-sm btn-accent" onclick="StudioPage.previewAudio(false)">
                        ▶ Nghe sau khi chỉnh
                    </button>
                    <span class="tune-preview-status" id="tunePreviewStatus"></span>
                </div>
                <audio id="tunePreviewPlayer" controls class="tune-player" style="display:none"></audio>
            </div>
        `;
    },

    _tuneSlider(field, label, value, min, max, step, unit) {
        return `
            <div class="tune-slider">
                <label>${label}</label>
                <input type="range" min="${min}" max="${max}" step="${step}" value="${value}"
                       oninput="StudioPage.setTuneValue('${field}', this.value)">
                <span class="tune-slider-val" id="tuneVal_${field}">
                    ${value > 0 ? '+' : ''}${value}${unit}
                </span>
            </div>
        `;
    },

    setTunePreset(presetId) {
        const tune = this.timeline.audio.tune || {};
        if (presetId === 'custom') {
            // Chuyển sang tuỳ chỉnh thì lấy giá trị của mức đang chọn làm điểm bắt đầu
            const current = (this.options.audio_tune_presets || [])
                .find(p => p.id === tune.preset);
            this.timeline.audio.tune = {
                preset: 'custom',
                pitch: current?.pitch ?? tune.pitch ?? 0,
                bass: current?.bass ?? tune.bass ?? 0,
                treble: current?.treble ?? tune.treble ?? 0,
            };
        } else {
            this.timeline.audio.tune = { preset: presetId };
        }
        App.refreshPage();
    },

    setTuneValue(field, value) {
        const tune = this.timeline.audio.tune;
        tune[field] = Number(value);
        const unit = field === 'pitch' ? '%' : 'dB';
        const el = document.getElementById(`tuneVal_${field}`);
        if (el) el.textContent = `${tune[field] > 0 ? '+' : ''}${tune[field]}${unit}`;
    },

    /** Nghe thử tiếng của cảnh đầu tiên, trước và sau khi chỉnh. */
    async previewAudio(raw) {
        const seg = this.timeline.segments[0];
        if (!seg) {
            Toast.error('Thêm ít nhất một cảnh ở bước 2 trước đã');
            return;
        }
        const asset = this.videoAssets.find(a => a.id === seg.asset_id);
        if (!asset) {
            Toast.error('Không tìm thấy clip của cảnh đầu tiên');
            return;
        }
        if (!asset.has_audio) {
            Toast.error(`Clip "${asset.name}" không có tiếng`);
            return;
        }

        const status = document.getElementById('tunePreviewStatus');
        if (status) status.textContent = 'Đang xử lý...';

        try {
            const res = await fetch('/api/studio/audio-preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    asset_id: asset.id,
                    start: seg.start || 0,
                    duration: Math.min(12, Math.max(3, (seg.end ?? 10) - (seg.start ?? 0))),
                    tune: this.timeline.audio.tune || { preset: 'none' },
                    raw: !!raw,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Không tạo được bản nghe thử');
            }

            const blob = await res.blob();
            const player = document.getElementById('tunePreviewPlayer');
            if (player) {
                if (player.src) URL.revokeObjectURL(player.src);
                player.src = URL.createObjectURL(blob);
                player.style.display = 'block';
                player.play();
            }
            if (status) status.textContent = raw ? 'Đang phát: tiếng gốc' : 'Đang phát: sau khi chỉnh';
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (status) status.textContent = '';
        }
    },

    // ══ Bước 5: Ghép & xem trước ══════════════════════════
    _renderComposeStep() {
        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">5</span> Ghép & xem trước</h3>
                </div>
                <div class="card-body">
                    <div id="staleWarn">${this._renderStaleWarning()}</div>

                    <div class="compose-row">
                        <button class="btn btn-primary btn-lg" onclick="StudioPage.compose()" id="composeBtn">
                            ${this.baseStale ? 'Ghép lại (có thay đổi chưa áp dụng)' : 'Ghép video & Xem trước'}
                        </button>
                        <div class="compose-status" id="composeStatus">
                            ${this.baseUrl
                                ? `<span class="status-ok">Đã ghép xong — ${this.baseDuration.toFixed(1)}s</span>`
                                : '<span class="muted">Ghép các cảnh thành một video hoàn chỉnh trước khi nhân bản.</span>'}
                        </div>
                    </div>

                    <div class="compose-preview" id="composePreview">
                        ${this.baseUrl ? `
                            <video src="${this.baseUrl}" controls preload="metadata" class="base-video"></video>
                        ` : ''}
                    </div>
                </div>
            </section>
        `;
    },

    /** Cảnh báo khi đã sửa timeline nhưng chưa ghép lại. */
    _renderStaleWarning() {
        if (!this.baseStale || !this.baseUrl) return '';
        return `
            <div class="stale-warning">
                <div>
                    <strong>Bản ghép hiện tại đã cũ.</strong>
                    Anh/chị đã thay đổi gì đó ở bước 2–4 (đổi nhạc, thêm cảnh, sửa chữ...)
                    sau lần ghép gần nhất.
                    <br>
                    <strong>Phải bấm "Ghép lại" trước khi nhân bản</strong> — nếu không, các biến thể
                    sẽ mang tiếng và hình của bản ghép cũ.
                </div>
            </div>
        `;
    },

    /** Tên bài nhạc đang dùng cho bản ghép (nhạc chọn ở bước 4). */
    _baseMusicName() {
        const a = this.timeline.audio;
        if (a.mode === 'mute') return null;
        if (a.mode !== 'music' && a.mode !== 'mix') return null;
        const asset = this.audioAssets.find(x => x.id === a.asset_id);
        return asset ? asset.name : null;
    },

    // ══ Ghép ngẫu nhiên ═══════════════════════════════════
    //
    // Một clip dài chứa rất nhiều đoạn dùng được. Mỗi bản render lấy một đoạn
    // khác nhau: cảnh mở đầu lấy trong clip A, phần thân lấy trong clip B.

    _hookCfg() {
        const h = this.timeline.hook || {};
        return { ...h, body: h.body || {} };
    },

    _renderHookBox() {
        const h = this._hookCfg();
        const on = !!h.enabled;
        const clips = this.videoAssets;
        const src = clips.find(a => a.id === h.asset_id);
        const segs = this.timeline.segments || [];

        const b = h.body;
        const bodySrc = clips.find(a => a.id === b.asset_id)
            || clips.find(a => a.id === segs[Math.min(h.scenes || 1, segs.length - 1)]?.asset_id);

        return `
            <div class="batch-section hook-box ${on ? 'on' : ''}">
                <label class="hook-toggle">
                    <input type="checkbox" ${on ? 'checked' : ''}
                           onchange="StudioPage.setHook('enabled', this.checked)">
                    <span>
                        <strong>Ghép ngẫu nhiên</strong> — mỗi bản một đoạn khác nhau
                        <small>Cắt ngẫu nhiên trong clip nguồn để mỗi bản render ra một video khác hẳn.
                        Một video ra được hàng chục bản không trùng nhau.</small>
                    </span>
                </label>

                ${!on ? '' : `
                    <div class="hook-part">
                        <div class="hook-part-title">Cảnh mở đầu (hook)</div>
                        <div class="hook-fields">
                            <div class="form-group inline">
                                <label>Lấy từ clip</label>
                                <select class="form-input form-input-sm"
                                        onchange="StudioPage.setHook('asset_id', +this.value || null)">
                                    <option value="">— chọn clip —</option>
                                    ${clips.map(a => `
                                        <option value="${a.id}" ${a.id === h.asset_id ? 'selected' : ''}>
                                            ${this._esc(a.name)} (${(a.duration || 0).toFixed(1)}s)
                                        </option>
                                    `).join('')}
                                </select>
                            </div>
                            <div class="form-group inline">
                                <label>Thay mấy cảnh đầu</label>
                                <select class="form-input form-input-sm num"
                                        onchange="StudioPage.setHook('scenes', +this.value)">
                                    ${[1, 2].map(n => `
                                        <option value="${n}" ${n === (h.scenes || 1) ? 'selected' : ''}>${n} cảnh</option>
                                    `).join('')}
                                </select>
                            </div>
                            <div class="form-group inline">
                                <label>Độ dài mỗi cảnh</label>
                                <input type="number" class="form-input form-input-sm num" min="1" max="60" step="0.5"
                                       value="${h.min_len ?? 5}"
                                       onchange="StudioPage.setHook('min_len', +this.value)">
                                <span class="unit">đến</span>
                                <input type="number" class="form-input form-input-sm num" min="1" max="60" step="0.5"
                                       value="${h.max_len ?? 10}"
                                       onchange="StudioPage.setHook('max_len', +this.value)">
                                <span class="unit">giây</span>
                            </div>
                        </div>
                    </div>

                    <div class="hook-part ${b.enabled ? 'on' : ''}">
                        <label class="hook-part-toggle">
                            <input type="checkbox" ${b.enabled ? 'checked' : ''}
                                   onchange="StudioPage.setBody('enabled', this.checked)">
                            <span>
                                <strong>Phần thân cũng cắt ngẫu nhiên</strong>
                                <small>Không tích thì phần thân giữ nguyên như ở bước 2, chỉ đổi mở đầu.</small>
                            </span>
                        </label>

                        ${!b.enabled ? '' : `
                            <div class="hook-fields">
                                <div class="form-group inline">
                                    <label>Lấy từ clip</label>
                                    <select class="form-input form-input-sm"
                                            onchange="StudioPage.setBody('asset_id', +this.value || null)">
                                        <option value="">— dùng clip của cảnh thân —</option>
                                        ${clips.map(a => `
                                            <option value="${a.id}" ${a.id === b.asset_id ? 'selected' : ''}>
                                                ${this._esc(a.name)} (${(a.duration || 0).toFixed(1)}s)
                                            </option>
                                        `).join('')}
                                    </select>
                                </div>
                                <div class="form-group inline">
                                    <label>Lấy bao nhiêu giây</label>
                                    <input type="number" class="form-input form-input-sm num" min="1" max="300" step="0.5"
                                           value="${b.min_len ?? 10}"
                                           onchange="StudioPage.setBody('min_len', +this.value)">
                                    <span class="unit">đến</span>
                                    <input type="number" class="form-input form-input-sm num" min="1" max="300" step="0.5"
                                           value="${b.max_len ?? 15}"
                                           onchange="StudioPage.setBody('max_len', +this.value)">
                                    <span class="unit">giây</span>
                                </div>
                            </div>
                        `}
                    </div>

                    <p class="hook-note">${this._hookNote(h, src, bodySrc, segs.length)}</p>

                    <div class="hook-actions">
                        <button class="btn btn-sm btn-primary" onclick="StudioPage.loadHookPlan()">
                            Xem trước ${this.batchCount} bản sẽ ghép
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="StudioPage.reshuffleHook()"
                                title="Bốc lại toàn bộ các đoạn ngẫu nhiên">
                            🎲 Trộn lại
                        </button>
                    </div>

                    <div id="hookPlan">${this._renderHookPlan()}</div>
                `}
            </div>
        `;
    },

    /** Câu ngay dưới ô cấu hình — nói rõ sắp render ra cái gì. */
    _hookNote(h, src, bodySrc, segCount) {
        if (!src) return '⚠️ Chưa chọn clip cho cảnh mở đầu. Bật mà chưa chọn thì lúc render sẽ bỏ qua.';

        const scenes = h.scenes || 1;
        const min = h.min_len ?? 5;
        const max = h.max_len ?? 10;
        if (min > max) return '⚠️ Độ dài tối thiểu của cảnh đầu đang lớn hơn tối đa — sửa lại hai ô đó.';
        if ((src.duration || 0) < scenes * min) {
            return `⚠️ Clip "${this._esc(src.name)}" chỉ dài ${(src.duration || 0).toFixed(1)}s,
                    không cắt đủ ${scenes} cảnh mỗi cảnh ${min}s.
                    Chọn clip dài hơn hoặc giảm độ dài cảnh đầu.`;
        }

        const b = h.body || {};
        if (b.enabled) {
            if (!bodySrc) return '⚠️ Chưa chọn được clip cho phần thân.';
            if ((b.min_len ?? 10) > (b.max_len ?? 15)) {
                return '⚠️ Độ dài tối thiểu của phần thân đang lớn hơn tối đa — sửa lại hai ô đó.';
            }
            if ((bodySrc.duration || 0) < (b.min_len ?? 10)) {
                return `⚠️ Clip thân "${this._esc(bodySrc.name)}" chỉ dài ${(bodySrc.duration || 0).toFixed(1)}s,
                        không cắt được đoạn ${b.min_len ?? 10}s.
                        Giảm độ dài phần thân hoặc chọn clip dài hơn.`;
            }
        }

        const replaced = Math.max(0, Math.min(scenes, segCount - 1));
        const dau = replaced
            ? `thay <strong>${replaced} cảnh đầu</strong>`
            : `<strong>chèn thêm vào đầu</strong> (timeline chỉ có 1 cảnh nên không xoá cảnh nào)`;
        const than = b.enabled
            ? `phần thân lấy <strong>${b.min_len ?? 10}–${b.max_len ?? 15}s</strong> ngẫu nhiên
               trong "${this._esc(bodySrc.name)}"`
            : `phần thân <strong>giữ nguyên</strong> như ở bước 2`;

        return `Mỗi bản sẽ ${dau} bằng ${scenes} đoạn ${min}–${max}s lấy ngẫu nhiên trong
                "${this._esc(src.name)}", còn ${than}.
                Các đoạn trải đều khắp clip nên các bản không lấy trùng chỗ.
                <br>⏱ Mỗi bản phải ghép lại từ đầu nên render lâu hơn bình thường.`;
    },

    /** Bảng xem trước: bản nào lấy đoạn nào. */
    _renderHookPlan() {
        if (this.hookPlanError) {
            return `<div class="hook-plan-error">${this._esc(this.hookPlanError)}</div>`;
        }
        if (!this.hookPlan || !this.hookPlan.length) return '';

        return `
            <div class="hook-plan">
                <div class="hook-plan-head">
                    ${this.hookPlan.length} bản sẽ ghép — bấm <strong>Ghép thử</strong> để xem thật một bản
                </div>
                ${this.hookPlan.map(v => this._renderPlanRow(v)).join('')}
                ${this.hookPreview ? `
                    <div class="hook-preview">
                        <div class="hook-preview-title">Bản thử #${this.hookPreview.idx}
                            — ${this.hookPreview.duration.toFixed(1)}s</div>
                        <video src="${this.hookPreview.url}" controls playsinline
                               class="hook-preview-video"></video>
                    </div>
                ` : ''}
            </div>
        `;
    },

    _renderPlanRow(v) {
        const busy = this.hookPreviewBusy === v.idx;
        return `
            <div class="plan-row ${this.hookPreview?.idx === v.idx ? 'active' : ''}">
                <div class="plan-idx">#${v.idx}</div>
                <div class="plan-segs">
                    ${v.segments.map(sg => this._renderPlanSeg(sg)).join('')}
                </div>
                <div class="plan-dur">${v.duration.toFixed(1)}s</div>
                <button class="btn btn-xs btn-outline" ${busy ? 'disabled' : ''}
                        onclick="StudioPage.previewHookVariant(${v.idx})">
                    ${busy ? 'Đang ghép...' : 'Ghép thử'}
                </button>
            </div>
        `;
    },

    /** Một đoạn: thanh biểu thị vị trí lấy trong clip gốc. */
    _renderPlanSeg(sg) {
        const total = sg.source_duration || 1;
        const left = Math.max(0, Math.min(100, (sg.start / total) * 100));
        const width = Math.max(1.5, Math.min(100 - left, (sg.length / total) * 100));
        const nhan = { hook: 'mở đầu', than: 'thân', codinh: 'cố định' }[sg.role] || '';

        return `
            <div class="plan-seg role-${sg.role}">
                <div class="plan-seg-top">
                    <span class="plan-seg-tag">${nhan}</span>
                    <span class="plan-seg-name">${this._esc(sg.name)}</span>
                    ${sg.reverse ? '<span class="plan-seg-rev">⟲ đảo</span>' : ''}
                </div>
                <div class="plan-bar" title="Clip dài ${total.toFixed(1)}s">
                    <div class="plan-bar-fill" style="left:${left}%;width:${width}%"></div>
                </div>
                <div class="plan-seg-time">${sg.start.toFixed(1)}s → ${sg.end.toFixed(1)}s
                    <span class="muted">(${sg.length.toFixed(1)}s)</span></div>
            </div>
        `;
    },

    setHook(key, value) {
        this.timeline.hook = { ...(this.timeline.hook || {}), [key]: value };

        const h = this.timeline.hook;
        // Bật lần đầu mà chưa chọn clip thì lấy sẵn clip của cảnh 1 cho đỡ thao tác
        if (key === 'enabled' && value && !h.asset_id) {
            h.asset_id = (this.timeline.segments || [])[0]?.asset_id
                || this.videoAssets[0]?.id || null;
        }
        if (!h.seed) h.seed = Math.floor(Math.random() * 1e9);

        this._afterHookChange();
    },

    setBody(key, value) {
        const h = this.timeline.hook || {};
        this.timeline.hook = { ...h, body: { ...(h.body || {}), [key]: value } };
        this._afterHookChange();
    },

    /** Bốc lại toàn bộ các đoạn ngẫu nhiên. */
    reshuffleHook() {
        this.timeline.hook = {
            ...(this.timeline.hook || {}),
            seed: Math.floor(Math.random() * 1e9),
        };
        this.hookPreview = null;
        this._afterHookChange();
        if (this.hookPlan) this.loadHookPlan();
    },

    _afterHookChange() {
        // Đổi cấu hình thì bảng xem trước cũ không còn đúng nữa
        this.hookPlan = null;
        this.hookPlanError = '';
        this.saveProject(true);
        this._repaintHookBox();
    },

    async loadHookPlan() {
        if (!this.project?.id) { Toast.error('Chưa có dự án.'); return; }
        this.hookPlanError = '';
        try {
            const res = await API.post(
                `/api/studio/projects/${this.project.id}/hook-plan`,
                { timeline: this.timeline, count: this.batchCount });
            if (res.status !== 'ok') {
                this.hookPlan = null;
                this.hookPlanError = res.error || 'Không xem trước được.';
            } else {
                this.hookPlan = res.variants || [];
            }
        } catch (e) {
            this.hookPlan = null;
            this.hookPlanError = e?.message || String(e);
        }
        this._repaintHookPlan();
    },

    async previewHookVariant(idx) {
        if (!this.project?.id) return;
        this.hookPreviewBusy = idx;
        this._repaintHookPlan();

        try {
            const res = await API.post(
                `/api/studio/projects/${this.project.id}/hook-preview`,
                { timeline: this.timeline, idx, count: this.batchCount });
            if (res.status !== 'ok') {
                Toast.error(res.error || 'Ghép thử thất bại');
            } else {
                this.hookPreview = { idx: res.idx, url: res.url, duration: res.duration };
            }
        } catch (e) {
            Toast.error('Ghép thử lỗi: ' + (e?.message || e));
        }

        this.hookPreviewBusy = 0;
        this._repaintHookPlan();
    },

    /** Vẽ lại riêng bảng xem trước — không đụng phần còn lại của trang. */
    _repaintHookPlan() {
        const box = document.getElementById('hookPlan');
        if (box) box.innerHTML = this._renderHookPlan();
    },

    /** Vẽ lại riêng khối ghép ngẫu nhiên — cho khỏi nhảy màn hình. */
    _repaintHookBox() {
        const box = document.querySelector('.hook-box');
        if (!box) { App.refreshPage({ keepState: true }); return; }
        box.outerHTML = this._renderHookBox();
    },

    // ══ Bước 6: Render hàng loạt ══════════════════════════
    _renderBatchStep() {
        const looks = this.options.looks || [];
        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">6</span> Nhân bản hàng loạt</h3>
                    <span class="badge">${this.renders.length} bản đã render</span>
                </div>
                <div class="card-body">
                    <div class="batch-config">
                        <div class="form-group inline">
                            <label>Số bản cần tạo</label>
                            <input type="number" class="form-input form-input-sm num" min="1" max="200"
                                   value="${this.batchCount}" id="batchCount"
                                   onchange="StudioPage.batchCount = Math.max(1, Math.min(200, +this.value || 1))">
                            <span class="unit">bản (tối đa 200)</span>
                        </div>
                    </div>

                    ${this._renderHookBox()}

                    <div class="batch-section">
                        <div class="batch-section-title">Bộ màu áp cho các bản — mỗi bản một kiểu, xoay vòng</div>
                        <div class="look-grid">
                            ${looks.map(l => `
                                <label class="look-chip ${this.selectedLooks.includes(l.id) ? 'active' : ''}">
                                    <input type="checkbox" value="${l.id}"
                                           ${this.selectedLooks.includes(l.id) ? 'checked' : ''}
                                           onchange="StudioPage.toggleLook('${l.id}', this.checked)">
                                    ${l.name}
                                </label>
                            `).join('')}
                        </div>
                    </div>

                    <div class="batch-section">
                        <div class="batch-section-title">
                            Nhạc cho các bản
                        </div>
                        <p class="form-hint" style="margin-bottom:10px">
                            ${this._baseMusicName()
                                ? `Mặc định <strong>tất cả các bản dùng nhạc "${this._esc(this._baseMusicName())}"</strong>
                                   đã chọn ở bước 4. Chỉ tick thêm bên dưới nếu muốn <strong>mỗi bản một bài khác nhau</strong>.`
                                : `Bước 4 đang <strong>giữ tiếng gốc của video</strong>. Tick nhạc bên dưới nếu
                                   muốn các bản dùng nhạc nền thay cho tiếng gốc.`}
                        </p>
                        ${this.audioAssets.length ? `
                            <div class="look-grid">
                                ${this.audioAssets.map(a => `
                                    <label class="look-chip ${this.selectedMusic.includes(a.id) ? 'active' : ''}">
                                        <input type="checkbox" value="${a.id}"
                                               ${this.selectedMusic.includes(a.id) ? 'checked' : ''}
                                               onchange="StudioPage.toggleMusic(${a.id}, this.checked)">
                                        ${this._esc(a.name)}
                                    </label>
                                `).join('')}
                            </div>
                        ` : `<p class="muted">Chưa có nhạc. Không chọn thì các bản giữ nguyên tiếng của video ghép.</p>`}
                    </div>

                    <div class="batch-actions">
                        <button class="btn btn-primary btn-lg" onclick="StudioPage.startBatch()" id="batchBtn"
                                ${this.baseUrl ? '' : 'disabled title="Ghép video ở bước 5 trước"'}>
                            Render ${this.batchCount} biến thể
                        </button>
                        <div class="batch-progress" id="batchProgress"></div>
                    </div>

                    <div id="exportPanel">${this._renderExportPanel()}</div>

                    <div class="render-grid" id="renderGrid">${this._renderRenderCards()}</div>
                </div>
            </section>
        `;
    },

    _renderExportPanel() {
        if (!this.renders.length) return '';

        const totalMb = this.renders.reduce((s, r) => s + (r.filesize || 0), 0) / 1048576;
        return `
            <div class="export-panel">
                <div class="export-info">
                    <strong>${this.renders.length} biến thể</strong> · ${totalMb.toFixed(0)} MB
                    ${this.lastExportPath ? `
                        <div class="export-last">
                            Đã xuất vào: <span class="mono">${this._esc(this.lastExportPath)}</span>
                            <button class="btn btn-xs btn-ghost"
                                    onclick="StudioPage.openExportFolder()">Mở thư mục</button>
                        </div>
                    ` : ''}
                </div>
                <div class="export-buttons">
                    <button class="btn btn-primary" onclick="StudioPage.showExportPicker()">
                        Xuất ra thư mục trên máy
                    </button>
                    <button class="btn btn-outline" onclick="StudioPage.downloadZip()" id="zipBtn">
                        Tải tất cả (.zip)
                    </button>
                </div>
            </div>
        `;
    },

    _renderRenderCards() {
        if (!this.renders.length) return '';
        // Đánh số theo vị trí trong danh sách, không dùng r.idx — mỗi lượt render
        // đều đếm lại từ 1 nên dự án render nhiều lượt sẽ hiện #001 lặp lại.
        return this.renders.map((r, i) => `
            <div class="render-card">
                <div class="render-thumb">
                    <video src="${r.media_url}" preload="metadata" muted
                           onclick="this.paused ? this.play() : this.pause()"></video>
                    ${r.id ? `
                        <a class="render-download" title="Tải bản này về máy"
                           href="/api/studio/renders/${r.id}/download">⤓</a>
                    ` : ''}
                </div>
                <div class="render-info">
                    <span class="render-idx">#${String(i + 1).padStart(3, '0')}</span>
                    <span class="render-look">${this._esc(r.recipe?.look_name || '')}</span>
                    ${this._renderMusicTag(r)}
                </div>
            </div>
        `).join('');
    },

    /** Nhãn nhạc trên thẻ biến thể.
     *
     * Bản không chọn nhạc riêng ở bước 6 vẫn dùng nhạc của bản ghép — trước đây
     * không hiện gì nên người dùng tưởng bản đó bị mất nhạc.
     */
    _renderMusicTag(r) {
        const own = r.recipe?.music?.name;
        if (own) {
            return `<span class="render-music" title="Nhạc riêng: ${this._attr(own)}">
                        ♪ ${this._esc(this._trunc(own, 14))}
                    </span>`;
        }
        const base = this._baseMusicName();
        if (base) {
            return `<span class="render-music muted" title="Dùng nhạc nền của bản ghép: ${this._attr(base)}">
                        ♪ ${this._esc(this._trunc(base, 14))}
                    </span>`;
        }
        return `<span class="render-music muted" title="Giữ tiếng gốc của video">tiếng gốc</span>`;
    },

    // ══ Bước 7: Đăng lên Fanpage ══════════════════════════
    _renderPublishStep() {
        return `
            <section class="card studio-step">
                <div class="card-header">
                    <h3 class="card-title"><span class="step-num">7</span> Đăng lên Fanpage</h3>
                    <span class="badge">${this.pages.length} page</span>
                </div>
                <div class="card-body">
                    ${!this.renders.length ? `
                        <div class="empty-mini"><p>Render biến thể ở bước 6 trước, rồi chọn Fanpage để đăng.</p></div>
                    ` : `
                        ${this._renderPickVariants()}

                        <p class="form-hint">
                            Mỗi Fanpage nhận một biến thể <strong>khác nhau</strong>, xoay vòng qua
                            <strong id="rotateCount">${this._activeRenders().length} bản đã chọn</strong>
                            — tránh đăng trùng giữa các page.
                        </p>

                        <div class="form-group">
                            <label>Caption</label>
                            <textarea class="form-input" id="publishCaption" rows="3"
                                      placeholder="Nội dung bài đăng..."></textarea>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label>Bình luận đầu tiên (tuỳ chọn)</label>
                                <input type="text" class="form-input" id="publishFirstComment"
                                       placeholder="Ví dụ: Inbox để đặt hàng nhé">
                            </div>
                            <div class="form-group">
                                <label>Link ảnh kèm bình luận (tuỳ chọn)</label>
                                <input type="text" class="form-input" id="publishCommentImage"
                                       placeholder="https://...">
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label>Hẹn giờ bài đầu tiên (để trống = đăng ngay)</label>
                                <input type="datetime-local" class="form-input" id="publishSchedule">
                            </div>
                            <div class="form-group">
                                <label>Giãn cách giữa các page</label>
                                <input type="number" class="form-input" id="publishInterval"
                                       min="0" max="1440" value="15">
                                <small class="form-hint">Phút. Chỉ áp dụng khi có hẹn giờ.</small>
                            </div>
                        </div>

                        <div class="page-pick-head">
                            <span>Chọn Fanpage</span>
                            <div>
                                <button class="btn btn-xs btn-outline" onclick="StudioPage.pickAllPages(true)">Chọn tất cả</button>
                                <button class="btn btn-xs btn-outline" onclick="StudioPage.pickAllPages(false)">Bỏ chọn</button>
                            </div>
                        </div>

                        <div class="page-pick-grid">
                            ${this.pages.length ? this.pages.map(p => `
                                <label class="page-pick">
                                    <input type="checkbox" class="page-check" value="${p.id}">
                                    <div class="page-pick-avatar">
                                        ${p.avatar_url ? `<img src="${this._attr(p.avatar_url)}" alt="" referrerpolicy="no-referrer">` : '📄'}
                                    </div>
                                    <div class="page-pick-info">
                                        <div class="page-pick-name">${this._esc(p.page_name)}</div>
                                        <div class="page-pick-meta">${this._num(p.followers_count)} follow</div>
                                    </div>
                                </label>
                            `).join('') : '<p class="muted">Chưa kết nối Fanpage nào. Vào mục Tài Khoản để thêm.</p>'}
                        </div>

                        <div class="publish-actions">
                            <button class="btn btn-primary btn-lg" onclick="StudioPage.distribute()" id="distributeBtn">
                                Đăng lên các Fanpage đã chọn
                            </button>
                        </div>

                        <div id="distributeResult"></div>
                    `}
                </div>
            </section>
        `;
    },

    /** Các biến thể đang được chọn để đăng (mặc định là tất cả). */
    _activeRenders() {
        if (!this.selectedRenders) return this.renders;
        return this.renders.filter(r => this.selectedRenders.includes(r.id));
    },

    _isRenderPicked(r) {
        return !this.selectedRenders || this.selectedRenders.includes(r.id);
    },

    _renderPickVariants() {
        if (!this.renders.length) return '';
        const active = this._activeRenders().length;

        return `
            <div class="pick-variants">
                <div class="pick-variants-head">
                    <span><strong>Chọn biến thể để đăng</strong> —
                          <span id="pickCount">${active}/${this.renders.length}</span> bản</span>
                    <div>
                        <button class="btn btn-xs btn-outline" onclick="StudioPage.pickAllRenders(true)">Chọn tất cả</button>
                        <button class="btn btn-xs btn-outline" onclick="StudioPage.pickAllRenders(false)">Bỏ chọn</button>
                    </div>
                </div>
                <div class="pick-variants-grid">
                    ${this.renders.map((r, i) => `
                        <label class="pick-variant ${this._isRenderPicked(r) ? 'picked' : ''}"
                               data-render-id="${r.id}">
                            <input type="checkbox" ${this._isRenderPicked(r) ? 'checked' : ''}
                                   onchange="StudioPage.toggleRender(${r.id}, this.checked)">
                            <video src="${r.media_url}" preload="metadata" muted
                                   onclick="event.preventDefault(); this.paused ? this.play() : this.pause()"></video>
                            <span class="pick-variant-label">
                                #${String(i + 1).padStart(3, '0')} ${this._esc(r.recipe?.look_name || '')}
                            </span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
    },

    toggleRender(renderId, checked) {
        // Lần đầu bỏ tick thì chuyển từ "tất cả" sang danh sách cụ thể
        if (!this.selectedRenders) {
            this.selectedRenders = this.renders.map(r => r.id);
        }
        if (checked) {
            if (!this.selectedRenders.includes(renderId)) this.selectedRenders.push(renderId);
        } else {
            this.selectedRenders = this.selectedRenders.filter(id => id !== renderId);
        }
        this._repaintPickState();
    },

    pickAllRenders(all) {
        this.selectedRenders = all ? null : [];
        this._repaintPickState();
    },

    /** Cập nhật ngay trên DOM thay vì vẽ lại cả trang.
     *
     *  Vẽ lại cả trang sẽ tải lại clip, dự án và Fanpage từ máy chủ rồi dựng lại
     *  cả 7 bước — màn hình nhảy về đầu, trông như trang bị tải lại.
     */
    _repaintPickState() {
        document.querySelectorAll('.pick-variant').forEach(el => {
            const on = this._isRenderPicked({ id: Number(el.dataset.renderId) });
            el.classList.toggle('picked', on);
            const box = el.querySelector('input[type="checkbox"]');
            if (box) box.checked = on;
        });

        const n = this._activeRenders().length;
        const count = document.getElementById('pickCount');
        if (count) count.textContent = `${n}/${this.renders.length}`;
        const rotate = document.getElementById('rotateCount');
        if (rotate) rotate.textContent = `${n} bản đã chọn`;
    },

    // ══ Thao tác: assets ══════════════════════════════════
    _wireUploadZone(zoneId, kind) {
        const zone = document.getElementById(zoneId);
        if (!zone) return;
        const input = zone.querySelector('input[type=file]');

        zone.addEventListener('click', () => input.click());
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            this.uploadFiles([...e.dataTransfer.files], kind);
        });
        input.addEventListener('change', (e) => {
            this.uploadFiles([...e.target.files], kind);
            e.target.value = '';
        });
    },

    async uploadFiles(files, kind) {
        if (!files.length) return;

        for (const file of files) {
            Toast.info(`Đang tải lên: ${file.name}...`);
            try {
                const fd = new FormData();
                fd.append('file', file);
                const res = await API.post(`/api/studio/assets/upload?kind=${kind}`, fd);
                if (res.status === 'ok') {
                    Toast.success(`Đã thêm: ${res.asset.name}`);
                } else {
                    Toast.error(`Lỗi với ${file.name}`);
                }
            } catch (e) {
                Toast.error(`Không tải được ${file.name}: ${e.message}`);
            }
        }

        await this._loadAll();
        App.refreshPage();
    },

    async deleteAsset(assetId) {
        if (!confirm('Xoá file này khỏi kho Studio?')) return;
        try {
            await API.delete(`/api/studio/assets/${assetId}`);

            // Gỡ mọi tham chiếu tới asset vừa xoá khỏi timeline
            const removed = [];
            this.timeline.segments.forEach((s, i) => {
                if (s.asset_id === assetId) removed.push(i);
            });
            removed.reverse().forEach(i => this._spliceSegment(i));
            if (this.timeline.audio.asset_id === assetId) {
                this.timeline.audio.asset_id = null;
                this.timeline.audio.mode = 'original';
            }
            this.selectedMusic = this.selectedMusic.filter(id => id !== assetId);

            // Phải lưu lại: nếu chỉ sửa trong bộ nhớ, mở lại dự án là các cảnh
            // trỏ tới clip vừa xoá sẽ quay về và làm bước ghép thất bại.
            if (removed.length && this.project?.id) {
                await this.saveProject(true);
            }

            Toast.success(removed.length
                ? `Đã xoá clip và ${removed.length} cảnh đang dùng nó`
                : 'Đã xoá');
            await this._loadAll();
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    // ══ Thao tác: timeline ════════════════════════════════
    addSegment(assetId) {
        const asset = this.videoAssets.find(a => a.id === assetId);
        if (!asset) return;

        this.timeline.segments.push({
            asset_id: assetId,
            start: 0,
            end: Number(asset.duration) || 5,
        });
        if (this.timeline.segments.length > 1) {
            this.timeline.transitions.push({ type: 'fade', duration: 0.5 });
        }
        App.refreshPage();
    },

    _spliceSegment(i) {
        this.timeline.segments.splice(i, 1);
        // Chuyển cảnh nằm GIỮA các cảnh: xoá cảnh thứ i thì bỏ mối nối liền trước nó
        const transIndex = i > 0 ? i - 1 : 0;
        if (this.timeline.transitions.length) {
            this.timeline.transitions.splice(transIndex, 1);
        }
    },

    removeSegment(i) {
        this._spliceSegment(i);
        App.refreshPage();
    },

    moveSegment(i, dir) {
        const j = i + dir;
        const segs = this.timeline.segments;
        if (j < 0 || j >= segs.length) return;
        [segs[i], segs[j]] = [segs[j], segs[i]];
        App.refreshPage();
    },

    /** Cập nhật điểm cắt. Không vẽ lại cả trang để kéo slider mượt. */
    onTrim(i, which, value, fromNumber = false) {
        const seg = this.timeline.segments[i];
        const asset = this.videoAssets.find(a => a.id === seg.asset_id);
        const dur = asset?.duration || 0;
        let val = Math.max(0, Math.min(dur, Number(value) || 0));

        const MIN_LEN = 0.3;
        if (which === 'start') {
            seg.start = Math.min(val, (seg.end ?? dur) - MIN_LEN);
        } else {
            seg.end = Math.max(val, (seg.start ?? 0) + MIN_LEN);
        }

        const start = seg.start, end = seg.end;

        // Đồng bộ slider ↔ ô số ↔ nhãn, và tua video tới đúng khung đang chỉnh
        const rangeEl = document.getElementById(`trimRange${i}`);
        if (rangeEl && dur) {
            rangeEl.style.left = `${start / dur * 100}%`;
            rangeEl.style.width = `${(end - start) / dur * 100}%`;
        }
        const lenEl = document.getElementById(`segLen${i}`);
        if (lenEl) lenEl.textContent = `${(end - start).toFixed(1)}s`;

        const startNum = document.getElementById(`trimStartNum${i}`);
        const endNum = document.getElementById(`trimEndNum${i}`);
        if (startNum) startNum.value = start.toFixed(1);
        if (endNum) endNum.value = end.toFixed(1);

        if (fromNumber) {
            const s = document.getElementById(`trimStart${i}`);
            const e = document.getElementById(`trimEnd${i}`);
            if (s) s.value = start;
            if (e) e.value = end;
        }

        const video = document.getElementById(`segVideo${i}`);
        if (video) {
            video.pause();
            video.currentTime = which === 'start' ? start : Math.max(0, end - 0.1);
        }

        this._updateTotalBadge();
    },

    takeWholeClip(i) {
        const seg = this.timeline.segments[i];
        const asset = this.videoAssets.find(a => a.id === seg.asset_id);
        seg.start = 0;
        seg.end = asset?.duration || seg.end;
        App.refreshPage();
    },

    playSegment(i) {
        const seg = this.timeline.segments[i];
        const video = document.getElementById(`segVideo${i}`);
        if (!video) return;

        video.currentTime = seg.start;
        video.play();

        // Dừng đúng điểm cắt cuối
        const stopAt = seg.end;
        const onTick = () => {
            if (video.currentTime >= stopAt) {
                video.pause();
                video.removeEventListener('timeupdate', onTick);
            }
        };
        video.addEventListener('timeupdate', onTick);
    },

    setTransition(i, field, value) {
        if (!this.timeline.transitions[i]) {
            this.timeline.transitions[i] = { type: 'fade', duration: 0.5 };
        }
        this.timeline.transitions[i][field] =
            field === 'duration' ? Math.max(0.1, Math.min(2.5, Number(value) || 0.5)) : value;
        this._updateTotalBadge();
    },

    setCanvas(presetId) {
        const preset = (this.options.canvas_presets || []).find(p => p.id === presetId);
        if (!preset) return;
        this.timeline.canvas.width = preset.width;
        this.timeline.canvas.height = preset.height;
    },

    setFit(fit) {
        this.timeline.canvas.fit = fit;
    },

    _totalDuration() {
        const segs = this.timeline.segments;
        if (!segs.length) return 0;

        // Bỏ qua cảnh trỏ tới clip đã bị xoá — chúng không vào được thành phẩm,
        // nếu cộng vào thì con số hiển thị sẽ dài hơn video thật.
        let total = segs.reduce((sum, s) => {
            const asset = this.videoAssets.find(a => a.id === s.asset_id);
            if (!asset) return sum;
            const end = s.end ?? asset.duration ?? 0;
            return sum + Math.max(0, end - (s.start ?? 0));
        }, 0);

        // Mỗi hiệu ứng chuyển cảnh làm hai cảnh chồng lên nhau, rút ngắn tổng thời lượng
        for (let i = 0; i < segs.length - 1; i++) {
            const t = this.timeline.transitions[i];
            if (t && t.type !== 'none') total -= Number(t.duration) || 0;
        }
        return Math.max(0, total);
    },

    _updateTotalBadge() {
        const badge = document.querySelector('.studio-step .badge-accent');
        if (!badge) return;
        badge.textContent = `Thành phẩm: ${this._totalDuration().toFixed(1)}s`;
        badge.title = this._durationExplain();
    },

    /** Diễn giải cách ra con số thời lượng, để không ai thắc mắc vì sao bị hụt. */
    _durationExplain() {
        const parts = [];
        this.timeline.segments.forEach(s => {
            const asset = this.videoAssets.find(a => a.id === s.asset_id);
            if (!asset) return;
            const end = s.end ?? asset.duration ?? 0;
            parts.push(Math.max(0, end - (s.start ?? 0)).toFixed(1));
        });
        if (!parts.length) return 'Chưa có cảnh nào.';

        let trans = 0;
        for (let i = 0; i < this.timeline.segments.length - 1; i++) {
            const t = this.timeline.transitions[i];
            if (t && t.type !== 'none') trans += Number(t.duration) || 0;
        }

        const sum = parts.join(' + ');
        if (!trans) return `${sum} = ${this._totalDuration().toFixed(1)}s`;
        return `${sum} − ${trans.toFixed(1)} (chuyển cảnh chồng hai cảnh lên nhau) `
             + `= ${this._totalDuration().toFixed(1)}s`;
    },

    // ══ Thao tác: text ════════════════════════════════════
    addText() {
        const total = this._totalDuration() || 10;
        this.timeline.texts.push({
            text: '',
            position: this.timeline.texts.length ? 'bottom' : 'top',
            size: 64,
            color: '#FFFFFF',
            style: 'shadow',
            start: 0,
            end: Math.round(total * 10) / 10,
        });
        App.refreshPage();
    },

    setText(i, field, value) {
        const numeric = ['size', 'start', 'end'];
        this.timeline.texts[i][field] = numeric.includes(field) ? Number(value) || 0 : value;
    },

    removeText(i) {
        this.timeline.texts.splice(i, 1);
        App.refreshPage();
    },

    // ══ Thao tác: âm thanh ════════════════════════════════
    setAudioMode(mode) {
        this.timeline.audio.mode = mode;
        App.refreshPage();
    },

    pickMusic(assetId) {
        this.timeline.audio.asset_id =
            this.timeline.audio.asset_id === assetId ? null : assetId;
        if (this.timeline.audio.asset_id && this.timeline.audio.mode === 'original') {
            this.timeline.audio.mode = 'music';
        }
        App.refreshPage();
    },

    toggleLook(lookId, checked) {
        if (checked) {
            if (!this.selectedLooks.includes(lookId)) this.selectedLooks.push(lookId);
        } else {
            this.selectedLooks = this.selectedLooks.filter(id => id !== lookId);
        }
        this._markChip(`.look-chip input[value="${lookId}"]`, checked);
    },

    toggleMusic(assetId, checked) {
        if (checked) {
            if (!this.selectedMusic.includes(assetId)) this.selectedMusic.push(assetId);
        } else {
            this.selectedMusic = this.selectedMusic.filter(id => id !== assetId);
        }
        this._markChip(`.look-chip input[value="${assetId}"]`, checked);
    },

    /** Bật/tắt viền sáng của chip vừa tích — nếu không, người dùng tích mà
     *  không thấy gì thay đổi nên tưởng nút hỏng. */
    _markChip(selector, on) {
        const input = document.querySelector(selector);
        if (input && input.parentElement) {
            input.parentElement.classList.toggle('active', on);
        }
    },

    // ══ Dự án / ghép / render ═════════════════════════════
    async saveProject(silent = false) {
        const nameEl = document.getElementById('projectName');
        const name = nameEl?.value.trim() || 'Dự án mới';

        try {
            if (this.project?.id) {
                const res = await API.put(`/api/studio/projects/${this.project.id}`, {
                    name, timeline: this.timeline,
                });
                this.project = res.project;
            } else {
                const res = await API.post('/api/studio/projects', {
                    name, timeline: this.timeline,
                });
                this.project = res.project;
            }
            if (!silent) Toast.success('Đã lưu dự án');
            return true;
        } catch (e) {
            Toast.error('Lưu dự án lỗi: ' + e.message);
            return false;
        }
    },

    _setComposeStatus(text, tone = '') {
        const el = document.getElementById('composeStatus');
        if (el) el.innerHTML = `<span class="status-${tone || 'muted'}">${this._esc(text)}</span>`;
    },

    async compose() {
        if (!this.timeline.segments.length) {
            Toast.error('Chưa có cảnh nào. Thêm ít nhất 1 cảnh ở bước 2.');
            return;
        }

        const btn = document.getElementById('composeBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Đang ghép...'; }
        this._setComposeStatus('Đang ghép video, vui lòng đợi...', 'working');

        try {
            if (!await this.saveProject(true)) return;

            const res = await API.post(`/api/studio/projects/${this.project.id}/compose`, {
                timeline: this.timeline,
            });

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Ghép video thất bại');
                this._setComposeStatus(res.error || 'Ghép video thất bại', 'error');
                return;
            }

            this.baseUrl = res.base_url + '?t=' + Date.now();
            this.baseDuration = res.duration || 0;
            this.baseStale = false;   // vừa ghép nên chắc chắn khớp
            Toast.success(`Ghép xong — ${this.baseDuration.toFixed(1)} giây`);
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            this._setComposeStatus('Lỗi: ' + e.message, 'error');
        } finally {
            if (btn && document.body.contains(btn)) {
                btn.disabled = false;
                btn.textContent = 'Ghép video & Xem trước';
            }
        }
    },

    async startBatch() {
        if (!this.project?.id || !this.baseUrl) {
            Toast.error('Ghép video ở bước 5 trước đã.');
            return;
        }
        if (!this.selectedLooks.length) {
            Toast.error('Chọn ít nhất một bộ màu.');
            return;
        }

        const btn = document.getElementById('batchBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Đang render...'; }

        // Máy chủ đọc cấu hình hook từ dự án đã lưu, nên phải lưu trước khi render
        await this.saveProject(true);

        this.renders = [];
        this.selectedRenders = null;   // lượt mới thì mặc định chọn hết
        this._repaintRenders();

        try {
            const res = await API.post(`/api/studio/projects/${this.project.id}/batch`, {
                count: this.batchCount,
                look_ids: this.selectedLooks,
                music_asset_ids: this.selectedMusic,
                keep_original_audio: this.timeline.audio.mode === 'mix',
                music_volume: 1.0,
            });

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Không khởi động được render');
                if (btn) { btn.disabled = false; btn.textContent = `Render ${this.batchCount} biến thể`; }
                return;
            }

            this.batchJob = res.job;
            Toast.info(`Bắt đầu render ${this.batchCount} biến thể. Có thể mất vài phút.`);
            this._updateBatchProgress(0, this.batchCount, 'Đang khởi động...');
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (btn) { btn.disabled = false; btn.textContent = `Render ${this.batchCount} biến thể`; }
        }
    },

    _updateBatchProgress(current, total, message) {
        const el = document.getElementById('batchProgress');
        if (!el) return;

        const pct = total ? Math.round(current / total * 100) : 0;
        const done = this.batchJob && ['completed', 'failed'].includes(this.batchJob.status);

        el.innerHTML = `
            <div class="progress-bar">
                <div class="progress-fill" style="width:${pct}%"></div>
            </div>
            <div class="progress-text">${this._esc(message || '')} (${pct}%)</div>
        `;

        if (done) {
            const btn = document.getElementById('batchBtn');
            if (btn) { btn.disabled = false; btn.textContent = `Render ${this.batchCount} biến thể`; }
        }
    },

    _repaintRenders() {
        const grid = document.getElementById('renderGrid');
        if (grid) grid.innerHTML = this._renderRenderCards();

        const panel = document.getElementById('exportPanel');
        if (panel) panel.innerHTML = this._renderExportPanel();
    },

    // ══ Xuất biến thể ═════════════════════════════════════
    showExportPicker() {
        if (!this.renders.length) {
            Toast.error('Chưa có biến thể nào để xuất');
            return;
        }

        this._exportPath = this.lastExportPath || '';
        Modal.open(`
            <h3 class="modal-title">Xuất ${this.renders.length} biến thể ra máy</h3>
            <p class="form-hint" style="margin-bottom:12px">
                Chọn ổ đĩa rồi bấm vào từng thư mục để đi sâu vào trong.
                File sẽ được chép vào thư mục con đặt theo tên dự án và thời gian.
            </p>
            <div class="folder-current" id="folderCurrent">Chọn ổ đĩa để bắt đầu</div>
            <div class="folder-list" id="folderList"></div>
            <label class="radio-chip" style="margin-top:12px">
                <input type="checkbox" id="exportSubfolder" checked>
                Tạo thư mục con theo tên dự án
            </label>
            <div class="modal-actions">
                <button class="btn btn-outline" onclick="Modal.close()">Huỷ</button>
                <button class="btn btn-outline" onclick="StudioPage.folderUp()" id="folderUpBtn" disabled>↑ Lên thư mục cha</button>
                <button class="btn btn-primary" onclick="StudioPage.confirmExport()" id="exportConfirmBtn" disabled>
                    Lưu vào đây
                </button>
            </div>
        `);
        this.navigateFolder('');
    },

    async navigateFolder(path) {
        const list = document.getElementById('folderList');
        const current = document.getElementById('folderCurrent');
        if (!list) return;

        list.innerHTML = '<div class="folder-loading">Đang tải...</div>';

        try {
            const res = await API.browseFolders(path);
            this._exportPath = res.current_path || '';
            this._parentPath = res.parent_path || '';

            if (current) {
                current.textContent = this._exportPath || 'Chọn ổ đĩa để bắt đầu';
            }

            const confirmBtn = document.getElementById('exportConfirmBtn');
            if (confirmBtn) confirmBtn.disabled = !this._exportPath;
            const upBtn = document.getElementById('folderUpBtn');
            if (upBtn) upBtn.disabled = !this._parentPath;

            const folders = res.folders || [];
            list.innerHTML = folders.length
                ? folders.map(f => `
                    <button class="folder-item" onclick="StudioPage.navigateFolder(${JSON.stringify(f.path).replace(/"/g, '&quot;')})">
                        <span class="folder-icon">${f.type === 'drive' ? '💾' : '📁'}</span>
                        <span class="folder-name">${this._esc(f.name)}</span>
                        <span class="folder-arrow">›</span>
                    </button>
                `).join('')
                : '<div class="folder-loading">Thư mục trống — có thể lưu vào đây</div>';
        } catch (e) {
            list.innerHTML = `<div class="folder-loading error-text">Không mở được: ${this._esc(e.message)}</div>`;
        }
    },

    folderUp() {
        if (this._parentPath) this.navigateFolder(this._parentPath);
    },

    async confirmExport() {
        if (!this._exportPath) {
            Toast.error('Chọn thư mục trước');
            return;
        }

        const btn = document.getElementById('exportConfirmBtn');
        const subfolder = document.getElementById('exportSubfolder')?.checked ?? true;
        if (btn) { btn.disabled = true; btn.textContent = 'Đang chép...'; }

        try {
            const res = await API.post('/api/studio/export', {
                export_path: this._exportPath,
                job_id: this.batchJob?.job_id || '',
                project_id: this.project?.id || null,
                create_subfolder: subfolder,
            });

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Xuất thất bại');
                if (btn) { btn.disabled = false; btn.textContent = 'Lưu vào đây'; }
                return;
            }

            this.lastExportPath = res.export_path;
            Modal.close();

            const mb = (res.total_bytes / 1048576).toFixed(0);
            Toast.success(`Đã xuất ${res.exported_count} video (${mb} MB) vào ${res.export_path}`);
            if (res.failed_count) {
                Toast.error(`${res.failed_count} file không chép được`);
            }

            const panel = document.getElementById('exportPanel');
            if (panel) panel.innerHTML = this._renderExportPanel();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (btn) { btn.disabled = false; btn.textContent = 'Lưu vào đây'; }
        }
    },

    async openExportFolder() {
        if (!this.lastExportPath) return;
        try {
            await API.post('/api/studio/open-folder', { path: this.lastExportPath });
        } catch (e) {
            Toast.error('Không mở được thư mục: ' + e.message);
        }
    },

    downloadZip() {
        if (!this.renders.length) {
            Toast.error('Chưa có biến thể nào để tải');
            return;
        }

        const params = new URLSearchParams();
        if (this.batchJob?.job_id) params.set('job_id', this.batchJob.job_id);
        else if (this.project?.id) params.set('project_id', this.project.id);

        Toast.info('Đang gói file, với nhiều video có thể mất một lúc...');
        // Điều hướng trực tiếp để trình duyệt tự quản lý việc tải file lớn
        window.location.href = `/api/studio/export/zip?${params.toString()}`;
    },

    // ══ Đăng Fanpage ══════════════════════════════════════
    pickAllPages(checked) {
        document.querySelectorAll('.page-check').forEach(el => { el.checked = checked; });
    },

    async distribute() {
        const pageIds = [...document.querySelectorAll('.page-check:checked')].map(el => +el.value);
        if (!pageIds.length) {
            Toast.error('Chọn ít nhất một Fanpage');
            return;
        }

        const caption = document.getElementById('publishCaption')?.value.trim() || '';
        const firstComment = document.getElementById('publishFirstComment')?.value.trim() || '';
        const commentImage = document.getElementById('publishCommentImage')?.value.trim() || '';
        const scheduleRaw = document.getElementById('publishSchedule')?.value || '';
        const interval = +(document.getElementById('publishInterval')?.value || 0);

        const picked = this._activeRenders();
        if (!picked.length) {
            Toast.error('Chưa chọn biến thể nào để đăng');
            return;
        }

        const when = scheduleRaw ? 'hẹn giờ' : 'đăng ngay';
        if (!confirm(`Sẽ ${when} lên ${pageIds.length} Fanpage, xoay vòng qua `
                   + `${picked.length} biến thể đã chọn. Tiếp tục?`)) {
            return;
        }

        const btn = document.getElementById('distributeBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Đang đăng...'; }

        try {
            const res = await API.post('/api/studio/distribute', {
                job_id: this.batchJob?.job_id || '',
                project_id: this.project?.id || null,
                page_ids: pageIds,
                caption,
                first_comment: firstComment,
                comment_image_url: commentImage,
                schedule_start: scheduleRaw ? new Date(scheduleRaw).toISOString() : null,
                interval_minutes: interval,
                render_ids: picked.map(r => r.id),
            });

            if (res.status !== 'ok') {
                Toast.error(res.error || 'Đăng thất bại');
                return;
            }

            const rs = res.results || [];
            const failed = rs.filter(r => r.status === 'failed');
            const queued = rs.filter(r => r.status === 'queued').length;

            if (failed.length) {
                Toast.error(`${res.posted}/${res.total} thành công, ${failed.length} lỗi`);
            } else if (queued) {
                Toast.success(`Đã xếp ${queued} bài vào hàng đợi`);
            } else {
                Toast.success(`Đã xử lý ${res.posted}/${res.total} Fanpage`);
            }
            if (queued) QueuePanel.show();
            this._showDistributeResult(rs);
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        } finally {
            if (btn && document.body.contains(btn)) {
                btn.disabled = false;
                btn.textContent = 'Đăng lên các Fanpage đã chọn';
            }
        }
    },

    _showDistributeResult(results) {
        const el = document.getElementById('distributeResult');
        if (!el) return;

        el.innerHTML = `
            <div class="distribute-result">
                <h4>Kết quả đăng</h4>
                <table class="data-table">
                    <thead>
                        <tr><th>Fanpage</th><th>Biến thể</th><th>Trạng thái</th></tr>
                    </thead>
                    <tbody>
                        ${results.map(r => {
                            const page = this.pages.find(p => p.id === r.page_id);
                            const label = { posted: 'Đã đăng', scheduled: 'Đã hẹn giờ', failed: 'Lỗi' }[r.status] || r.status;
                            return `
                                <tr>
                                    <td>${this._esc(page?.page_name || r.page_id)}</td>
                                    <td class="mono">${this._esc(r.variant || '')}</td>
                                    <td>
                                        <span class="status-pill ${r.status}">${label}</span>
                                        ${r.error ? `<div class="error-text">${this._esc(r.error)}</div>` : ''}
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    },

    // ══ Tiện ích ══════════════════════════════════════════
    _esc(str) {
        return String(str ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    },

    _attr(str) { return this._esc(str); },

    _trunc(str, len) {
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
        const m = Math.floor(s / 60);
        return `${m}:${String(s % 60).padStart(2, '0')}`;
    },
};
