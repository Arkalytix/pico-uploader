// --- 使用者必須設定 ---
// 你的後端 API 公開 URL，結尾不要加斜線
const RAW_API_BASE_URL = 'http://localhost:8765';
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, '');
// --------------------

const tokenSection = document.getElementById('token-section');
const uploadSection = document.getElementById('upload-section');
const tokenInput = document.getElementById('token-input');
const saveTokenButton = document.getElementById('save-token-button');
const dropZone = document.getElementById('drop-zone');
const resultUrlInput = document.getElementById('result-url');
const copyButton = document.getElementById('copy-button');
const logoutButton = document.getElementById('logout-button');
const messageDisplay = document.getElementById('message-display'); // 新增訊息顯示元素
let thumbnailContainer; // 新增縮圖容器變數

let bearerToken = null;
let uploadConfig = null; // 儲存上傳配置

function showUI(section) {
    tokenSection.style.display = section === 'token' ? 'block' : 'none';
    uploadSection.style.display = section === 'upload' ? 'block' : 'none';
    // 只有在切換到上傳頁面時才隱藏訊息，保留 token 頁面的錯誤訊息
    if (section === 'upload') {
        showMessage('', 'hide');
    }
}

function showMessage(message, type = 'info') {
    if (!messageDisplay) {
        return;
    }
    
    messageDisplay.textContent = message;
    
    if (type !== 'hide') {
        // 顯示訊息時，移除隱藏類別並添加相應的樣式類別
        messageDisplay.classList.remove('message-hidden');
        messageDisplay.classList.remove('message-info', 'message-success', 'message-error');
        messageDisplay.classList.add(`message-${type}`);
        
        // 確保元素可見
        messageDisplay.style.height = 'auto';
        messageDisplay.style.padding = '10px 15px';
        messageDisplay.style.margin = '15px 0';
        messageDisplay.style.opacity = '1';
        messageDisplay.style.display = 'block';
    } else {
        // 隱藏訊息時
        messageDisplay.style.opacity = '0';
        messageDisplay.style.height = '0';
        messageDisplay.style.padding = '0';
        messageDisplay.style.margin = '0';
        
        // 延遲添加 hidden 類別，讓過渡效果完成
        setTimeout(() => {
            messageDisplay.classList.add('message-hidden');
            messageDisplay.classList.remove('message-info', 'message-success', 'message-error');
        }, 300);
    }
    
    // 自動隱藏訊息（成功和資訊訊息）
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            showMessage('', 'hide');
        }, 3000);
    }
    // 錯誤訊息不自動隱藏
}

// 驗證 Token 格式是否有效（只包含 ASCII 字符）
function isValidTokenFormat(token) {
    // 檢查是否只包含 ASCII 字符（0-127）
    return /^[\x00-\x7F]*$/.test(token);
}

// 載入上傳配置
async function loadUploadConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/config`);
        if (response.ok) {
            uploadConfig = await response.json();
            console.log('上傳配置已載入:', uploadConfig);
        } else {
            console.error('無法載入上傳配置:', response.status);
        }
    } catch (error) {
        console.error('載入上傳配置失敗:', error);
    }
}

// 驗證檔案
function validateFile(file) {
    if (!uploadConfig) {
        return { isValid: false, errorMessage: '配置未載入，請稍後再試' };
    }
    
    // 檢查副檔名
    const fileName = file.name.toLowerCase();
    const fileExtension = fileName.split('.').pop();
    
    if (!uploadConfig.allowed_extensions.includes(fileExtension)) {
        const allowedExts = uploadConfig.allowed_extensions.join(', ');
        return { 
            isValid: false, 
            errorMessage: `不支援的檔案類型。允許的副檔名: ${allowedExts}` 
        };
    }
    
    // 檢查檔案大小
    if (uploadConfig.max_file_size_mb !== -1) {
        const maxSizeBytes = uploadConfig.max_file_size_mb * 1024 * 1024;
        if (file.size > maxSizeBytes) {
            return { 
                isValid: false, 
                errorMessage: `檔案太大。最大允許大小: ${uploadConfig.max_file_size_mb}MB` 
            };
        }
    }
    
    // 檢查儲存空間（概略檢查）
    if (uploadConfig.max_storage_size_mb !== -1) {
        const fileSizeMB = file.size / (1024 * 1024);
        const remainingSpace = uploadConfig.max_storage_size_mb - uploadConfig.current_storage_size_mb;
        
        if (fileSizeMB > remainingSpace) {
            return { 
                isValid: false, 
                errorMessage: `儲存空間不足。剩餘空間: ${remainingSpace.toFixed(1)}MB，檔案大小: ${fileSizeMB.toFixed(1)}MB` 
            };
        }
    }
    
    return { isValid: true };
}

// 驗證 Token 的通用函數
async function verifyToken(token) {
    if (!token) {
        return { isValid: false, errorType: 'empty' };
    }
    
    // 先檢查 Token 格式
    if (!isValidTokenFormat(token)) {
        return { isValid: false, errorType: 'format' };
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: new FormData()
        });

        if (response.ok || response.status === 422) {
            return { isValid: true };
        } else if (response.status === 403) {
            return { isValid: false, errorType: 'unauthorized' };
        } else {
            console.error('Token 驗證時發生未知錯誤:', response.status, await response.text());
            return { isValid: false, errorType: 'server' };
        }
    } catch (error) {
        console.error('Token 驗證請求失敗:', error);
        if (error.message.includes('non ISO-8859-1')) {
            return { isValid: false, errorType: 'encoding' };
        } else {
            return { isValid: false, errorType: 'network' };
        }
    }
}

// 儲存並驗證 Token
saveTokenButton.addEventListener('click', async () => {
    const token = tokenInput.value.trim();
    if (!token) {
        showMessage('Token 不能為空', 'error');
        return;
    }

    const result = await verifyToken(token);
    if (result.isValid) {
        bearerToken = token;
        localStorage.setItem('pico_uploader_token', token);
        showUI('upload');
        showMessage('Token 儲存成功！', 'success');
    } else {
        // 根據錯誤類型顯示相應的錯誤訊息
        switch (result.errorType) {
            case 'format':
                showMessage('Token 格式無效，請確保只包含英文字母、數字和符號', 'error');
                break;
            case 'encoding':
                showMessage('Token 包含無效字符，請確保只使用英文字母、數字和符號', 'error');
                break;
            case 'network':
                showMessage('網路連線錯誤，請檢查網路連線或稍後再試', 'error');
                break;
            case 'unauthorized':
                showMessage('Token 驗證失敗，請檢查您的 Token 是否正確', 'error');
                break;
            case 'server':
                showMessage('伺服器錯誤，請稍後再試', 'error');
                break;
            default:
                showMessage('Token 驗證失敗，請檢查您的 Token 是否正確', 'error');
        }
        tokenInput.value = '';
        showUI('token');
    }
});

// 頁面載入時檢查並驗證 Token
document.addEventListener('DOMContentLoaded', async () => {
    // 載入上傳配置
    await loadUploadConfig();
    
    // 初始化 dropZone 的內容
    dropZone.innerHTML = `
        <div class="drop-zone-left">
            <p>將檔案拖到這裡</p>
        </div>
        <div class="drop-zone-right">
            <div id="thumbnail-container"></div>
        </div>
    `;
    thumbnailContainer = document.getElementById('thumbnail-container');

    const savedToken = localStorage.getItem('pico_uploader_token');
    if (savedToken) {
        const result = await verifyToken(savedToken);
        if (result.isValid) {
            bearerToken = savedToken;
            showUI('upload');
        } else {
            showMessage('已儲存的 Token 無效，請重新輸入', 'error');
            localStorage.removeItem('pico_uploader_token');
            tokenInput.value = '';
            showUI('token');
        }
    } else {
        showUI('token');
    }
});

// 登出功能
logoutButton.addEventListener('click', () => {
    bearerToken = null;
    localStorage.removeItem('pico_uploader_token');
    tokenInput.value = '';
    resultUrlInput.value = ''; // 清空上次上傳的連結
    if (thumbnailContainer) {
        thumbnailContainer.innerHTML = ''; // 清空縮圖
    }
    // 清空上傳狀態訊息
    dropZone.querySelector('.drop-zone-left p').textContent = '將檔案拖到這裡';
    showUI('token');
    showMessage('已登出。', 'info');
});

// 上傳邏輯
async function uploadFile(file) {
    if (!bearerToken) {
        showMessage('無法驗證，請重新輸入 Token', 'error');
        showUI('token');
        return;
    }
    
    // 驗證檔案
    const validation = validateFile(file);
    if (!validation.isValid) {
        showMessage(validation.errorMessage, 'error');
        dropZone.querySelector('.drop-zone-left p').innerHTML = `<span style="color: red;">${validation.errorMessage}</span>`;
        setTimeout(() => {
            dropZone.querySelector('.drop-zone-left p').textContent = '將檔案拖到這裡';
        }, 3000);
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);

    // 清空縮圖容器並顯示上傳中訊息
    thumbnailContainer.innerHTML = '';
    dropZone.querySelector('.drop-zone-left p').textContent = '上傳中...';
    dropZone.classList.add('dragover');
    showMessage('檔案上傳中...', 'info');

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${bearerToken}`
            },
            body: formData,
        });

        const result = await response.json();

        if (!response.ok) {
            if (response.status === 403) {
                 throw new Error('驗證失敗 (Forbidden)，請檢查你的 Token。');
            }
            throw new Error(result.detail || `伺服器錯誤: ${response.status}`);
        }
        
        // 後端返回的 result.url 已經是完整的 URL，直接使用
        // 後端返回的 result.url 已經是完整的 URL，對其進行正規化處理，移除多餘的斜線
        const finalImageUrl = result.url.replace(/([^:]\/)\/+/g, '$1').replace(/"/g, '').trim();
        resultUrlInput.value = finalImageUrl;
        copyButton.style.display = 'inline-block';
        showMessage('檔案上傳成功！', 'success');

        // 顯示縮圖
        const img = document.createElement('img');
        img.src = finalImageUrl;
        img.alt = 'Uploaded Image Thumbnail';
        thumbnailContainer.innerHTML = ''; // 清空之前的縮圖
        thumbnailContainer.appendChild(img);
        dropZone.querySelector('.drop-zone-left p').textContent = '上傳成功！';

    } catch (error) {
        console.error('上傳失敗:', error);
        dropZone.querySelector('.drop-zone-left p').innerHTML = `<span style="color: red;">上傳失敗: ${error.message}</span>`;
        thumbnailContainer.innerHTML = ''; // 清空縮圖
        showMessage(`上傳失敗: ${error.message}`, 'error');
    } finally {
        // 只有在非成功狀態下才重置 dropZone 內容和清空縮圖
        // 成功上傳後，縮圖和成功訊息會保留
        if (!response || !response.ok) { // 檢查 response 是否存在且不成功
            setTimeout(() => {
                dropZone.querySelector('.drop-zone-left p').textContent = '將檔案拖到這裡';
                thumbnailContainer.innerHTML = ''; // 清空縮圖
                dropZone.classList.remove('dragover');
            }, 3000);
        }
    }
}

// --- 事件監聽器 (拖拉、複製) ---
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); });
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) { uploadFile(files[0]); }
});
copyButton.addEventListener('click', () => {
    const imageUrl = resultUrlInput.value; // 獲取完整的圖片 URL
    const markdownLink = `![image](${imageUrl})`; // 轉換為 Markdown 格式

    // 創建一個臨時的 textarea 元素來複製內容
    const tempTextArea = document.createElement('textarea');
    tempTextArea.value = markdownLink;
    document.body.appendChild(tempTextArea);
    tempTextArea.select();
    document.execCommand('copy');
    document.body.removeChild(tempTextArea); // 移除臨時元素

    copyButton.textContent = '已複製！';
    setTimeout(() => { copyButton.textContent = '複製'; }, 1500);
});