// Trang Kiểm Tra Trùng Lặp
const CheckerPage = {
    async render() {
        let jobs = [];
        try {
            const jRes = await API.listJobs();
            jobs = (jRes.jobs || []).filter(j => j.status === 'completed' && j.variants.length > 0);
        } catch (e) { /* empty */ }

        const lastReport = window._lastReport || null;

        return `
            <div class="page-header">
                <h1 class="page-title">Kiểm Tra Trùng Lặp</h1>
                <p class="page-subtitle">Xác minh tất cả biến thể video có mã hash khác nhau</p>
            </div>

            ${lastReport ? CheckerPage.renderReport(lastReport) : ''}

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Chọn Công Việc Để Kiểm Tra</h3>
                </div>

                ${jobs.length > 0 ? `
                    <div class="video-list">
                        ${jobs.map(j => `
                            <div class="video-item" onclick="CheckerPage.runCheck('${j.job_id}')">
                                <div class="video-thumb">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5z"/></svg>
                                </div>
                                <div class="video-info">
                                    <div class="video-name">Mã: ${j.job_id}</div>
                                    <div class="video-meta">
                                        <span>${j.variants.length} biến thể</span>
                                        <span class="badge badge-green">hoàn thành</span>
                                    </div>
                                </div>
                                <button class="btn btn-sm btn-primary">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                    Kiểm Tra
                                </button>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="empty-state">
                        <div class="empty-state-icon">🔍</div>
                        <div class="empty-state-title">Chưa có công việc hoàn thành</div>
                        <div class="empty-state-desc">Tạo biến thể trước, sau đó kiểm tra trùng lặp tại đây</div>
                    </div>
                `}
            </div>

            <div id="checkResultArea"></div>
        `;
    },

    renderReport(report) {
        const samplePositions = report.results.length > 0 && report.results[0].frame_hashes.length > 0
            ? report.results[0].frame_hashes.map(fh => fh.position)
            : [];
        const numPositions = samplePositions.length;

        return `
            <div class="report-result ${report.all_unique ? 'unique' : 'duplicate'} mb-6">
                <div class="report-result-icon">${report.all_unique ? '✅' : '⚠️'}</div>
                <div class="report-result-title">
                    ${report.all_unique ? 'Tất Cả Video Đều ĐỘC NHẤT' : 'Phát Hiện Video Có Thể Trùng Lặp'}
                </div>
                <div class="report-result-desc">
                    ${report.total_videos} video đã kiểm tra · ${report.unique_count} độc nhất ·
                    ${report.duplicate_pairs.length} cặp tương tự
                </div>
            </div>

            ${report.all_unique ? `
                <div class="card mb-6" style="border-color: var(--success)">
                    <h4 style="color: var(--success); margin-bottom: var(--space-3)">✅ Bạn có thể yên tâm đăng bài:</h4>
                    <ul style="color: var(--text-secondary); font-size: var(--text-sm); list-style: disc; padding-left: var(--space-6); line-height: 1.8">
                        <li>Mỗi biến thể được tạo với các hiệu ứng FFmpeg khác nhau (cắt, màu sắc, tốc độ, tỷ lệ, mã hóa lại)</li>
                        <li>Kiểm tra hash từng khung hình xác nhận tất cả video đều khác biệt về hình ảnh</li>
                        <li>Metadata đã được xóa và tạo mới ngẫu nhiên cho mỗi biến thể</li>
                        <li>Các nền tảng như Facebook, TikTok so sánh video bằng dấu vân tay hình ảnh — biến thể của bạn sẽ vượt qua</li>
                    </ul>
                </div>
            ` : `
                <div class="card mb-6" style="border-color: var(--warning)">
                    <h4 style="color: var(--warning); margin-bottom: var(--space-3)">⚠️ Phát hiện cặp video tương tự:</h4>
                    ${report.duplicate_pairs.map(p => `
                        <div style="font-size: var(--text-sm); padding: var(--space-2) 0; color: var(--text-secondary)">
                            <strong>${p.video_a}</strong> ↔ <strong>${p.video_b}</strong>
                            — Độ tương tự: <span style="color: var(--error)">${p.similarity}%</span>
                            ${p.avg_distance !== undefined ? `<span style="color: var(--text-muted)"> (khoảng cách: ${p.avg_distance})</span>` : ''}
                        </div>
                    `).join('')}
                    <p style="margin-top: var(--space-3); font-size: var(--text-sm); color: var(--text-secondary)">
                        Hãy tạo lại biến thể với chế độ "Mạnh" để thay đổi nhiều hơn.
                    </p>
                </div>
            `}

            ${report.results.length > 0 ? `
                <div class="card mb-6">
                    <div class="card-header">
                        <h3 class="card-title">Chi Tiết Hash Từng Khung Hình</h3>
                    </div>
                    <div class="hash-matrix">
                        <table>
                            <thead>
                                <tr>
                                    <th>Video</th>
                                    ${samplePositions.map(p => `<th>${p}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${report.results.map(r => `
                                    <tr>
                                        <td style="text-align:left; font-weight:500">${r.filename.substring(0, 30)}</td>
                                        ${r.frame_hashes.map(fh => `<td>${fh.hash_value.substring(0, 14)}...</td>`).join('')}
                                        ${numPositions > r.frame_hashes.length
                                            ? Array(numPositions - r.frame_hashes.length).fill('<td>-</td>').join('')
                                            : ''}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : ''}
        `;
    },

    async runCheck(jobId) {
        Toast.info('Đang kiểm tra trùng lặp...');
        const area = document.getElementById('checkResultArea');
        if (area) area.innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Đang phân tích khung hình...</div>';

        try {
            const res = await API.checkJob(jobId);
            window._lastReport = res.report;
            await App.refreshPage();
            if (res.report.all_unique) {
                Toast.success('Tất cả biến thể đều độc nhất!');
            } else {
                Toast.warning('Một số biến thể có thể quá giống nhau');
            }
        } catch (e) {
            Toast.error(`Kiểm tra thất bại: ${e.message}`);
            if (area) area.innerHTML = '';
        }
    },

    init() {},
};
