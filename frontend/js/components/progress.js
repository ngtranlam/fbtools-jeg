// Progress bar component
const Progress = {
    create(id) {
        return `
            <div class="progress-wrap" id="progress-${id}">
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text">
                    <span class="progress-msg">Waiting...</span>
                    <span class="progress-pct">0%</span>
                </div>
            </div>
        `;
    },

    update(id, pct, msg) {
        const wrap = document.getElementById(`progress-${id}`);
        if (!wrap) return;
        const fill = wrap.querySelector('.progress-bar-fill');
        const msgEl = wrap.querySelector('.progress-msg');
        const pctEl = wrap.querySelector('.progress-pct');
        if (fill) fill.style.width = `${pct}%`;
        if (msgEl) msgEl.textContent = msg || '';
        if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;
    },
};
