// Video player component
const VideoPlayer = {
    createPreview(src, poster = '') {
        return `
            <video controls preload="metadata" ${poster ? `poster="${poster}"` : ''} style="width:100%; max-height: 400px; border-radius: var(--radius-md); background: #000;">
                <source src="${src}" type="video/mp4">
                Your browser does not support video.
            </video>
        `;
    },

    createThumbnail(src) {
        return `
            <div class="video-thumb">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </div>
        `;
    },
};
