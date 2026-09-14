// Cài đặt hệ thống
const SettingsPage = {
    async render() {
        let settings = {};
        try {
            const res = await API.get('/api/settings');
            settings = res.settings || {};
        } catch (e) { /* empty */ }

        let storage = {};
        try {
            storage = await API.get('/api/settings/storage');
        } catch (e) { /* empty */ }

        return `
            <div class="page-header">
                <h1 class="page-title">⚙️ Cài Đặt Hệ Thống</h1>
                <p class="page-subtitle">Cấu hình Telegram, ngưỡng viral, auto-comment và lưu trữ</p>
            </div>

            <div class="settings-grid">
                <!-- Telegram -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">📱 Telegram</h3>
                        <button class="btn btn-xs btn-outline" onclick="SettingsPage.testTelegram()">🔧 Test kết nối</button>
                    </div>
                    <div class="card-body">
                        <div class="form-group">
                            <label>Bot Token</label>
                            <input type="password" id="set_telegram_bot_token" class="form-input" value="${settings.telegram_bot_token || ''}" placeholder="123456:ABC-DEF...">
                        </div>
                        <div class="form-group">
                            <label>Chat ID</label>
                            <input type="text" id="set_telegram_chat_id" class="form-input" value="${settings.telegram_chat_id || ''}" placeholder="-100123456789">
                        </div>
                        <div class="form-group">
                            <label>Giờ gửi báo cáo hàng ngày</label>
                            <input type="number" id="set_daily_report_hour" class="form-input" value="${settings.daily_report_hour || '8'}" min="0" max="23">
                        </div>
                    </div>
                </div>

                <!-- Viral Thresholds -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🔥 Ngưỡng Viral</h3>
                    </div>
                    <div class="card-body">
                        <div class="form-group">
                            <label>🟡 Cắn View (views)</label>
                            <input type="number" id="set_viral_threshold_catching" class="form-input" value="${settings.viral_threshold_catching || '10000'}">
                        </div>
                        <div class="form-group">
                            <label>🟠 Viral (views)</label>
                            <input type="number" id="set_viral_threshold_viral" class="form-input" value="${settings.viral_threshold_viral || '100000'}">
                        </div>
                        <div class="form-group">
                            <label>🔴 Siêu Viral (views)</label>
                            <input type="number" id="set_viral_threshold_super_viral" class="form-input" value="${settings.viral_threshold_super_viral || '1000000'}">
                        </div>
                        <div class="form-group">
                            <label>Tần suất kiểm tra (phút)</label>
                            <input type="number" id="set_monitor_interval_minutes" class="form-input" value="${settings.monitor_interval_minutes || '30'}" min="5" max="120">
                        </div>
                    </div>
                </div>

                <!-- Auto Comment -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">💬 Auto Comment</h3>
                    </div>
                    <div class="card-body">
                        <div class="form-group">
                            <label class="toggle-label">
                                <input type="checkbox" id="set_auto_comment_enabled" ${settings.auto_comment_enabled === 'true' ? 'checked' : ''}>
                                <span>Bật tự động comment</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label>Delay tối thiểu (giây)</label>
                            <input type="number" id="set_auto_comment_delay_min" class="form-input" value="${settings.auto_comment_delay_min || '30'}" min="10">
                        </div>
                        <div class="form-group">
                            <label>Delay tối đa (giây)</label>
                            <input type="number" id="set_auto_comment_delay_max" class="form-input" value="${settings.auto_comment_delay_max || '120'}" min="30">
                        </div>
                    </div>
                </div>

                <!-- OpenAI -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🤖 AI Caption (OpenAI)</h3>
                        <button class="btn btn-xs btn-outline" onclick="SettingsPage.testOpenAI()">🔧 Test API</button>
                    </div>
                    <div class="card-body">
                        <div class="form-group">
                            <label>API Key</label>
                            <input type="password" id="set_openai_api_key" class="form-input" value="${settings.openai_api_key || ''}" placeholder="sk-...">
                        </div>
                        <p class="text-muted" style="font-size: 12px; margin-top: 8px;">
                            🧠 Dùng GPT-4o-mini để viết lại caption viral + hashtag thông minh. Model rẻ nhất (~$0.15/1M tokens).
                        </p>
                    </div>
                </div>

                <!-- Auto-Sync -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🔄 Auto-Sync Pages</h3>
                        <button class="btn btn-xs btn-outline" onclick="SettingsPage.syncNow()">⚡ Sync ngay</button>
                    </div>
                    <div class="card-body">
                        <div class="form-group">
                            <label>Tần suất sync (phút)</label>
                            <select id="set_sync_interval_minutes" class="form-input">
                                <option value="30" ${settings.sync_interval_minutes === '30' ? 'selected' : ''}>30 phút</option>
                                <option value="60" ${(settings.sync_interval_minutes || '60') === '60' ? 'selected' : ''}>1 giờ</option>
                                <option value="120" ${settings.sync_interval_minutes === '120' ? 'selected' : ''}>2 giờ</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Cảnh báo khi followers tăng (người/lần sync)</label>
                            <input type="number" id="set_growth_alert_followers_threshold" class="form-input" value="${settings.growth_alert_followers_threshold || '50'}" min="10">
                        </div>
                        <p class="text-muted" style="font-size: 12px; margin-top: 8px;">
                            ⏱️ Hệ thống tự động đồng bộ followers, views, và phát hiện video tăng tốc. Alert gửi về Telegram.
                        </p>
                    </div>
                </div>

                <!-- Storage -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">💾 Lưu Trữ</h3>
                        <button class="btn btn-xs btn-danger-outline" onclick="SettingsPage.cleanup()">🧹 Dọn dẹp</button>
                    </div>
                    <div class="card-body">
                        <div class="storage-stats">
                            <div class="storage-stat">
                                <span>Video gốc:</span>
                                <strong>${storage.downloads_size_mb || 0} MB</strong>
                            </div>
                            <div class="storage-stat">
                                <span>Biến thể:</span>
                                <strong>${storage.variants_size_mb || 0} MB</strong>
                            </div>
                            <div class="storage-stat total">
                                <span>Tổng:</span>
                                <strong>${storage.total_size_gb || 0} GB</strong>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="toggle-label">
                                <input type="checkbox" id="set_auto_cleanup_source_after_spoof" ${settings.auto_cleanup_source_after_spoof !== 'false' ? 'checked' : ''}>
                                <span>Xóa video gốc sau khi tạo biến thể</span>
                            </label>
                        </div>
                        <div class="form-group">
                            <label>Tự động xóa biến thể sau (ngày)</label>
                            <input type="number" id="set_auto_cleanup_variant_days" class="form-input" value="${settings.auto_cleanup_variant_days || '7'}" min="1">
                        </div>
                    </div>
                </div>
            </div>

            <div class="settings-actions">
                <button class="btn btn-primary btn-lg" onclick="SettingsPage.save()">💾 Lưu tất cả cài đặt</button>
            </div>
        `;
    },

    async save() {
        const settings = {};
        document.querySelectorAll('[id^="set_"]').forEach(el => {
            const key = el.id.replace('set_', '');
            if (el.type === 'checkbox') {
                settings[key] = el.checked ? 'true' : 'false';
            } else {
                settings[key] = el.value;
            }
        });

        try {
            await API.put('/api/settings', { settings });
            Toast.success('Đã lưu cài đặt!');
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    async testTelegram() {
        try {
            const res = await API.post('/api/settings/telegram/test');
            if (res.ok) {
                Toast.success(`Kết nối thành công! Bot: @${res.bot_username}`);
            } else {
                Toast.error('Kết nối thất bại: ' + (res.error || 'Unknown'));
            }
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    async cleanup() {
        if (!confirm('Are you sure you want to clean up old video files? This will:\n\n• Delete source videos already processed\n• Delete old posted variants\n• Remove orphaned files not tracked in database\n• Clean empty directories')) return;
        
        const btn = document.querySelector('[onclick*="cleanup"]');
        const originalText = btn?.textContent || '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Cleaning...';
        }
        
        try {
            const res = await API.post('/api/settings/storage/cleanup');
            const total = (res.source_deleted || 0) + (res.variants_deleted || 0) + (res.orphaned_deleted || 0);
            
            if (total > 0 || res.space_freed_mb > 0) {
                Toast.success(`✅ Cleaned up ${res.space_freed_mb} MB!\n${res.source_deleted || 0} source, ${res.variants_deleted || 0} variants, ${res.orphaned_deleted || 0} orphaned files removed.`);
            } else {
                Toast.info('✨ Storage is already clean — no files to remove.');
            }
            App.refreshPage();
        } catch (e) {
            Toast.error('Cleanup error: ' + e.message);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
    },

    async testOpenAI() {
        const key = document.getElementById('set_openai_api_key')?.value?.trim();
        if (!key) {
            Toast.error('Nhập API Key trước khi test');
            return;
        }
        try {
            // Save key to DB first
            await API.put('/api/settings', { settings: { openai_api_key: key } });
            Toast.info('⏳ Đang test kết nối OpenAI...');
            const res = await API.post('/api/ai/rewrite-caption', {
                original_caption: 'Video hay quá, chia sẻ ngay nào!',
                page_name: 'Test Page',
            });
            if (res.status === 'ok') {
                Toast.success(`✅ OpenAI hoạt động! (${res.tokens_used} tokens)`);
            } else {
                Toast.error('❌ ' + (res.error || 'Lỗi không xác định'));
            }
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    async syncNow() {
        Toast.info('⏳ Đang sync dữ liệu tất cả pages...');
        try {
            const res = await API.post('/api/pages/sync');
            const stats = res.stats || {};
            Toast.success(`✅ Sync xong! ${stats.synced || 0} pages, ${stats.alerts_sent || 0} alerts gửi`);
        } catch (e) {
            Toast.error('Lỗi sync: ' + e.message);
        }
    },

    init() {},
};
