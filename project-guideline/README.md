# 專案指南：PicoUploader - 基於 FastAPI 與 Netlify 的安全圖床

這是一份為「PicoUploader」專案制定的開發規範，旨在定義其技術架構、檔案結構和核心功能實現。此文件將作為後續與 AI Agent 協作開發的基礎藍圖。

## 1. 核心架構 (Core Architecture)

本專案採用前後端分離架構：

*   **前端 (Frontend):**
    *   **技術:** 純靜態 HTML, CSS, JavaScript。
    *   **職責:** 提供使用者介面，包括 token 輸入、檔案拖曳上傳、結果顯示。
    *   **部署:** Netlify (利用其全球 CDN 和簡易的拖曳部署)。

*   **後端 (Backend):**
    *   **技術:** Python FastAPI 框架。
    *   **職責:** 接收檔案、驗證 Bearer Token、產生 UUID 檔名、儲存檔案、回傳公開 URL。
    *   **部署:** Docker 容器，運行在你的個人 VPS 上。

*   **流量走向 (Traffic Flow):**
    1.  **使用者** 在 Netlify 網站上操作。
    2.  **前端 JS** 攜帶 Bearer Token 向你的 VPS 發起 API 請求 (`https://your-domain.com/upload`)。
    3.  **你的 Nginx** 收到請求，將其反向代理到後端 Docker 容器的指定端口。
    4.  **Docker 容器內的 FastAPI** 處理請求，儲存檔案。
    5.  **FastAPI** 回傳結果給前端。

## 2. 專案目錄結構

為了保持清晰，我們將前後端程式碼放在不同的資料夾中。

```
src/
├── backend/
│   ├── uploads/          # 儲存上傳的圖片 (重要：會被 .gitignore 排除)
│   │   └── .gitkeep      # 讓 git 追蹤這個空目錄
│   ├── Dockerfile        # Docker 鏡像設定檔
│   ├── main.py           # FastAPI 應用程式主檔案
│   ├── requirements.txt  # Python 依賴套件
│   ├── .env              # 【私密】環境變數，儲存 Token (絕不提交到 Git)
│   ├── .env.example      # .env 的範本檔，可公開
│   └── .gitignore        # Git 忽略清單
│
└── frontend/
    ├── index.html        # 主頁面
    ├── style.css         # 樣式表
    └── script.js         # 主要的 JavaScript 邏輯
```

## 3. 開發規範 - 後端 (FastAPI + Docker)

後端將被打包成一個獨立的 Docker 鏡像，方便在任何地方部署。

### 3.1. 端口選擇

*   **內部端口:** 我們選擇 `8765` 作為 Docker 容器內部 FastAPI 服務的監聽端口。這是一個非標準的高位端口，避免衝突。
*   **外部端口:** 你將透過 Nginx 將外部的請求（例如 443 埠的 `/upload` 路徑）映射到內部的 `8765` 端口。

### 3.2. 環境變數 (`backend/.env.example`)

為了安全起見，所有敏感資訊都將透過環境變數管理。提供一個範本檔讓使用者知道需要設定哪些值。

```ini
# .env.example
# 將此檔案複製為 .env 並填入你自己的值

# 用於 API 驗證的靜態 Bearer Token，請產生一個複雜的隨機字串
# 例如用 openssl rand -hex 32 產生
STATIC_BEARER_TOKEN="change-this-to-a-very-secure-random-string"

# 你的服務器對外的公開 URL，用於組合圖片連結，結尾不要加斜線
# 例如：https://images.your-domain.com
HOST_URL="http://localhost:8765"
```
**規範：** 實際的 `.env` 檔案必須被 `backend/.gitignore` 忽略。
此外，`.venv` 虛擬環境目錄也應被忽略。

### 3.3. Python 依賴 (`backend/requirements.txt`)

```txt
fastapi
uvicorn[standard]
python-multipart
python-dotenv
aiofiles
```

*   `fastapi`: 核心框架。
*   `uvicorn`: ASGI 伺服器，用於運行 FastAPI。
*   `python-multipart`: 處理表單檔案上傳。
*   `python-dotenv`: 從 `.env` 檔案讀取環境變數。
*   `aiofiles`: 以非同步方式處理檔案 I/O，避免阻塞。

### 3.4. FastAPI 應用 (`backend/main.py`)

這是後端的核心邏輯。

```python
import os
import uuid
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# --- Initial Setup ---
load_dotenv()  # 從 .env 檔案載入環境變數

# 讀取環境變數
STATIC_BEARER_TOKEN = os.getenv("STATIC_BEARER_TOKEN")
HOST_URL = os.getenv("HOST_URL")
UPLOADS_DIR = Path("uploads")

# 確保上傳目錄存在
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PicoUploader API")

# --- CORS Middleware ---
# 允許所有來源，方便 Netlify 前端調用。在生產環境中，可以設定為你的 Netlify 域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static File Serving ---
# 將 /images 路徑映射到 uploads 資料夾，讓外界可以訪問上傳的圖片
app.mount("/images", StaticFiles(directory=UPLOADS_DIR), name="images")


# --- Helper Function: Security Check ---
async def verify_token(authorization: str = Header(...)):
    """依賴注入函數，用於驗證 Bearer Token"""
    if authorization != f"Bearer {STATIC_BEARER_TOKEN}":
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Token")

# --- API Endpoint ---
@app.post("/upload", dependencies=[Depends(verify_token)])
async def upload_image(file: UploadFile = File(...)):
    """
    處理圖片上傳。
    - 驗證 Bearer Token。
    - 使用 UUID 作為檔名。
    - 儲存檔案。
    - 回傳公開 URL。
    """
    try:
        # 產生唯一檔名，保留原始副檔名
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOADS_DIR / unique_filename

        # 非同步寫入檔案
        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # 每次讀取 1MB
                await buffer.write(content)

        # 組合公開 URL
        public_url = f"{HOST_URL}/images/{unique_filename}"
        
        return JSONResponse(
            status_code=200, 
            content={"url": public_url}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

# --- Root Endpoint (for health check) ---
@app.get("/")
def read_root():
    return {"status": "PicoUploader API is running"}
```

### 3.5. Docker 設定 (`backend/Dockerfile`)

```dockerfile
# 使用官方 Python 基礎鏡像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式程式碼
COPY . .

# 容器對外暴露的端口
EXPOSE 8765

# 容器啟動時運行的命令
# 使用 0.0.0.0 讓容器外部可以訪問
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
```

### 3.6. Docker 構建與運行指令

```bash
# 1. 進入 backend 目錄
cd backend

# 2. 構建 Docker 鏡像 (picouploader:latest 是鏡像名稱和標籤)
docker build -t picouploader:latest .

# 3. 運行 Docker 容器
#    --name: 給容器取個名字
#    -p: 將主機的 8765 端口映射到容器的 8765 端口
#    --env-file: 將 .env 檔案中的環境變數載入到容器中
#    -v: 將主機的 uploads 目錄掛載到容器的 uploads 目錄，確保檔案持久化
#    -d: 在背景運行
docker run \
  --name pico-uploader-container \
  -p 8765:8765 \
  --env-file .env \
  -v "$(pwd)/uploads":/app/uploads \
  -d picouploader:latest
```

## 4. 開發規範 - 前端 (Netlify)

前端追求極致的簡潔與易用性。

### 4.1. HTML 結構 (`frontend/index.html`)

與先前版本類似，包含 token 輸入區和上傳區。

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PicoUploader</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="app">
        <!-- Token 輸入區 -->
        <div id="token-section">
            <h1>驗證</h1>
            <p>請輸入您的 Bearer Token</p>
            <input type="password" id="token-input" placeholder="貼上你的 Token">
            <button id="save-token-button">儲存並開始</button>
        </div>

        <!-- 上傳區 (預設隱藏) -->
        <div id="upload-section" style="display: none;">
            <h1>PicoUploader</h1>
            <div id="drop-zone"><p>將檔案拖到這裡</p></div>
            <div id="result">
                <p>上傳成功後，連結會顯示在這裡</p>
                <input type="text" id="result-url" readonly>
                <button id="copy-button" style="display: none;">複製</button>
            </div>
        </div>
    </div>
    <script src="script.js"></script>
</body>
</html>
```

### 4.2. CSS 樣式 (`frontend/style.css`)

樣式與先前版本相同，專注於簡潔的用戶體驗。

```css
/* (此處的 CSS 內容與先前回答中的相同，為了簡潔省略) */
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; color: #333;}
#app { background: white; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.1); text-align: center; max-width: 450px; width: 90%;}
h1 { color: #1c1e21; margin-bottom: 0.5rem; }
p { color: #606770; font-size: 0.9rem; }
input[type="password"], input[type="text"] { width: 100%; padding: 12px; margin: 1rem 0; box-sizing: border-box; border: 1px solid #dddfe2; border-radius: 6px; font-size: 1rem; }
button { background: #1877f2; color: white; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-size: 1rem; font-weight: bold; width: 100%; transition: background-color 0.2s; }
button:hover { background: #166fe5; }
#drop-zone { border: 2px dashed #ccd0d5; border-radius: 8px; padding: 50px 20px; margin-top: 1.5rem; transition: background-color 0.2s, border-color 0.2s; }
#drop-zone.dragover { background-color: #e7f3ff; border-color: #1877f2; }
#result { margin-top: 1.5rem; position: relative; }
#copy-button { position: absolute; right: 8px; top: 35px; width: auto; font-size: 0.8rem; padding: 6px 10px; }
```

### 4.3. JavaScript 邏輯 (`frontend/script.js`)

**規範：** 使用者必須手動修改 `API_BASE_URL`。絕不在程式碼中硬編碼 Bearer Token。

```javascript
// --- 使用者必須設定 ---
// 你的後端 API 公開 URL，結尾不要加斜線
const API_BASE_URL = 'https://your-vps-domain.com'; 
// --------------------

const tokenSection = document.getElementById('token-section');
const uploadSection = document.getElementById('upload-section');
const tokenInput = document.getElementById('token-input');
const saveTokenButton = document.getElementById('save-token-button');
const dropZone = document.getElementById('drop-zone');
const resultUrlInput = document.getElementById('result-url');
const copyButton = document.getElementById('copy-button');

let bearerToken = null;

function showUI(section) {
    tokenSection.style.display = section === 'token' ? 'block' : 'none';
    uploadSection.style.display = section === 'upload' ? 'block' : 'none';
}

// 儲存 Token
saveTokenButton.addEventListener('click', () => {
    const token = tokenInput.value;
    if (token) {
        bearerToken = token;
        localStorage.setItem('pico_uploader_token', token);
        showUI('upload');
    } else {
        alert('Token 不能為空');
    }
});

// 頁面載入時檢查 Token
document.addEventListener('DOMContentLoaded', () => {
    const savedToken = localStorage.getItem('pico_uploader_token');
    if (savedToken) {
        bearerToken = savedToken;
        showUI('upload');
    } else {
        showUI('token');
    }
});

// 上傳邏輯
async function uploadFile(file) {
    if (!bearerToken) {
        alert('無法驗證，請重新輸入 Token');
        showUI('token');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);

    dropZone.innerHTML = '<p>上傳中...</p>';
    dropZone.classList.add('dragover');

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
            // 如果 token 錯誤 (403)，提示使用者
            if (response.status === 403) {
                 throw new Error('驗證失敗 (Forbidden)，請檢查你的 Token。');
            }
            throw new Error(result.detail || `伺服器錯誤: ${response.status}`);
        }
        
        dropZone.innerHTML = '<p>上傳成功！</p>';
        resultUrlInput.value = result.url;
        copyButton.style.display = 'inline-block';

    } catch (error) {
        console.error('上傳失敗:', error);
        dropZone.innerHTML = `<p style="color: red;">上傳失敗: ${error.message}</p>`;
    } finally {
        setTimeout(() => {
            dropZone.innerHTML = '<p>將檔案拖到這裡</p>';
            dropZone.classList.remove('dragover');
        }, 3000);
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
    resultUrlInput.select();
    document.execCommand('copy');
    copyButton.textContent = '已複製！';
    setTimeout(() => { copyButton.textContent = '複製'; }, 1500);
});
```