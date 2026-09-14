// Unified Inbox — comment management across all pages
const InboxPage = {
    comments: [],
    total: 0,
    filter: 'all', // all, unreplied, replied
    selectedPage: null,

    async render() {
        await this.loadComments();

        return `
            <div class="page-header">
                <h1 class="page-title">📥 Unified Inbox</h1>
                <p class="page-subtitle">Quản lý bình luận từ tất cả Fanpage — trả lời nhanh từ 1 nơi</p>
                <button class="btn btn-primary" onclick="InboxPage.syncComments()">🔄 Sync Bình Luận</button>
            </div>

            <!-- Filters -->
            <div class="inbox-filters card">
                <div class="inbox-filter-tabs">
                    <button class="btn btn-sm ${this.filter === 'all' ? 'btn-primary' : 'btn-outline'}"
                            onclick="InboxPage.setFilter('all')">Tất cả (${this.total})</button>
                    <button class="btn btn-sm ${this.filter === 'unreplied' ? 'btn-primary' : 'btn-outline'}"
                            onclick="InboxPage.setFilter('unreplied')">Chưa trả lời</button>
                    <button class="btn btn-sm ${this.filter === 'replied' ? 'btn-primary' : 'btn-outline'}"
                            onclick="InboxPage.setFilter('replied')">Đã trả lời</button>
                </div>
            </div>

            <!-- Comments List -->
            <div class="inbox-list" id="inboxList">
                ${this.comments.length ? this.comments.map(c => `
                    <div class="inbox-item card ${c.replied ? 'inbox-replied' : 'inbox-unreplied'}">
                        <div class="inbox-item-header">
                            <div class="inbox-commenter">
                                <div class="inbox-avatar">${(c.commenter_name || 'U')[0].toUpperCase()}</div>
                                <div>
                                    <div class="inbox-commenter-name">${c.commenter_name || 'Unknown'}</div>
                                    <div class="inbox-meta">
                                        <span class="inbox-page-badge">${c.page_name || 'Page'}</span>
                                        <span>${this._timeAgo(c.created_at)}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="inbox-status">
                                ${c.replied ?
                                    '<span class="badge badge-success">✓ Đã trả lời</span>' :
                                    '<span class="badge badge-warning">Chờ trả lời</span>'}
                            </div>
                        </div>
                        <div class="inbox-message">${this._escapeHtml(c.message)}</div>

                        ${c.replied && c.reply_message ? `
                            <div class="inbox-reply-preview">
                                <span class="inbox-reply-label">↩ Đã trả lời:</span>
                                ${this._escapeHtml(c.reply_message)}
                            </div>
                        ` : ''}

                        ${!c.replied ? `
                            <div class="inbox-reply-form">
                                <input type="text" class="form-input" id="reply_${c.id}"
                                       placeholder="Nhập nội dung trả lời..." onkeydown="if(event.key==='Enter')InboxPage.reply(${c.id})">
                                <button class="btn btn-sm btn-primary" onclick="InboxPage.reply(${c.id})">Gửi</button>
                            </div>
                        ` : ''}
                    </div>
                `).join('') : `
                    <div class="empty-state">
                        <div class="empty-state-icon">📥</div>
                        <div class="empty-state-title">Chưa có bình luận</div>
                        <div class="empty-state-desc">Bấm "Sync Bình Luận" để tải bình luận từ tất cả Fanpage</div>
                    </div>
                `}
            </div>
        `;
    },

    async loadComments() {
        try {
            let url = '/api/inbox/comments?limit=100';
            if (this.filter === 'unreplied') url += '&replied=0';
            if (this.filter === 'replied') url += '&replied=1';

            const res = await API.get(url);
            this.comments = res.comments || [];
            this.total = res.total || 0;
        } catch (e) {
            this.comments = [];
            this.total = 0;
        }
    },

    async setFilter(filter) {
        this.filter = filter;
        App.refreshPage();
    },

    async syncComments() {
        try {
            Toast.info('Đang sync bình luận...');
            const res = await API.post('/api/inbox/sync');
            if (res.status === 'ok') {
                Toast.success(`Sync xong: ${res.new_comments} bình luận mới`);
                App.refreshPage();
            } else {
                Toast.error(res.error || 'Sync thất bại');
            }
        } catch (e) {
            Toast.error('Lỗi sync: ' + e.message);
        }
    },

    async reply(commentId) {
        const input = document.getElementById(`reply_${commentId}`);
        if (!input || !input.value.trim()) {
            Toast.error('Nhập nội dung trả lời');
            return;
        }

        const message = input.value.trim();
        try {
            input.disabled = true;
            const res = await API.post('/api/inbox/reply', {
                comment_id: commentId,
                message: message,
            });

            if (res.status === 'ok') {
                Toast.success('Đã trả lời thành công');
                App.refreshPage();
            } else {
                Toast.error(res.error || 'Trả lời thất bại');
                input.disabled = false;
            }
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
            input.disabled = false;
        }
    },

    _timeAgo(dateStr) {
        if (!dateStr) return '';
        const now = new Date();
        const d = new Date(dateStr);
        const diff = Math.floor((now - d) / 1000);
        if (diff < 60) return 'vừa xong';
        if (diff < 3600) return Math.floor(diff / 60) + ' phút trước';
        if (diff < 86400) return Math.floor(diff / 3600) + ' giờ trước';
        return Math.floor(diff / 86400) + ' ngày trước';
    },

    _escapeHtml(text) {
        if (!text) return '';
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    },

    reset() {
        this.filter = 'all';
    },
};
