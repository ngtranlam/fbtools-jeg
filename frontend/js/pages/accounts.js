// Quản Lý Tài Khoản — Multi-Platform (Facebook, Pinterest, YouTube)
const AccountsPage = {
    activeTab: 'facebook',
    channels: [],
    loadError: '',

    // Required Facebook permissions for MocLan Hub
    FB_PERMISSIONS: [
        'pages_show_list',
        'pages_read_engagement',
        'pages_manage_posts',
        'pages_read_user_content',
        'pages_manage_engagement',
        'publish_video',
        'read_insights',
    ],

    PLATFORM_CONFIG: {
        facebook: {
            icon: '📘', label: 'Facebook', color: '#1877F2',
            desc: 'Quản lý Fanpage, đăng Reels & theo dõi hiệu suất',
        },
        pinterest: {
            icon: '📌', label: 'Pinterest', color: '#E60023',
            desc: 'Đăng Video Pin lên boards, bán hàng affiliate',
        },
        youtube: {
            icon: '▶️', label: 'YouTube', color: '#FF0000',
            desc: 'Upload Shorts & video lên kênh YouTube',
        },
    },

    async render() {
        // Trước đây hai lệnh gọi này nuốt lỗi rồi hiện "Chưa có tài khoản" —
        // một câu SAI SỰ THẬT. Máy chủ hỏng, chưa khởi động lại, hay lệch phiên
        // bản đều ra cùng màn hình trống y hệt lúc chưa thêm tài khoản nào, nên
        // không ai lần ra được nguyên nhân. Nay hỏng thì phải nói là hỏng.
        this.loadError = '';

        let accounts = [];
        try {
            const res = await API.get('/api/accounts');
            accounts = res.accounts || [];
        } catch (e) {
            this.loadError = e?.message || String(e);
        }

        try {
            const res = await API.get('/api/channels');
            this.channels = res.channels || [];
        } catch (e) {
            this.channels = [];
            if (!this.loadError) this.loadError = e?.message || String(e);
        }

        const fbCount = accounts.length;
        const pinCount = this.channels.filter(c => c.platform === 'pinterest').length;
        const ytCount = this.channels.filter(c => c.platform === 'youtube').length;

        return `
            <div class="page-header">
                <h1 class="page-title">👤 Quản Lý Tài Khoản</h1>
                <p class="page-subtitle">Kết nối & quản lý tài khoản đa nền tảng</p>
            </div>

            ${this._renderLoadError()}

            <div class="acct-platform-tabs" id="acctPlatformTabs">
                ${this._renderTab('facebook', fbCount)}
                ${this._renderTab('pinterest', pinCount)}
                ${this._renderTab('youtube', ytCount)}
            </div>

            <div class="acct-tab-content" id="acctTabContent">
                ${this._renderTabContent('facebook', accounts)}
            </div>
        `;
    },

    /** Dải cảnh báo khi không đọc được danh sách tài khoản từ máy chủ. */
    _renderLoadError() {
        if (!this.loadError) return '';
        const stale = /not found|404/i.test(this.loadError);
        return `
            <div class="load-error">
                <strong>Không đọc được danh sách tài khoản từ máy chủ.</strong>
                <span class="load-error-detail">${this._esc(this.loadError)}</span>
                <div class="load-error-fix">
                    ${stale
                        ? `Thường là do <strong>đã cập nhật mã nguồn nhưng chưa khởi động lại tool</strong>.
                           Đóng hẳn cửa sổ đen (Terminal) rồi mở lại bằng
                           <strong>start.bat</strong> (Windows) hoặc <strong>start.command</strong> (Mac).`
                        : `Thử theo thứ tự: tải lại trang bằng <strong>Ctrl + Shift + R</strong>
                           (Mac: <strong>Command + Shift + R</strong>) → đóng hẳn tool rồi mở lại →
                           nếu vẫn lỗi thì báo Admin kèm dòng chữ đỏ ở trên.`}
                </div>
                <button class="btn btn-sm btn-outline" onclick="App.refreshPage()">Thử lại</button>
            </div>
        `;
    },

    _renderTab(platform, count) {
        const cfg = this.PLATFORM_CONFIG[platform];
        const active = this.activeTab === platform ? 'active' : '';
        return `
            <button class="acct-tab ${active}" data-platform="${platform}"
                    onclick="AccountsPage.switchTab('${platform}')"
                    style="--platform-color: ${cfg.color}">
                <span class="acct-tab-icon">${cfg.icon}</span>
                <span class="acct-tab-label">${cfg.label}</span>
                <span class="acct-tab-count">${count}</span>
            </button>
        `;
    },

    async switchTab(platform) {
        this.activeTab = platform;
        // Update tab active states
        document.querySelectorAll('.acct-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.platform === platform);
        });

        const container = document.getElementById('acctTabContent');
        if (!container) return;
        container.style.opacity = '0';
        container.style.transform = 'translateY(8px)';

        await new Promise(r => setTimeout(r, 150));

        if (platform === 'facebook') {
            let accounts = [];
            try {
                const res = await API.get('/api/accounts');
                accounts = res.accounts || [];
            } catch (e) { /* empty */ }
            container.innerHTML = this._renderTabContent('facebook', accounts);
        } else {
            const items = this.channels.filter(c => c.platform === platform);
            container.innerHTML = this._renderTabContent(platform, items);
        }

        requestAnimationFrame(() => {
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        });
    },

    _renderTabContent(platform, items) {
        const cfg = this.PLATFORM_CONFIG[platform];
        const addLabel = platform === 'facebook' ? 'Thêm tài khoản Facebook' :
            platform === 'pinterest' ? 'Thêm tài khoản Pinterest' : 'Thêm kênh YouTube';

        const header = `
            <div class="acct-content-header">
                <div class="acct-content-info">
                    <span class="acct-content-icon" style="background: ${cfg.color}22; color: ${cfg.color}">${cfg.icon}</span>
                    <div>
                        <h3>${cfg.label}</h3>
                        <p>${cfg.desc}</p>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="AccountsPage.showAddModal('${platform}')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    ${addLabel}
                </button>
            </div>
        `;

        // Không tải được dữ liệu thì dải cảnh báo đỏ ở trên đã nói rồi — thêm câu
        // "Chưa có tài khoản" ở đây nữa là khẳng định một điều không đúng.
        if (!items.length && this.loadError && platform === 'facebook') return header;

        if (!items.length) {
            return header + `
                <div class="acct-empty">
                    <div class="acct-empty-icon" style="background: ${cfg.color}15; color: ${cfg.color}">${cfg.icon}</div>
                    <div class="acct-empty-title">Chưa có tài khoản ${cfg.label}</div>
                    <div class="acct-empty-desc">Nhấn nút phía trên để thêm tài khoản ${cfg.label} đầu tiên</div>
                </div>
            `;
        }

        const cards = items.map(item =>
            platform === 'facebook' ? this._renderFacebookCard(item) : this._renderChannelCard(item)
        ).join('');

        return header + `<div class="acct-cards-grid">${cards}</div>`;
    },

    _renderFacebookCard(a) {
        const statusClass = a.status === 'active' ? 'status-active' : 'status-error';
        const statusText = a.status === 'active' ? 'Hoạt động' : 'Lỗi';
        return `
            <div class="acct-card" style="--platform-color: #1877F2">
                <div class="acct-card-top">
                    <div class="acct-card-avatar" style="background: #1877F222; color: #1877F2">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    </div>
                    <div class="acct-card-info">
                        <div class="acct-card-name">${a.name}</div>
                        <div class="acct-card-id">
                            FB ID: ${a.fb_user_id}
                            ${a.token_type === 'system'
                                ? '<span class="token-tag">System User</span>' : ''}
                        </div>
                    </div>
                    <span class="status-pill ${statusClass}">${statusText}</span>
                </div>
                <div class="acct-card-stats">
                    <div class="acct-stat">
                        <span class="acct-stat-value">${a.pages_count || 0}</span>
                        <span class="acct-stat-label">Pages</span>
                    </div>
                    <div class="acct-stat">
                        <span class="acct-stat-value">${
                            a.token_type === 'system' ? 'Vĩnh viễn'
                            : a.token_expires_at
                                ? new Date(a.token_expires_at).toLocaleDateString('vi-VN')
                                : 'N/A'}</span>
                        <span class="acct-stat-label">Token hết hạn</span>
                    </div>
                </div>
                <div class="acct-card-actions">
                    <button class="btn btn-sm btn-outline" onclick="AccountsPage.checkToken(${a.id})">Kiểm tra token</button>
                    <button class="btn btn-sm btn-accent" onclick="AccountsPage.showUpdateTokenModal(${a.id}, '${a.token_type || 'user'}')">Cập nhật token</button>
                    <button class="btn btn-sm btn-outline" onclick="AccountsPage.discoverPages(${a.id})">🔍 Tìm Pages</button>
                    <button class="btn btn-sm btn-danger-outline" onclick="AccountsPage.deleteAccount(${a.id})">🗑️ Xóa</button>
                </div>
            </div>
        `;
    },

    _renderChannelCard(ch) {
        const cfg = this.PLATFORM_CONFIG[ch.platform];
        const hasCredentials = ch.has_credentials;
        const statusClass = ch.status === 'active' ? 'status-active' : 'status-error';
        const statusText = ch.status === 'active' ? 'Hoạt động' : 'Lỗi';

        return `
            <div class="acct-card" style="--platform-color: ${cfg.color}">
                <div class="acct-card-top">
                    <div class="acct-card-avatar" style="background: ${cfg.color}22; color: ${cfg.color}">
                        <span style="font-size:24px">${cfg.icon}</span>
                    </div>
                    <div class="acct-card-info">
                        <div class="acct-card-name">${ch.channel_name}</div>
                        <div class="acct-card-id">${ch.channel_id || ch.platform}</div>
                    </div>
                    <span class="status-pill ${statusClass}">${statusText}</span>
                </div>
                <div class="acct-card-stats">
                    <div class="acct-stat">
                        <span class="acct-stat-value">${hasCredentials ? '✅' : '❌'}</span>
                        <span class="acct-stat-label">Credentials</span>
                    </div>
                    <div class="acct-stat">
                        <span class="acct-stat-value">${ch.followers_count || 0}</span>
                        <span class="acct-stat-label">Followers</span>
                    </div>
                </div>
                <div class="acct-card-actions">
                    <button class="btn btn-sm btn-outline" onclick="AccountsPage.validateChannel(${ch.id})">🔧 Test API</button>
                    <button class="btn btn-sm btn-outline" onclick="AccountsPage.editChannel(${ch.id})">✏️ Sửa</button>
                    <button class="btn btn-sm btn-danger-outline" onclick="AccountsPage.deleteChannel(${ch.id})">🗑️ Xóa</button>
                </div>
            </div>
        `;
    },

    // ━━━ Add Modal per platform ━━━

    showAddModal(platform) {
        if (platform === 'facebook') return this._showFacebookModal();
        if (platform === 'pinterest') return this._showPinterestModal();
        if (platform === 'youtube') return this._showYouTubeModal();
    },

    //: Hai kiểu token dùng được. Token System User của Business Manager không có
    //: hạn nên đỡ hẳn việc cứ 60 ngày lại phải đi gia hạn cho từng tài khoản.
    TOKEN_KINDS: {
        system: {
            label: 'Người dùng hệ thống (System User)',
            note: 'Token VĨNH VIỄN — khuyên dùng',
        },
        user: {
            label: 'Tài khoản cá nhân (Graph API Explorer)',
            note: 'Token 60 ngày, hết hạn phải lấy lại',
        },
    },

    _tokenKindPicker(current, onpick) {
        return `
            <div class="token-kind">
                ${Object.entries(this.TOKEN_KINDS).map(([id, k]) => `
                    <label class="token-kind-opt ${id === current ? 'active' : ''}">
                        <input type="radio" name="tokenKind" value="${id}"
                               ${id === current ? 'checked' : ''}
                               onchange="${onpick}('${id}')">
                        <span>
                            <strong>${k.label}</strong>
                            <small>${k.note}</small>
                        </span>
                    </label>
                `).join('')}
            </div>
        `;
    },

    /** Đổi kiểu token nhưng giữ lại những gì đã gõ. */
    switchTokenKind(kind) {
        const v = id => document.getElementById(id)?.value || '';
        this._fbDraft = {
            name: v('accName'), app_id: v('accAppId'),
            app_secret: v('accAppSecret'), token: v('accToken'),
        };
        this._showFacebookModal(kind);
    },

    _sysUserGuide() {
        return `
            <div class="token-guide">
                <div class="token-guide-title">📋 Lấy token System User (dùng được vĩnh viễn)</div>
                <ol class="token-guide-steps">
                    <li>Vào <strong>business.facebook.com</strong> → <strong>Cài đặt doanh nghiệp</strong></li>
                    <li>Mục <strong>Người dùng → Người dùng hệ thống</strong> → bấm <strong>Thêm</strong>,
                        đặt tên và chọn vai trò <strong>Quản trị viên</strong></li>
                    <li>Bấm <strong>Thêm tài sản</strong> → chọn <strong>Trang</strong> →
                        tích các Fanpage cần quản lý → bật <strong>Toàn quyền</strong></li>
                    <li>Bấm <strong>Tạo mã truy cập mới</strong>:
                        <ul>
                            <li>Chọn <strong>App</strong> của anh/chị</li>
                            <li><strong>Token Expiration: Never</strong> — chỗ quan trọng nhất,
                                chọn sai là token vẫn hết hạn</li>
                            <li>Tích đủ các quyền:
                                <span class="token-scopes">pages_show_list · pages_read_engagement ·
                                pages_manage_posts · pages_read_user_content ·
                                pages_manage_engagement · publish_video · read_insights ·
                                business_management</span></li>
                        </ul>
                    </li>
                    <li>Copy token rồi dán xuống ô bên dưới.
                        <strong>Token chỉ hiện đúng một lần</strong> — đóng cửa sổ đi là mất,
                        phải tạo lại.</li>
                </ol>
                <div class="token-guide-warn">
                    App phải nằm trong Business thì mới chọn được ở bước 4 —
                    thêm ở <strong>Cài đặt doanh nghiệp → Tài khoản → Ứng dụng</strong>.
                </div>
                <button type="button" class="btn btn-primary btn-sm"
                        onclick="window.open('https://business.facebook.com/settings/system-users','_blank')">
                    Mở Business Settings
                </button>
            </div>
        `;
    },

    _userTokenGuide() {
        return `
            <div class="token-guide">
                <div class="token-guide-title">📋 Lấy User Access Token</div>
                <ol class="token-guide-steps">
                    <li>Bấm nút <strong>Mở Graph API Explorer</strong> bên dưới</li>
                    <li>Chọn <strong>Facebook App</strong> của anh/chị ở góc trên phải</li>
                    <li>Bấm <strong>Add a Permission</strong> rồi tích:
                        <span class="token-scopes">pages_show_list · pages_read_engagement ·
                        pages_manage_posts · pages_read_user_content ·
                        pages_manage_engagement · publish_video · read_insights</span></li>
                    <li>Bấm <strong>Generate Access Token</strong> → đăng nhập → cho phép tất cả</li>
                    <li>Copy token <strong>EAA...</strong> ở ô "Access Token" rồi dán xuống dưới</li>
                </ol>
                <div class="token-guide-warn">
                    Token này chỉ sống <strong>1–2 tiếng</strong>. Tool sẽ đổi sang bản
                    <strong>60 ngày</strong>, nhưng bắt buộc phải nhập đúng App ID và App Secret.
                </div>
                <button type="button" class="btn btn-primary btn-sm"
                        onclick="window.open('https://developers.facebook.com/tools/explorer/','_blank')">
                    🔑 Mở Graph API Explorer
                </button>
            </div>
        `;
    },

    _showFacebookModal(kind = 'system') {
        const d = this._fbDraft || {};
        this._fbDraft = null;
        const sys = kind === 'system';
        const req = '<span style="color:var(--error)">*</span>';

        Modal.open(`
            <h3>📘 Thêm Tài Khoản Facebook</h3>
            <form id="addAccountForm" onsubmit="AccountsPage.submitAdd(event)">
                <input type="hidden" id="accTokenKind" value="${kind}">

                ${this._tokenKindPicker(kind, 'AccountsPage.switchTokenKind')}

                <div class="form-group">
                    <label>Tên tài khoản ${req}</label>
                    <input type="text" id="accName" class="form-input" required
                           value="${this._esc(d.name || '')}"
                           placeholder="${sys ? 'VD: System User - Team A' : 'VD: Anh Minh - TK1'}">
                </div>

                ${sys ? this._sysUserGuide() : this._userTokenGuide()}

                <div class="form-group">
                    <label>${sys ? 'System User Access Token' : 'User Access Token'} ${req}</label>
                    <textarea id="accToken" class="form-input" rows="3" required
                              placeholder="Dán token EAA... tại đây">${this._esc(d.token || '')}</textarea>
                    <small class="form-hint">
                        ${sys
                            ? 'Token System User đặt <strong>Never</strong> thì dùng mãi, không phải gia hạn.'
                            : 'Token ngắn hạn sẽ tự đổi sang <strong>token 60 ngày</strong>.'}
                    </small>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>App ID ${sys ? '' : req}</label>
                        <input type="text" id="accAppId" class="form-input" ${sys ? '' : 'required'}
                               value="${this._esc(d.app_id || '')}"
                               placeholder="VD: 123456789012345">
                    </div>
                    <div class="form-group">
                        <label>App Secret ${sys ? '' : req}</label>
                        <input type="password" id="accAppSecret" class="form-input" ${sys ? '' : 'required'}
                               value="${this._esc(d.app_secret || '')}"
                               placeholder="Facebook App Secret">
                    </div>
                </div>
                <small class="form-hint" style="display:block;margin-top:-8px">
                    developers.facebook.com → App → Settings → Basic.
                    ${sys
                        ? 'Với token System User thì <strong>không bắt buộc</strong> — nhập vào chỉ để tool kiểm tra được hạn và quyền của token.'
                        : '<strong>Bắt buộc</strong> — thiếu là token chỉ sống 1–2 tiếng.'}
                </small>

                <div class="form-actions">
                    <button type="button" class="btn btn-outline" onclick="Modal.close()">Hủy</button>
                    <button type="submit" class="btn btn-primary" id="addAccBtn">
                        ${sys ? 'Xác thực & Quét Fanpage' : '🔄 Xác thực & Tạo Long-Lived Token'}
                    </button>
                </div>
            </form>
        `);
    },

    _showPinterestModal() {
        Modal.open(`
            <h3>📌 Thêm Tài Khoản Pinterest</h3>
            <form id="addPinterestForm" onsubmit="AccountsPage.submitPinterest(event)">

                <div class="form-group">
                    <label>Tên hiển thị <span style="color:var(--error)">*</span></label>
                    <input type="text" id="pinName" class="form-input" placeholder="VD: Pinterest - Shop ABC" required>
                </div>

                <div style="background:linear-gradient(135deg, rgba(230,0,35,0.08), rgba(230,0,35,0.04));border:1px solid #E6002344;border-radius:12px;padding:16px;margin:16px 0">
                    <div style="font-size:14px;font-weight:700;color:#E60023;margin-bottom:10px">🤖 Đăng nhập qua Browser tự động</div>
                    <div style="font-size:12px;color:var(--text-secondary);line-height:1.8;margin-bottom:12px">
                        <strong style="color:var(--text-primary)">Bước 1:</strong> Nhập tên hiển thị ở trên<br>
                        <strong style="color:var(--text-primary)">Bước 2:</strong> Click <strong style="color:#E60023">"Thêm & Đăng nhập"</strong> bên dưới<br>
                        <strong style="color:var(--text-primary)">Bước 3:</strong> Browser sẽ mở ra → <strong>Đăng nhập Pinterest</strong> bình thường<br>
                        <strong style="color:var(--text-primary)">Bước 4:</strong> Sau khi login xong → hệ thống tự lưu session<br>
                        <span style="display:inline-block;margin-top:8px;padding:6px 10px;background:rgba(0,212,170,0.15);border-radius:6px;font-size:11px;color:var(--accent)">
                            ✅ Không cần API Token &nbsp;•&nbsp; ✅ Không cần Developer App &nbsp;•&nbsp; ✅ Tự động lưu cookie
                        </span>
                    </div>
                </div>

                <div class="form-actions">
                    <button type="button" class="btn btn-outline" onclick="Modal.close()">Hủy</button>
                    <button type="submit" class="btn" id="addPinBtn" style="background:#E60023;color:white;border:none">
                        📌 Thêm & Đăng nhập Pinterest
                    </button>
                </div>
            </form>
        `);
    },

    _showYouTubeModal() {
        Modal.open(`
            <h3>▶️ Thêm Kênh YouTube</h3>
            <form id="addYouTubeForm" onsubmit="AccountsPage.submitYouTube(event)">

                <div class="form-group">
                    <label>Tên kênh <span style="color:var(--error)">*</span></label>
                    <input type="text" id="ytName" class="form-input" placeholder="VD: Kênh Viral Shorts" required>
                </div>

                <div class="form-group">
                    <label>Channel ID</label>
                    <input type="text" id="ytChannelId" class="form-input" placeholder="VD: UCxxxxxxxxxxxxxx">
                    <small class="form-hint">Youtube Studio → Settings → Advanced → Channel ID</small>
                </div>

                <div style="background:linear-gradient(135deg, rgba(255,0,0,0.08), rgba(255,0,0,0.04));border:1px solid #FF000044;border-radius:12px;padding:16px;margin:16px 0">
                    <div style="font-size:14px;font-weight:700;color:#FF0000;margin-bottom:10px">📋 Hướng dẫn lấy YouTube API Credentials</div>
                    <div style="font-size:12px;color:var(--text-secondary);line-height:1.8;margin-bottom:12px">
                        <strong style="color:var(--text-primary)">Bước 1:</strong> Truy cập <strong>console.cloud.google.com</strong><br>
                        <strong style="color:var(--text-primary)">Bước 2:</strong> Tạo Project → Bật <strong>YouTube Data API v3</strong><br>
                        <strong style="color:var(--text-primary)">Bước 3:</strong> Vào <strong>Credentials</strong> → Tạo <strong>OAuth 2.0 Client ID</strong><br>
                        <strong style="color:var(--text-primary)">Bước 4:</strong> Copy <strong>Client ID</strong> và <strong>Client Secret</strong><br>
                        <strong style="color:var(--text-primary)">Bước 5:</strong> Dùng OAuth Playground để lấy <strong>Refresh Token</strong> với scope: <code>https://www.googleapis.com/auth/youtube.upload</code>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap">
                        <button type="button" class="btn" onclick="window.open('https://console.cloud.google.com/apis/credentials','_blank')" style="font-size:13px;padding:8px 16px;background:#FF0000;color:white;border:none;border-radius:8px">
                            ☁️ Google Cloud Console
                        </button>
                        <button type="button" class="btn btn-outline" onclick="window.open('https://developers.google.com/oauthplayground/','_blank')" style="font-size:13px;padding:8px 16px">
                            🔑 OAuth Playground
                        </button>
                    </div>
                </div>

                <div class="form-group">
                    <label>Client ID <span style="color:var(--error)">*</span></label>
                    <input type="text" id="ytClientId" class="form-input" placeholder="xxxxxxxxx.apps.googleusercontent.com" required>
                </div>

                <div class="form-group">
                    <label>Client Secret <span style="color:var(--error)">*</span></label>
                    <input type="password" id="ytClientSecret" class="form-input" placeholder="Google OAuth Client Secret" required>
                </div>

                <div class="form-group">
                    <label>Refresh Token <span style="color:var(--error)">*</span></label>
                    <textarea id="ytRefreshToken" class="form-input" rows="3" placeholder="Paste Refresh Token từ OAuth Playground..." required></textarea>
                    <small class="form-hint">Refresh Token cho phép hệ thống tự động lấy Access Token mới</small>
                </div>

                <div class="form-actions">
                    <button type="button" class="btn btn-outline" onclick="Modal.close()">Hủy</button>
                    <button type="submit" class="btn" id="addYtBtn" style="background:#FF0000;color:white;border:none">
                        ▶️ Thêm kênh YouTube
                    </button>
                </div>
            </form>
        `);
    },

    // ━━━ Submit handlers ━━━

    async submitAdd(e) {
        e.preventDefault();
        const btn = document.getElementById('addAccBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-sm"></span> Đang xác thực & đổi token...';

        try {
            const res = await API.post('/api/accounts', {
                name: document.getElementById('accName').value,
                access_token: document.getElementById('accToken').value.trim(),
                app_id: document.getElementById('accAppId').value.trim(),
                app_secret: document.getElementById('accAppSecret').value.trim(),
                token_type: document.getElementById('accTokenKind')?.value || 'user',
            });

            const account = res.account || {};
            let msg = `✅ Thêm "${account.name || ''}" thành công!`;
            if (account.token_type === 'system' && account.never_expires) {
                msg += ' Token System User — không bao giờ hết hạn.';
            } else if (account.token_expires_at) {
                const expiry = new Date(account.token_expires_at).toLocaleDateString('vi-VN');
                msg += ` Token hết hạn: ${expiry}`;
            }
            Toast.success(msg);
            Modal.close();

            // Cảnh báo (token có hạn dù khai là System User...) phải đập vào mắt,
            // không được trôi mất cùng toast sau vài giây.
            if (account.warning) {
                Modal.open(`
                    <h3 class="modal-title">⚠️ Lưu ý về token vừa thêm</h3>
                    <p style="line-height:1.7;color:var(--text-secondary)">${this._esc(account.warning)}</p>
                    <div class="modal-actions">
                        <button class="btn btn-primary" onclick="Modal.close(); App.refreshPage()">Đã hiểu</button>
                    </div>
                `);
                return;
            }
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + (e.message || 'Token không hợp lệ hoặc App ID/Secret sai'));
            btn.disabled = false;
            btn.innerHTML = (document.getElementById('accTokenKind')?.value === 'system')
                ? 'Xác thực & Quét Fanpage'
                : '🔄 Xác thực & Tạo Long-Lived Token';
        }
    },

    async submitPinterest(e) {
        e.preventDefault();
        const btn = document.getElementById('addPinBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-sm"></span> Đang thêm...';

        try {
            const credentials = {
                access_token: document.getElementById('pinAccessToken').value.trim(),
            };
            const refreshToken = document.getElementById('pinRefreshToken').value.trim();
            if (refreshToken) credentials.refresh_token = refreshToken;

            const extra_data = {};
            const boardId = document.getElementById('pinBoardId').value.trim();
            if (boardId) extra_data.default_board_id = boardId;

            await API.post('/api/channels', {
                platform: 'pinterest',
                channel_name: document.getElementById('pinName').value.trim(),
                channel_id: document.getElementById('pinChannelId').value.trim(),
                credentials,
                extra_data,
            });

            Toast.success('✅ Đã thêm tài khoản Pinterest!');
            Modal.close();
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + (e.message || 'Không thể thêm tài khoản'));
            btn.disabled = false;
            btn.innerHTML = '📌 Thêm tài khoản Pinterest';
        }
    },

    async submitYouTube(e) {
        e.preventDefault();
        const btn = document.getElementById('addYtBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-sm"></span> Đang thêm...';

        try {
            await API.post('/api/channels', {
                platform: 'youtube',
                channel_name: document.getElementById('ytName').value.trim(),
                channel_id: document.getElementById('ytChannelId').value.trim(),
                credentials: {
                    client_id: document.getElementById('ytClientId').value.trim(),
                    client_secret: document.getElementById('ytClientSecret').value.trim(),
                    refresh_token: document.getElementById('ytRefreshToken').value.trim(),
                },
            });

            Toast.success('✅ Đã thêm kênh YouTube!');
            Modal.close();
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + (e.message || 'Không thể thêm kênh'));
            btn.disabled = false;
            btn.innerHTML = '▶️ Thêm kênh YouTube';
        }
    },

    // ━━━ Channel actions ━━━

    async validateChannel(channelId) {
        Toast.info('⏳ Đang kiểm tra kết nối...');
        try {
            const res = await API.post(`/api/channels/${channelId}/validate`);
            if (res.valid) {
                Toast.success('✅ API hoạt động tốt!');
            } else {
                Toast.error('❌ Lỗi: ' + (res.error || 'Credentials không hợp lệ'));
            }
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    editChannel(channelId) {
        const ch = this.channels.find(c => c.id === channelId);
        if (!ch) return;

        Modal.open(`
            <h3>✏️ Sửa ${this.PLATFORM_CONFIG[ch.platform]?.label || ch.platform}: ${ch.channel_name}</h3>
            <form onsubmit="AccountsPage._submitEditChannel(event, ${channelId})">
                <div class="form-group">
                    <label>Tên hiển thị</label>
                    <input type="text" id="editChName" class="form-input" value="${ch.channel_name}">
                </div>
                <div class="form-group">
                    <label>Access Token mới (để trống nếu không đổi)</label>
                    <textarea id="editChToken" class="form-input" rows="3" placeholder="Paste token mới nếu muốn đổi..."></textarea>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-outline" onclick="Modal.close()">Hủy</button>
                    <button type="submit" class="btn btn-primary">💾 Cập nhật</button>
                </div>
            </form>
        `);
    },

    async _submitEditChannel(e, channelId) {
        e.preventDefault();
        const updates = {};
        const name = document.getElementById('editChName')?.value?.trim();
        if (name) updates.channel_name = name;

        const token = document.getElementById('editChToken')?.value?.trim();
        if (token) updates.credentials = { access_token: token };

        try {
            await API.put(`/api/channels/${channelId}`, updates);
            Toast.success('✅ Đã cập nhật!');
            Modal.close();
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    deleteChannel(channelId) {
        const ch = this.channels.find(c => c.id === channelId);
        const name = ch?.channel_name || `#${channelId}`;
        Modal.open(`
            <div style="text-align:center;padding:20px 0">
                <div style="font-size:48px;margin-bottom:16px">⚠️</div>
                <h3 style="margin-bottom:8px">Xóa tài khoản "${name}"?</h3>
                <p style="color:var(--text-secondary);margin-bottom:24px">
                    Hành động này không thể hoàn tác.
                </p>
                <div style="display:flex;gap:12px;justify-content:center">
                    <button class="btn btn-outline" onclick="Modal.close()" style="min-width:100px">Hủy</button>
                    <button class="btn btn-danger" onclick="AccountsPage._confirmDeleteChannel(${channelId})" style="min-width:100px">🗑️ Xóa</button>
                </div>
            </div>
        `);
    },

    async _confirmDeleteChannel(channelId) {
        Modal.close();
        try {
            await API.delete(`/api/channels/${channelId}`);
            Toast.success('Đã xóa!');
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    // ━━━ Facebook legacy ━━━

    async discoverPages(accountId) {
        Toast.info('Đang tìm Fanpage...');
        try {
            const res = await API.post(`/api/accounts/${accountId}/discover-pages`);

            if (!res.count) {
                // 0 Page là lúc cần giải thích nhất — không được để trôi qua
                // bằng một dòng toast rồi thôi.
                Modal.open(`
                    <h3 class="modal-title">Không tìm thấy Fanpage nào</h3>
                    <pre class="fb-error-box">${this._esc(res.hint || 'Không rõ nguyên nhân.')}</pre>
                    <div class="modal-actions">
                        <button class="btn btn-primary" onclick="Modal.close()">Đã hiểu</button>
                    </div>
                `);
                return;
            }

            Toast.success(`Tìm thấy ${res.count} Fanpage!`);
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + (e.message || 'Không thể tìm pages'));
        }
    },

    async checkToken(accountId) {
        Toast.info('Đang hỏi Facebook...');
        try {
            const res = await API.get(`/api/accounts/${accountId}/token-status`);
            if (res.valid) {
                const ngan = res.hours_left !== null && res.hours_left !== undefined
                             && res.hours_left <= 24 && !res.never_expires;
                if (ngan || !res.can_inspect) {
                    // Token sắp chết hoặc không tra được hạn -> hiện bảng để đọc kỹ.
                    // Không tra được hạn KHÁC với sắp hết hạn — nói nhầm là người
                    // dùng đi lấy token mới trong khi token cũ chẳng làm sao cả.
                    const tieuDe = ngan
                        ? 'Token dùng được, nhưng sắp hết hạn'
                        : 'Token dùng được — chưa kiểm chứng được hạn';
                    Modal.open(`
                        <h3 class="modal-title">${tieuDe}</h3>
                        <pre class="fb-error-box">${this._esc(res.message)}</pre>
                        ${this._tokenFacts(res)}
                        <div class="modal-actions">
                            <button class="btn btn-outline" onclick="Modal.close()">Đóng</button>
                            <button class="btn ${ngan ? 'btn-primary' : 'btn-outline'}"
                                    onclick="Modal.close(); AccountsPage.showUpdateTokenModal(${accountId}, '${res.token_type || 'user'}')">
                                Cập nhật token
                            </button>
                        </div>
                    `);
                } else {
                    Toast.success(res.message);
                }
            } else {
                Modal.open(`
                    <h3 class="modal-title">Token không dùng được</h3>
                    <pre class="fb-error-box">${this._esc(res.message)}</pre>
                    ${this._tokenFacts(res)}
                    <div class="modal-actions">
                        <button class="btn btn-outline" onclick="Modal.close()">Đóng</button>
                        <button class="btn btn-primary"
                                onclick="Modal.close(); AccountsPage.showUpdateTokenModal(${accountId})">
                            Cập nhật token ngay
                        </button>
                    </div>
                `);
            }
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    /** Bảng thông tin token lấy thẳng từ Facebook — để biết chắc vấn đề ở đâu. */
    _tokenFacts(res) {
        const rows = [];
        if (res.never_expires) {
            rows.push(['Hạn dùng', 'Không hết hạn']);
        } else if (res.hours_left !== null && res.hours_left !== undefined) {
            const h = res.hours_left;
            rows.push(['Còn lại', h < 48 ? `${h} tiếng` : `${res.days_left} ngày`]);
        } else {
            rows.push(['Hạn dùng', res.token_type === 'system'
                ? 'Không tra được — cần App ID / App Secret để kiểm chứng'
                : 'Không tra được (thiếu App ID / App Secret)']);
        }
        rows.push(['Loại token', res.can_inspect
            ? (res.hours_left !== null && res.hours_left !== undefined && res.hours_left <= 24
                ? 'NGẮN HẠN (1-2 tiếng)' : 'Dài hạn')
            : 'Chưa xác định được']);
        rows.push(['Kiểu token', res.token_type === 'system'
            ? 'System User (Business Manager)' : 'Tài khoản cá nhân']);
        rows.push(['Có App Secret', res.has_secret
            ? 'Có'
            : (res.token_type === 'system'
                ? 'Chưa — không bắt buộc với System User'
                : 'CHƯA — đây thường là nguyên nhân')]);
        if (res.scopes?.length) {
            rows.push(['Quyền', res.scopes.slice(0, 6).join(', ')
                       + (res.scopes.length > 6 ? '...' : '')]);
        }

        return `
            <table class="token-facts">
                ${rows.map(([k, v]) => `<tr><th>${k}</th><td>${this._esc(String(v))}</td></tr>`).join('')}
            </table>
        `;
    },

    showUpdateTokenModal(accountId, kind = 'user') {
        const sys = kind === 'system';
        Modal.open(`
            <h3 class="modal-title">Cập nhật token Facebook</h3>
            <p class="form-hint" style="margin-bottom:14px">
                Dán token mới vào đây. Tool sẽ <strong>lấy lại token cho tất cả Fanpage</strong>
                của tài khoản này — bước bắt buộc, không thì các Page vẫn dùng token cũ đã chết.
            </p>

            <input type="hidden" id="updTokenKind" value="${kind}">
            <input type="hidden" id="updAccountId" value="${accountId}">

            ${this._tokenKindPicker(kind, 'AccountsPage.switchUpdateTokenKind')}

            <div class="form-group">
                <label>${sys ? 'System User Access Token (mới)' : 'User Access Token (mới)'}</label>
                <textarea class="form-input" id="newToken" rows="4"
                          placeholder="${sys
                              ? 'Dán token tạo ở Business Settings → Người dùng hệ thống...'
                              : 'Dán token lấy từ Graph API Explorer...'}"></textarea>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>App ID</label>
                    <input type="text" class="form-input" id="newAppId"
                           placeholder="Để trống sẽ dùng lại App ID đã lưu">
                </div>
                <div class="form-group">
                    <label>App Secret</label>
                    <input type="password" class="form-input" id="newAppSecret"
                           placeholder="Để trống sẽ dùng lại App Secret đã lưu">
                </div>
            </div>

            <div class="fb-token-warn">
                ${sys
                    ? `Token <strong>System User</strong> tạo với <strong>Token Expiration = Never</strong>
                       thì dùng vĩnh viễn, không phải gia hạn nữa.
                       App ID + App Secret không bắt buộc — nhập vào chỉ để tool kiểm tra được
                       hạn và quyền của token.`
                    : `<strong>Bắt buộc phải có App ID + App Secret.</strong>
                       Thiếu hai thứ này, Facebook chỉ cấp token sống <strong>1–2 tiếng</strong>,
                       đăng bài hôm sau là báo lỗi "Session has expired".`}
            </div>

            <div class="modal-actions">
                <button class="btn btn-outline" onclick="Modal.close()">Huỷ</button>
                <button class="btn btn-primary" onclick="AccountsPage.updateToken(${accountId})" id="updTokenBtn">
                    Cập nhật & Quét lại Page
                </button>
            </div>
        `);
    },

    /** Đổi kiểu token ở cửa sổ cập nhật, giữ lại những gì đã dán. */
    switchUpdateTokenKind(kind) {
        const v = id => document.getElementById(id)?.value || '';
        const keep = { token: v('newToken'), appId: v('newAppId'), secret: v('newAppSecret') };
        const accountId = +v('updAccountId');

        this.showUpdateTokenModal(accountId, kind);

        const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
        set('newToken', keep.token);
        set('newAppId', keep.appId);
        set('newAppSecret', keep.secret);
    },

    async updateToken(accountId) {
        const token = document.getElementById('newToken')?.value.trim();
        if (!token) {
            Toast.error('Chưa dán token');
            return;
        }

        const btn = document.getElementById('updTokenBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Đang xử lý...'; }

        try {
            const res = await API.put(`/api/accounts/${accountId}/token`, {
                access_token: token,
                app_id: document.getElementById('newAppId')?.value.trim() || '',
                app_secret: document.getElementById('newAppSecret')?.value.trim() || '',
                token_type: document.getElementById('updTokenKind')?.value || null,
            });

            const r = res.result;
            Modal.close();

            const ngay = r.days_left;
            if (r.long_lived && !r.warning) {
                Toast.success(`Xong! Token dùng được ${ngay ?? 60} ngày. `
                            + `Đã làm mới ${r.pages_refreshed} Fanpage.`);
            } else {
                Toast.success(`Đã cập nhật, làm mới ${r.pages_refreshed} Fanpage.`);
            }
            if (r.warning) {
                Modal.open(`
                    <h3 class="modal-title">Token vẫn chưa dùng lâu được</h3>
                    <pre class="fb-error-box">${this._esc(r.warning)}</pre>
                    <div class="fb-token-warn">
                        Lấy <strong>App ID</strong> và <strong>App Secret</strong> tại
                        <strong>developers.facebook.com</strong> → chọn App →
                        <strong>Settings → Basic</strong>. Nhập đúng hai giá trị này thì
                        Facebook mới cấp token dùng được 60 ngày.
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-outline" onclick="Modal.close()">Đóng</button>
                        <button class="btn btn-primary"
                                onclick="Modal.close(); AccountsPage.showUpdateTokenModal(${accountId})">
                            Nhập lại
                        </button>
                    </div>
                `);
            }

            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            if (btn) { btn.disabled = false; btn.textContent = 'Cập nhật & Quét lại Page'; }
        }
    },

    _esc(str) {
        return String(str ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    },

    deleteAccount(accountId) {
        Modal.open(`
            <div style="text-align:center;padding:20px 0">
                <div style="font-size:48px;margin-bottom:16px">⚠️</div>
                <h3 style="margin-bottom:8px">Xác nhận xóa tài khoản?</h3>
                <p style="color:var(--text-secondary);margin-bottom:24px">
                    Tất cả Fanpage liên kết cũng sẽ bị xóa.<br>Hành động này không thể hoàn tác.
                </p>
                <div style="display:flex;gap:12px;justify-content:center">
                    <button class="btn btn-outline" onclick="Modal.close()" style="min-width:100px">Hủy</button>
                    <button class="btn btn-danger" onclick="AccountsPage._confirmDelete(${accountId})" style="min-width:100px">🗑️ Xóa</button>
                </div>
            </div>
        `);
    },

    async _confirmDelete(accountId) {
        Modal.close();
        try {
            await API.delete(`/api/accounts/${accountId}`);
            Toast.success('Đã xóa tài khoản');
            App.refreshPage();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    init() {},
};
