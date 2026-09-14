// Modal dialog component
const Modal = {
    overlay: null,
    content: null,

    init() {
        this.overlay = document.getElementById('modalOverlay');
        this.content = document.getElementById('modalContent');
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.close();
        });
    },

    open(html) {
        this.content.innerHTML = html;
        this.overlay.classList.add('active');
    },

    close() {
        this.overlay.classList.remove('active');
        this.content.innerHTML = '';
    },

    confirm(title, message, onConfirm) {
        this.open(`
            <h3 style="margin-bottom: var(--space-4)">${title}</h3>
            <p style="color: var(--text-secondary); margin-bottom: var(--space-6)">${message}</p>
            <div class="flex gap-3" style="justify-content: flex-end">
                <button class="btn btn-secondary" onclick="Modal.close()">Hủy</button>
                <button class="btn btn-danger" id="modalConfirmBtn">Xác Nhận</button>
            </div>
        `);
        document.getElementById('modalConfirmBtn').addEventListener('click', () => {
            onConfirm();
            this.close();
        });
    },
};
