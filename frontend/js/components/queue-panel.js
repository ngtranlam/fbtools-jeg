// Bảng theo dõi hàng đợi đăng bài.
//
// Đăng ngay không còn nghĩa là bài lên ngay: mỗi bài cách nhau 60–120 giây để
// không giống máy chạy tự động. Vậy nên phải có chỗ nhìn thấy hàng đợi đang tới
// đâu, còn bao nhiêu bài, bao lâu nữa tới bài kế — nếu không người dùng tưởng
// tool treo và bấm đăng lại.

const QueuePanel = {
    el: null,
    data: null,
    _timer: null,

    setup() {
        if (typeof WS !== 'undefined' && WS.on) {
            WS.on('publish_queue', (msg) => {
                this.data = msg;
                if (msg.waiting || msg.current) this.show();
                this.render();
            });
        }
        this.refresh();
    },

    async refresh() {
        try {
            const res = await API.get('/api/posts/queue');
            this.data = res;
            if (res.waiting || res.current) this.show();
            this.render();
        } catch (e) { /* chưa chạy thì thôi */ }
    },

    show() {
        if (!this.el) {
            this.el = document.createElement('div');
            this.el.className = 'queue-panel';
            document.body.appendChild(this.el);
        }
        this.el.classList.remove('hidden');
        this._tick();
    },

    hide() {
        if (this.el) this.el.classList.add('hidden');
        clearInterval(this._timer);
        this._timer = null;
    },

    /** Đếm ngược tại chỗ để số giây chạy mượt, khỏi đợi tin từ máy chủ. */
    _tick() {
        clearInterval(this._timer);
        this._timer = setInterval(() => {
            if (!this.data) return;
            if (this.data.next_in > 0) {
                this.data.next_in -= 1;
                this.render();
            }
        }, 1000);
    },

    render() {
        if (!this.el || !this.data) return;
        const d = this.data;

        if (!d.waiting && !d.current) {
            this.el.innerHTML = `
                <div class="queue-head">
                    <strong>Hàng đợi đăng bài</strong>
                    <button class="queue-x" onclick="QueuePanel.hide()">✕</button>
                </div>
                <div class="queue-empty">Không còn bài nào chờ.</div>
                ${this._recent(d)}
            `;
            clearInterval(this._timer);
            return;
        }

        const dangDang = d.current
            ? `Đang đăng: <strong>${this._esc(d.current.target_name || d.current.target_id)}</strong>`
            : (d.next_in > 0
                ? `Nghỉ <strong>${d.next_in}s</strong> nữa rồi đăng bài kế tiếp`
                : 'Đang chuẩn bị...');

        this.el.innerHTML = `
            <div class="queue-head">
                <strong>Hàng đợi đăng bài</strong>
                <button class="queue-x" onclick="QueuePanel.hide()">✕</button>
            </div>
            <div class="queue-now">${dangDang}</div>
            <div class="queue-count">
                Còn <strong>${d.waiting}</strong> bài đang chờ
                <span class="muted">— mỗi bài cách nhau ${d.delay_min}–${d.delay_max}s</span>
            </div>
            ${d.waiting ? `
                <div class="queue-eta muted">
                    Ước tính xong sau khoảng ${this._eta(d)} phút
                </div>
                <button class="btn btn-xs btn-outline" onclick="QueuePanel.cancel()">
                    Huỷ các bài còn chờ
                </button>
            ` : ''}
            ${this._recent(d)}
        `;
    },

    _eta(d) {
        const tb = (d.delay_min + d.delay_max) / 2;
        return Math.max(1, Math.round((d.waiting * tb + d.next_in) / 60));
    },

    _recent(d) {
        const r = (d.recent || []).slice(0, 5);
        if (!r.length) return '';
        return `
            <div class="queue-recent">
                ${r.map(x => `
                    <div class="queue-recent-row ${x.status}">
                        <span>${x.status === 'posted' ? '✓' : '✕'}</span>
                        <span class="queue-recent-name">${this._esc(x.target_name || x.target_id)}</span>
                        <span class="muted">${x.at}</span>
                    </div>
                `).join('')}
            </div>
        `;
    },

    async cancel() {
        if (!confirm('Huỷ tất cả các bài còn đang chờ trong hàng đợi?')) return;
        try {
            const res = await API.post('/api/posts/queue/cancel', {});
            Toast.info(`Đã huỷ ${res.removed} bài`);
            this.refresh();
        } catch (e) {
            Toast.error('Lỗi: ' + e.message);
        }
    },

    _esc(v) {
        return String(v ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    },
};
