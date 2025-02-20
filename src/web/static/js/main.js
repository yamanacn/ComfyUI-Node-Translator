document.addEventListener('DOMContentLoaded', function() {
    const apiKeyInput = document.getElementById('api-key');
    const folderPathInput = document.getElementById('folder-path');
    const selectFolderBtn = document.getElementById('select-folder');
    const startTranslationBtn = document.getElementById('start-translation');
    const stopTranslationBtn = document.getElementById('stop-translation');
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    const logContent = document.getElementById('log-content');
    const viewJsonBtn = document.getElementById('view-json');

    let translationInProgress = false;

    // 选择文件夹
    selectFolderBtn.addEventListener('click', async () => {
        const response = await fetch('/select-folder');
        const data = await response.json();
        if (data.path) {
            folderPathInput.value = data.path;
            addLog(`已选择文件夹: ${data.path}`);
        }
    });

    // 开始翻译
    startTranslationBtn.addEventListener('click', async () => {
        if (!folderPathInput.value) {
            alert('请先选择插件文件夹！');
            return;
        }

        translationInProgress = true;
        startTranslationBtn.disabled = true;
        stopTranslationBtn.disabled = false;
        
        const response = await fetch('/start-translation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                apiKey: apiKeyInput.value,
                folderPath: folderPathInput.value
            })
        });

        // 开始轮询进度
        pollProgress();
    });

    // 终止翻译
    stopTranslationBtn.addEventListener('click', async () => {
        const response = await fetch('/stop-translation');
        translationInProgress = false;
        startTranslationBtn.disabled = false;
        stopTranslationBtn.disabled = true;
        addLog('翻译已终止');
    });

    // 轮询翻译进度
    async function pollProgress() {
        if (!translationInProgress) return;

        const response = await fetch('/translation-progress');
        const data = await response.json();

        updateProgress(data.progress);
        addLog(data.message);

        if (data.progress < 100 && translationInProgress) {
            setTimeout(pollProgress, 1000);
        } else {
            translationInProgress = false;
            startTranslationBtn.disabled = false;
            stopTranslationBtn.disabled = true;
        }
    }

    // 更新进度条
    function updateProgress(percent) {
        progressFill.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
    }

    // 添加日志
    function addLog(message) {
        const logEntry = document.createElement('div');
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    // 创建 JSON 查看器
    const jsonViewer = document.createElement('div');
    jsonViewer.className = 'json-viewer';
    jsonViewer.innerHTML = `
        <div class="json-content">
            <span class="close-viewer">&times;</span>
            <pre></pre>
        </div>
    `;
    document.body.appendChild(jsonViewer);
    
    const jsonContent = jsonViewer.querySelector('pre');
    const closeViewer = jsonViewer.querySelector('.close-viewer');
    
    // 查看 JSON 按钮点击事件
    viewJsonBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/get-nodes-json');
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }
            
            // 格式化显示 JSON
            jsonContent.textContent = JSON.stringify(data, null, 2);
            jsonViewer.style.display = 'block';
        } catch (error) {
            alert('获取 JSON 文件失败: ' + error.message);
        }
    });
    
    // 关闭查看器
    closeViewer.addEventListener('click', () => {
        jsonViewer.style.display = 'none';
    });
    
    // 点击背景关闭
    jsonViewer.addEventListener('click', (e) => {
        if (e.target === jsonViewer) {
            jsonViewer.style.display = 'none';
        }
    });
}); 