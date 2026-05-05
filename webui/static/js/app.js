/**
 * Live2D Image Transformer — WebUI App
 */

let selectedFile = null;

// === 拖拽上传 ===
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const previewImg = document.getElementById('previewImg');
const options = document.getElementById('options');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
});

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('请上传图片文件');
        return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        dropZone.style.display = 'none';
        preview.style.display = 'block';
        options.style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

function resetUpload() {
    selectedFile = null;
    fileInput.value = '';
    dropZone.style.display = 'block';
    preview.style.display = 'none';
    options.style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
}

function resetAll() {
    resetUpload();
    document.getElementById('progressSection').style.display = 'none';
}

// === 提交处理 ===
async function startProcess() {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('atlas_size', document.getElementById('atlasSize').value);

    // 显示进度
    options.style.display = 'none';
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';

    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    // 模拟进度动画
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressFill.style.width = progress + '%';
        progressText.textContent = `处理中... ${Math.round(progress)}%`;
    }, 500);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
        });

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = '完成!';

        const data = await response.json();

        setTimeout(() => {
            document.getElementById('progressSection').style.display = 'none';

            if (data.success) {
                showResult(data);
            } else {
                showError(data.error || '处理失败');
            }
        }, 500);

    } catch (err) {
        clearInterval(progressInterval);
        showError('网络错误: ' + err.message);
    }
}

function showResult(data) {
    document.getElementById('resultSection').style.display = 'block';

    // 统计信息
    document.getElementById('resultStats').innerHTML = `
        <div class="stat">
            <div class="stat-value">${data.num_layers}</div>
            <div class="stat-label">图层</div>
        </div>
        <div class="stat">
            <div class="stat-value">${data.num_params}</div>
            <div class="stat-label">参数</div>
        </div>
    `;

    // 图层标签
    const layersDiv = document.getElementById('resultLayers');
    layersDiv.innerHTML = data.layers.map(l =>
        `<span class="layer-tag">${l.name}</span>`
    ).join('');

    // 下载链接
    document.getElementById('downloadBtn').href = data.download_url;
}

function showError(message) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
}
