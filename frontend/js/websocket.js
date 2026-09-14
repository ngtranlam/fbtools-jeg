// WebSocket client for real-time updates
const WS = {
    socket: null,
    listeners: {},
    reconnectDelay: 2000,
    maxReconnectDelay: 30000,

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws`;

        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            this.reconnectDelay = 2000;
            this._updateStatus('connected');
            console.log('[WS] Connected');
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._dispatch(data.type, data);
            } catch (e) {
                console.error('[WS] Parse error:', e);
            }
        };

        this.socket.onclose = () => {
            this._updateStatus('disconnected');
            console.log('[WS] Disconnected, reconnecting...');
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
        };

        this.socket.onerror = () => {
            this._updateStatus('disconnected');
        };
    },

    on(type, callback) {
        if (!this.listeners[type]) this.listeners[type] = [];
        this.listeners[type].push(callback);
    },

    off(type, callback) {
        if (!this.listeners[type]) return;
        this.listeners[type] = this.listeners[type].filter(cb => cb !== callback);
    },

    _dispatch(type, data) {
        (this.listeners[type] || []).forEach(cb => cb(data));
        (this.listeners['*'] || []).forEach(cb => cb(data));
    },

    _updateStatus(status) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        if (!dot || !text) return;

        dot.className = 'status-dot ' + status;
        const labels = { connected: 'Đã kết nối', disconnected: 'Mất kết nối', connecting: 'Đang kết nối...' };
        text.textContent = labels[status] || status;
    },
};
