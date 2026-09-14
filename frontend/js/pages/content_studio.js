// Content Studio — Chọn variant + chọn page/channel + đăng multi-platform
const ContentStudioPage = {
    selectedVariant: null,
    selectedPages: [],
    selectedChannels: [],
    activePlatformTab: 'facebook',
    channels: [],
    pinterestBoards: {},
    selectedBoardId: '',
    spinEnabled: false,
    spinResults: null,

    async render() {
        // Load variants (from existing spoof system)
        let jobs = [];
        try {
            const res = await API.listJobs();
            jobs = (res.jobs || []).filter(j => j.status === 'completed' && j.variants?.length);
        } catch (e) { /* empty */ }

        let pages = [];
        try {
            const res = await API.get('/api/pages?status=active');
            pages = res.pages || [];
        } catch (e) { /* empty */ }

        // Load multi-platform channels
        let channels = [];
        try {
            const res = await API.get('/api/channels');
            channels = res.channels || [];
            this.channels = channels;
        } catch (e) { /* empty */ }

        const pinterestChannels = channels.filter(c => c.platform === 'pinterest');
        const youtubeChannels = channels.filter(c => c.platform === 'youtube');

        const allVariants = [];
        jobs.forEach(j => {
            (j.variants || []).forEach((v, idx) => {
                // Create globally unique key: jobId_variantIndex
                const uniqueKey = `${j.job_id}_${idx}`;
                allVariants.push({
                    ...v,
                    _key: uniqueKey,
                    jobId: j.job_id,
                    sourceName: j.video_title || j.filename || '',
                    videoTitle: j.video_title || '',
                    videoDescription: j.video_description || '',
                });
            });
        });

        // Detect user timezone
        const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
        const tzOffset = new Date().getTimezoneOffset();
        const tzSign = tzOffset <= 0 ? '+' : '-';
        const tzHours = String(Math.floor(Math.abs(tzOffset) / 60)).padStart(2, '0');
        const tzMins = String(Math.abs(tzOffset) % 60).padStart(2, '0');
        const tzLabel = `UTC${tzSign}${tzHours}:${tzMins}`;

        return `
            <div class="page-header">
                <h1 class="page-title">🎬 Content Studio</h1>
                <p class="page-subtitle">Select Variant → Select Targets → Publish</p>
            </div>

            <div class="studio-layout">
                <!-- Step 1: Select Variant -->
                <div class="studio-step card">
                    <div class="card-header">
                        <h3 class="card-title">① Select Video Variant</h3>
                        <span class="badge" id="variantCount">${allVariants.length} variants</span>
                    </div>
                    <div class="card-body">
                        <div class="variant-grid" id="variantGrid">
                            ${allVariants.length ? allVariants.map(v => `
                                <div class="variant-card-mini ${this.selectedVariant?._key === v._key ? 'selected' : ''}"
                                     onclick="ContentStudioPage.selectVariant(${JSON.stringify(v).replace(/"/g, '&quot;')})"
                                     data-variant-key="${v._key}">
                                    <div class="variant-thumb">
                                        <video src="/media/variants/${v.filename}" muted preload="metadata"></video>
                                    </div>
                                    <div class="variant-info-mini">
                                        <div class="variant-name">${v.filename}</div>
                                        <div class="variant-source">${v.sourceName || ''}</div>
                                    </div>
                                </div>
                            `).join('') : `
                                <div class="empty-mini">
                                    No variants yet. <a href="#spoofer">Create variants</a> first.
                                </div>
                            `}
                        </div>
                    </div>
                </div>

                <!-- Step 2: Select Targets -->
                <div class="studio-step card">
                    <div class="card-header">
                        <h3 class="card-title">② Select Targets</h3>
                        <div class="header-actions">
                            <button class="btn btn-xs btn-outline" onclick="ContentStudioPage.selectAllTargets()">Select All</button>
                            <button class="btn btn-xs btn-outline" onclick="ContentStudioPage.deselectAllTargets()">Deselect All</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <!-- Platform Tabs -->
                        <div class="platform-tabs" id="platformTabs">
                            <button class="platform-tab active" data-platform="facebook" onclick="ContentStudioPage.switchPlatformTab('facebook')">
                                <span class="platform-icon">📘</span> Facebook <span class="platform-count">${pages.length}</span>
                            </button>
                            <button class="platform-tab" data-platform="pinterest" onclick="ContentStudioPage.switchPlatformTab('pinterest')">
                                <span class="platform-icon">📌</span> Pinterest <span class="platform-count">${pinterestChannels.length}</span>
                            </button>
                            <button class="platform-tab" data-platform="youtube" onclick="ContentStudioPage.switchPlatformTab('youtube')">
                                <span class="platform-icon">▶️</span> YouTube <span class="platform-count">${youtubeChannels.length}</span>
                            </button>
                        </div>

                        <!-- Facebook Pages Panel -->
                        <div class="platform-panel" id="panel-facebook" style="display:block;">
                            <div class="page-select-grid" id="pageSelectGrid">
                                ${pages.length ? pages.map(p => `
                                    <label class="page-select-item" data-page-id="${p.id}">
                                        <input type="checkbox" class="page-checkbox" value="${p.id}" onchange="ContentStudioPage.togglePage(${p.id})">
                                        <div class="page-select-info">
                                            ${p.avatar_url ? `<img src="${p.avatar_url}" class="page-avatar-sm">` : '📄'}
                                            <span>${p.page_name}</span>
                                        </div>
                                    </label>
                                `).join('') : '<div class="empty-mini">No pages yet. <a href="#accounts">Add an account</a> first.</div>'}
                            </div>
                        </div>

                        <!-- Pinterest Channels Panel -->
                        <div class="platform-panel" id="panel-pinterest" style="display:none;">
                            <div class="page-select-grid" id="pinterestGrid">
                                ${pinterestChannels.length ? pinterestChannels.map(c => `
                                    <label class="page-select-item channel-item" data-channel-id="${c.id}">
                                        <input type="checkbox" class="channel-checkbox" value="${c.id}" data-platform="pinterest" onchange="ContentStudioPage.togglePinterestChannel(${c.id})">
                                        <div class="page-select-info">
                                            <span class="platform-badge pinterest">📌</span>
                                            <span>${c.channel_name}</span>
                                        </div>
                                    </label>
                                `).join('') : '<div class="empty-mini">No Pinterest accounts. <a href="#accounts">Add an account</a> first.</div>'}
                            </div>
                            <!-- Board selector (shown when a Pinterest channel is checked) -->
                            <div id="boardSelectorContainer" style="display:none; margin-top:10px;">
                                <label style="font-size:13px; color:var(--text-muted); margin-bottom:4px; display:block;">📋 Chọn Board để đăng:</label>
                                <select id="boardSelect" class="form-select" onchange="ContentStudioPage.selectBoard(this.value)" style="width:100%;">
                                    <option value="">-- Đang tải boards... --</option>
                                </select>
                            </div>
                        </div>

                        <!-- YouTube Channels Panel -->
                        <div class="platform-panel" id="panel-youtube" style="display:none;">
                            <div class="page-select-grid" id="youtubeGrid">
                                ${youtubeChannels.length ? youtubeChannels.map(c => `
                                    <label class="page-select-item channel-item" data-channel-id="${c.id}">
                                        <input type="checkbox" class="channel-checkbox" value="${c.id}" data-platform="youtube" onchange="ContentStudioPage.toggleChannel(${c.id})">
                                        <div class="page-select-info">
                                            <span class="platform-badge youtube">▶️</span>
                                            <span>${c.channel_name}</span>
                                        </div>
                                    </label>
                                `).join('') : '<div class="empty-mini">No YouTube channels. <a href="#settings">Add in Settings</a></div>'}
                            </div>
                        </div>

                        <!-- Selected summary -->
                        <div class="selected-targets-summary" id="targetsSummary"></div>
                    </div>
                </div>

                <!-- Step 3: Caption & Publish -->
                <div class="studio-step card">
                    <div class="card-header">
                        <h3 class="card-title">③ Publish Reels</h3>
                    </div>
                    <div class="card-body">
                        <div class="form-group">
                            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                                <label style="margin:0;">Original Caption</label>
                                <button class="btn btn-xs btn-accent" id="aiRewriteBtn" onclick="ContentStudioPage.aiRewrite()" title="Use AI to rewrite viral caption + hashtags">
                                    ✨ AI Write Caption
                                </button>
                            </div>
                            <textarea id="reelCaption" class="form-input" rows="3" placeholder="Enter original caption or describe video content..."></textarea>
                            <div id="videoContextInfo" class="video-context-info" style="display:none; margin-top:4px; font-size:12px; color:var(--text-muted); opacity:0.8;">
                                📎 <span id="videoContextText"></span>
                            </div>
                        </div>

                        <!-- AI Result Panel -->
                        <div id="aiResultPanel" class="ai-result-panel" style="display:none;">
                            <div class="ai-result-header">
                                <span>🤖 Caption AI</span>
                                <div class="ai-result-actions">
                                    <button class="btn btn-xs btn-primary" onclick="ContentStudioPage.applyAiCaption()">✅ Apply</button>
                                    <button class="btn btn-xs btn-outline" onclick="ContentStudioPage.regenerateAi()">🔄 Rewrite</button>
                                    <button class="btn btn-xs btn-outline" onclick="document.getElementById('aiResultPanel').style.display='none'">✖</button>
                                </div>
                            </div>
                            <div id="aiCaptionPreview" class="ai-caption-preview"></div>
                            <div id="aiHashtagPreview" class="ai-hashtag-preview"></div>
                            <div id="aiTokenInfo" class="ai-token-info"></div>
                        </div>

                        <!-- Spin + First Comment Section -->
                        <div class="studio-spin-section">
                            <div class="studio-spin-header">
                                <h4>🎰 Content Spinning</h4>
                                <label class="studio-spin-toggle">
                                    <input type="checkbox" id="spinToggle" onchange="ContentStudioPage.toggleSpin()">
                                    <span>Unique caption per page</span>
                                </label>
                            </div>
                            <div id="spinControls" style="display:none;">
                                <p style="font-size:12px; color:var(--text-muted); margin:0 0 8px 0;">AI generates different captions for each page — avoids spam detection.</p>
                                <button class="btn btn-sm btn-accent" id="spinBtn" onclick="ContentStudioPage.generateSpins()">✨ Generate Spin (${this.selectedPages.length} pages)</button>
                                <div id="spinPreview" class="studio-spin-preview"></div>
                            </div>

                            <div class="studio-first-comment">
                                <label>💬 First Comment (auto-comment after posting)</label>
                                <input type="text" id="firstComment" class="form-input" placeholder="Leave empty if not needed — e.g. 'Link in bio!' or 'Shop now at mystore.com'">
                                <div style="margin-top:8px;">
                                    <label style="font-size:13px; color:var(--text-secondary);">🖼️ Comment Image (optional — attach product photo)</label>
                                    <input type="text" id="commentImageUrl" class="form-input" placeholder="Paste public image URL — e.g. https://mystore.com/product.jpg" style="margin-top:4px;">
                                    <p style="font-size:11px; color:var(--text-muted); margin:4px 0 0 0;">Image URL must be publicly accessible. Comment will include both text + image.</p>
                                </div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="scheduleToggle" onchange="ContentStudioPage.toggleSchedule()">
                                Schedule Post <span style="font-size:12px; color:var(--text-muted);">(${tzLabel} — ${tzName})</span>
                            </label>
                            <input type="datetime-local" id="scheduleTime" class="form-input" style="display:none; margin-top:8px;">
                        </div>
                        <div class="publish-summary" id="publishSummary">
                            <span id="summaryText">Select a variant and at least 1 page to publish</span>
                        </div>
                        <button class="btn btn-primary btn-lg" id="publishBtn" onclick="ContentStudioPage.publish()" disabled>
                            🚀 Publish Now
                        </button>
                    </div>
                </div>
            </div>

            <!-- Scheduled Posts Queue -->
            <div class="card" style="margin-top:20px;">
                <div class="card-header">
                    <h3 class="card-title">📅 Scheduled Posts Queue</h3>
                    <button class="btn btn-sm" onclick="ContentStudioPage.refreshQueue()">🔄 Refresh</button>
                </div>
                <div class="card-body" id="scheduleQueue">
                    <div class="loading-spinner">Loading...</div>
                </div>
            </div>
        `;
    },

    initQueue() {
        this.refreshQueue();
    },

    async refreshQueue() {
        try {
            const res = await API.get('/api/posts/schedule-debug');
            const el = document.getElementById('scheduleQueue');
            if (!el) return;

            if (!res.scheduled_posts || res.scheduled_posts.length === 0) {
                el.innerHTML = '<div class="empty-mini">No scheduled posts pending. Server UTC: ' + res.server_utc_now + '</div>';
                return;
            }

            const rows = res.scheduled_posts.map(p => {
                const statusClass = p.publish_status === 'READY' ? 'color:var(--success)' : 'color:var(--warning)';
                // Handle both '2026-04-07 09:58:00' and '2026-04-07T09:58:00.000Z' formats
                const isoStr = p.scheduled_at.replace(' ', 'T').replace(/Z*$/, '') + 'Z';
                const schedLocal = new Date(isoStr).toLocaleString();
                return `
                    <tr>
                        <td>#${p.id}</td>
                        <td>Page ${p.page_id}</td>
                        <td>${schedLocal}</td>
                        <td>${p.scheduled_at} (UTC)</td>
                        <td><strong style="${statusClass}">${p.publish_status}</strong></td>
                        <td><button class="btn btn-sm btn-danger" onclick="ContentStudioPage.cancelScheduled(${p.id})">✕</button></td>
                    </tr>
                `;
            }).join('');

            el.innerHTML = `
                <div style="font-size:12px; color:var(--text-muted); margin-bottom:8px;">
                    Server UTC: <strong>${res.server_utc_now}</strong> · ${res.total_pending} pending
                </div>
                <table class="table table-compact">
                    <thead><tr><th>ID</th><th>Page</th><th>Scheduled (Local)</th><th>Scheduled (UTC)</th><th>Status</th><th></th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            `;
        } catch (e) {
            const el = document.getElementById('scheduleQueue');
            if (el) el.innerHTML = '<div class="empty-mini">Error loading schedule: ' + e.message + '</div>';
        }
    },

    async cancelScheduled(postId) {
        if (!confirm('Cancel this scheduled post?')) return;
        try {
            await API.delete(`/api/posts/${postId}`);
            Toast.success('Scheduled post cancelled');
            this.refreshQueue();
        } catch (e) {
            Toast.error('Error: ' + e.message);
        }
    },

    selectVariant(variant) {
        this.selectedVariant = variant;
        // Use _key for unique matching — prevents multi-select bug
        document.querySelectorAll('.variant-card-mini').forEach(el => {
            el.classList.toggle('selected', el.dataset.variantKey === variant._key);
        });

        // Auto-fill caption from video description if available
        const captionEl = document.getElementById('reelCaption');
        const contextInfo = document.getElementById('videoContextInfo');
        const contextText = document.getElementById('videoContextText');

        if (variant.videoDescription && captionEl && !captionEl.value.trim()) {
            captionEl.value = variant.videoDescription;
        }

        // Show video context info
        if (variant.videoTitle && contextInfo && contextText) {
            contextText.textContent = `Video: ${variant.videoTitle}`;
            contextInfo.style.display = 'block';
        } else if (contextInfo) {
            contextInfo.style.display = 'none';
        }

        this.updateSummary();
    },

    togglePage(pageId) {
        const idx = this.selectedPages.indexOf(pageId);
        if (idx >= 0) this.selectedPages.splice(idx, 1);
        else this.selectedPages.push(pageId);
        this.updateSummary();
        this.updateTargetsSummary();
    },

    toggleChannel(channelId) {
        const idx = this.selectedChannels.indexOf(channelId);
        if (idx >= 0) this.selectedChannels.splice(idx, 1);
        else this.selectedChannels.push(channelId);
        this.updateSummary();
        this.updateTargetsSummary();
    },

    async togglePinterestChannel(channelId) {
        this.toggleChannel(channelId);

        // Check if any Pinterest channel is selected
        const pinterestSelected = this.selectedChannels.filter(id => {
            const ch = this.channels.find(c => c.id === id);
            return ch && ch.platform === 'pinterest';
        });

        const container = document.getElementById('boardSelectorContainer');
        if (!container) return;

        if (pinterestSelected.length === 0) {
            container.style.display = 'none';
            this.selectedBoardId = '';
            return;
        }

        container.style.display = 'block';
        const select = document.getElementById('boardSelect');

        // Fetch boards for the first selected Pinterest channel
        const chId = pinterestSelected[0];
        if (this.pinterestBoards[chId]) {
            this._renderBoardOptions(select, this.pinterestBoards[chId]);
            return;
        }

        select.innerHTML = '<option value="">⏳ Đang tải boards...</option>';
        try {
            const res = await API.get(`/api/channels/${chId}/boards`);
            const boards = res.boards || [];
            this.pinterestBoards[chId] = boards;
            this._renderBoardOptions(select, boards);
        } catch (e) {
            select.innerHTML = `<option value="">❌ Lỗi: ${e.message}</option>`;
        }
    },

    _renderBoardOptions(select, boards) {
        if (!boards.length) {
            select.innerHTML = '<option value="">⚠️ Chưa có board. Tạo board trên Pinterest trước.</option>';
            return;
        }
        select.innerHTML = '<option value="">-- Chọn Board --</option>' +
            boards.map(b => `<option value="${b.id}">${b.name} (${b.pin_count} pins, ${b.privacy})</option>`).join('');
    },

    selectBoard(boardId) {
        this.selectedBoardId = boardId;
        this.updateSummary();
    },

    switchPlatformTab(platform) {
        this.activePlatformTab = platform;
        document.querySelectorAll('.platform-tab').forEach(t => t.classList.toggle('active', t.dataset.platform === platform));
        document.querySelectorAll('.platform-panel').forEach(p => p.style.display = 'none');
        const panel = document.getElementById(`panel-${platform}`);
        if (panel) panel.style.display = 'block';
    },

    selectAllTargets() {
        const platform = this.activePlatformTab;
        if (platform === 'facebook') {
            this.selectedPages = [];
            document.querySelectorAll('.page-checkbox').forEach(cb => {
                cb.checked = true;
                this.selectedPages.push(parseInt(cb.value));
            });
        } else {
            document.querySelectorAll(`#panel-${platform} .channel-checkbox`).forEach(cb => {
                cb.checked = true;
                const id = parseInt(cb.value);
                if (!this.selectedChannels.includes(id)) this.selectedChannels.push(id);
            });
        }
        this.updateSummary();
        this.updateTargetsSummary();
    },

    deselectAllTargets() {
        const platform = this.activePlatformTab;
        if (platform === 'facebook') {
            this.selectedPages = [];
            document.querySelectorAll('.page-checkbox').forEach(cb => cb.checked = false);
        } else {
            document.querySelectorAll(`#panel-${platform} .channel-checkbox`).forEach(cb => {
                cb.checked = false;
                const id = parseInt(cb.value);
                const idx = this.selectedChannels.indexOf(id);
                if (idx >= 0) this.selectedChannels.splice(idx, 1);
            });
        }
        this.updateSummary();
        this.updateTargetsSummary();
    },

    updateTargetsSummary() {
        const el = document.getElementById('targetsSummary');
        if (!el) return;
        const parts = [];
        if (this.selectedPages.length) parts.push(`📘 ${this.selectedPages.length} FB page(s)`);
        const pCh = this.selectedChannels.filter(id => (this.channels.find(c => c.id === id) || {}).platform === 'pinterest');
        const yCh = this.selectedChannels.filter(id => (this.channels.find(c => c.id === id) || {}).platform === 'youtube');
        if (pCh.length) parts.push(`📌 ${pCh.length} Pinterest`);
        if (yCh.length) parts.push(`▶️ ${yCh.length} YouTube`);
        el.innerHTML = parts.length ? `<div class="targets-badge">${parts.join(' · ')}</div>` : '';
    },

    toggleSchedule() {
        const show = document.getElementById('scheduleToggle').checked;
        document.getElementById('scheduleTime').style.display = show ? 'block' : 'none';
        const btn = document.getElementById('publishBtn');
        btn.textContent = show ? '📅 Schedule Post' : '🚀 Publish Now';
    },

    updateSummary() {
        const totalTargets = this.selectedPages.length + this.selectedChannels.length;
        const ready = this.selectedVariant && totalTargets > 0;
        document.getElementById('publishBtn').disabled = !ready;
        document.getElementById('summaryText').textContent = ready
            ? `Ready: 1 video → ${totalTargets} target(s)`
            : 'Select a variant and at least 1 target to publish';
    },

    async publish() {
        const totalTargets = this.selectedPages.length + this.selectedChannels.length;
        if (!this.selectedVariant || totalTargets === 0) return;

        // Validate board selection for Pinterest
        const hasPinterest = this.selectedChannels.some(id => {
            const ch = this.channels.find(c => c.id === id);
            return ch && ch.platform === 'pinterest';
        });
        if (hasPinterest && !this.selectedBoardId) {
            Toast.error('⚠️ Vui lòng chọn Board Pinterest trước khi đăng!');
            return;
        }

        const btn = document.getElementById('publishBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Processing...';

        const isScheduled = document.getElementById('scheduleToggle').checked;
        const scheduleAt = isScheduled ? document.getElementById('scheduleTime').value : null;
        const firstComment = document.getElementById('firstComment')?.value?.trim() || '';
        const commentImageUrl = document.getElementById('commentImageUrl')?.value?.trim() || '';

        try {
            const variantId = parseInt(this.selectedVariant.id);

            // Build captions dict if spinning is enabled
            let captions = {};
            if (this.spinEnabled && this.spinResults) {
                captions = this.spinResults;
            }

            const res = await API.post('/api/posts/publish', {
                variant_id: isNaN(variantId) ? null : variantId,
                variant_filepath: this.selectedVariant.filepath || null,
                page_ids: this.selectedPages,
                channel_ids: this.selectedChannels,
                board_id: this.selectedBoardId || '',
                caption: document.getElementById('reelCaption').value,
                captions: captions,
                first_comment: firstComment,
                comment_image_url: commentImageUrl || null,
                schedule_at: scheduleAt ? new Date(scheduleAt).toISOString() : null,
            });

            const results = res.results || [];
            const queued = results.filter(r => r.status === 'queued').length;
            const success = results.filter(r => r.status === 'posted' || r.status === 'scheduled').length;
            const failed = results.filter(r => r.status === 'failed').length;

            // Đăng ngay giờ đi qua hàng đợi: bài được xếp hàng chứ chưa lên ngay,
            // nên phải nói đúng như vậy thay vì báo "đã đăng".
            if (queued > 0) {
                Toast.success(`Đã xếp ${queued} bài vào hàng đợi`);
                QueuePanel.show();
            }
            if (success > 0) Toast.success(`✅ ${success} bài ${isScheduled ? 'đã hẹn giờ' : 'đã đăng'}!`);
            if (failed > 0) Toast.error(`❌ ${failed} bài lỗi`);

            this.selectedVariant = null;
            this.selectedPages = [];
            App.refreshPage();
        } catch (e) {
            Toast.error('Error: ' + e.message);
            btn.disabled = false;
            btn.textContent = isScheduled ? '📅 Schedule Post' : '🚀 Publish Now';
        }
    },

    _lastAiResult: null,

    async aiRewrite() {
        const caption = document.getElementById('reelCaption').value.trim();
        if (!caption && !this.selectedVariant?.videoTitle) {
            Toast.error('Enter an original caption or select a variant with a video title for AI rewrite');
            return;
        }

        // Get page name from first selected page
        let pageName = 'Fanpage';
        let pageCategory = '';
        if (this.selectedPages.length > 0) {
            const el = document.querySelector(`[data-page-id="${this.selectedPages[0]}"] .page-select-info span`);
            if (el) pageName = el.textContent.trim();
        }

        // Get video title from selected variant
        const videoTitle = this.selectedVariant?.videoTitle || '';

        const btn = document.getElementById('aiRewriteBtn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Writing...';
        btn.disabled = true;

        try {
            const res = await API.post('/api/ai/rewrite-caption', {
                original_caption: caption,
                page_name: pageName,
                page_category: pageCategory,
                video_title: videoTitle,
            });

            if (res.status === 'ok') {
                this._lastAiResult = res;
                this._showAiResult(res);
                Toast.success(`✨ AI Caption ready! (${res.tokens_used} tokens)`);
            } else {
                Toast.error(res.error || 'AI error — check API Key in Settings');
            }
        } catch (e) {
            Toast.error('AI connection error: ' + e.message);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },

    _showAiResult(result) {
        const panel = document.getElementById('aiResultPanel');
        const captionEl = document.getElementById('aiCaptionPreview');
        const hashtagEl = document.getElementById('aiHashtagPreview');
        const tokenEl = document.getElementById('aiTokenInfo');

        captionEl.innerHTML = this._formatCaption(result.caption || '');
        hashtagEl.innerHTML = result.hashtags
            ? `<div class="hashtag-list">${result.hashtags.split(/\s+/).filter(h => h.startsWith('#')).map(h => `<span class="hashtag-tag">${h}</span>`).join(' ')}</div>`
            : '';
        tokenEl.textContent = `Model: ${result.model} • Tokens: ${result.tokens_used}`;
        panel.style.display = 'block';
    },

    _formatCaption(text) {
        return text.split('\n').map(line => {
            if (!line.trim()) return '<br>';
            return `<p>${line}</p>`;
        }).join('');
    },

    applyAiCaption() {
        if (!this._lastAiResult) return;
        const fullText = this._lastAiResult.full_text || this._lastAiResult.caption || '';
        document.getElementById('reelCaption').value = fullText;
        document.getElementById('aiResultPanel').style.display = 'none';
        Toast.success('✅ AI Caption applied');
    },

    regenerateAi() {
        document.getElementById('aiResultPanel').style.display = 'none';
        this.aiRewrite();
    },

    toggleSpin() {
        this.spinEnabled = document.getElementById('spinToggle').checked;
        const controls = document.getElementById('spinControls');
        if (controls) controls.style.display = this.spinEnabled ? 'block' : 'none';
    },

    async generateSpins() {
        if (!this.selectedPages.length) {
            Toast.error('Select at least 1 page first');
            return;
        }

        const baseCaption = document.getElementById('reelCaption').value.trim();
        const videoTitle = this.selectedVariant?.videoTitle || '';

        const btn = document.getElementById('spinBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Generating spins...';

        try {
            const res = await API.post('/api/ai/spin-captions', {
                base_caption: baseCaption,
                page_ids: this.selectedPages,
                video_title: videoTitle,
            });

            if (res.status === 'ok') {
                this.spinResults = res.spins;
                this._showSpinPreview(res.spins, res.tokens_used);
                Toast.success(`✨ Generated ${this.selectedPages.length} unique captions!`);
            } else {
                Toast.error(res.error || 'AI Spin error');
            }
        } catch (e) {
            Toast.error('Error: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.textContent = `✨ Generate Spin (${this.selectedPages.length} pages)`;
        }
    },

    _showSpinPreview(spins, tokensUsed) {
        const preview = document.getElementById('spinPreview');
        if (!preview) return;

        const pageCheckboxes = document.querySelectorAll('.page-checkbox:checked');
        const pageNames = {};
        pageCheckboxes.forEach(cb => {
            const label = cb.closest('.page-select-item');
            const nameEl = label?.querySelector('.page-select-info span');
            if (nameEl) pageNames[cb.value] = nameEl.textContent.trim();
        });

        let html = `<div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">Tokens: ${tokensUsed || '?'}</div>`;
        for (const [pageId, caption] of Object.entries(spins)) {
            const name = pageNames[pageId] || `Page #${pageId}`;
            html += `
                <div class="studio-spin-item">
                    <div class="studio-spin-page">${name}</div>
                    <div class="studio-spin-caption">${caption.replace(/\n/g, '<br>')}</div>
                </div>`;
        }
        preview.innerHTML = html;
    },

    reset() {
        this.selectedVariant = null;
        this.selectedPages = [];
        this.selectedChannels = [];
        this.activePlatformTab = 'facebook';
        this.spinEnabled = false;
        this.spinResults = null;
        this._lastAiResult = null;
    },

    init() {
        this.refreshQueue();
    },
};
