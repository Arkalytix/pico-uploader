# PicoUploader - 簡易圖床後端服務

基於 FastAPI 的輕量級圖床服務，支援 Docker 部署、動態配置更新、檔案上傳限制和自定義儲存路徑。

## 1. 功能簡介

### 🚀 核心功能
- **檔案上傳**：支援多種圖片格式上傳，自動生成 UUID 檔名
- **Bearer Token 驗證**：安全的 API 存取控制
- **靜態檔案服務**：直接透過 URL 存取上傳的圖片
- **動態配置重載**：修改 `.env` 檔案後自動重新載入，無需重啟服務

### 🛡️ 上傳限制功能
- **檔案類型限制**：可設定允許的副檔名類型
- **檔案大小限制**：可設定單檔最大上傳大小
- **儲存空間限制**：可設定上傳目錄總使用空間限制
- **前後端雙重驗證**：提高安全性和用戶體驗

### 🔧 部署功能
- **Docker 容器化**：一鍵建置和部署
- **自定義上傳目錄**：支援任意絕對路徑配置
- **自動權限處理**：自動設定目錄權限和擁有者
- **容器健康檢查**：自動驗證部署狀態

### 📊 監控功能
- **配置 API**：即時查看當前配置和儲存使用情況
- **除錯端點**：詳細的系統狀態和配置資訊
- **日誌監控**：完整的操作日誌記錄

## 2. 快速上手

### 前置需求
- Docker 和 Docker Compose
- Linux/macOS 環境（推薦）
- 至少 100MB 可用磁碟空間

### 🚀 一鍵部署

```bash
# 1. 克隆專案並進入後端目錄
cd src/backend

# 2. 創建配置檔案
cp .env.example .env

# 3. 編輯配置（必須設定 STATIC_BEARER_TOKEN）
nano .env

# 4. 一鍵部署
chmod +x deploy-production.sh
./deploy-production.sh
```

### 📝 基本配置

編輯 `.env` 檔案：

```bash
# 必須設定：API 驗證 Token（請使用強密碼）
STATIC_BEARER_TOKEN="your-very-secure-random-string-here"

# 必須設定：服務器對外 URL
HOST_URL="https://images.your-domain.com"

# 可選：自定義上傳目錄
# CUSTOM_UPLOAD_DIR="/your/custom/path/"

# 可選：上傳限制配置
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,bmp,svg"
MAX_FILE_SIZE_MB=10
MAX_STORAGE_SIZE_MB=1000
```

### 🧪 測試服務

```bash
# 檢查服務狀態
curl http://localhost:8765/

# 查看配置資訊
curl http://localhost:8765/config

# 測試檔案上傳
curl -X POST \
  -H "Authorization: Bearer your-token" \
  -F "file=@test-image.jpg" \
  http://localhost:8765/upload
```

### 📱 前端整合

前端需要設定 API 基礎 URL：

```javascript
// 在 frontend/script.js 中修改
const API_BASE_URL = 'https://images.your-domain.com';
```

## 3. 詳細配置與部署

### 🐳 Docker 部署

#### 手動 Docker 命令

```bash
# 建置映像
docker build -t picouploader .

# 啟動容器
docker run -d \
    --name picouploader-prod \
    --restart unless-stopped \
    -p 8765:8765 \
    -v "$(pwd)/.env:/app/.env:ro" \
    -v "$(pwd)/uploads:/app/uploads" \
    picouploader
```

#### 容器管理命令

```bash
# 查看日誌
docker logs -f picouploader-prod

# 停止容器
docker stop picouploader-prod

# 重啟容器
docker restart picouploader-prod

# 進入容器（除錯用）
docker exec -it picouploader-prod /bin/bash
```

### 📁 上傳目錄配置

#### 預設路徑配置
- 預設使用 `$HOME/pico_uploads` 作為上傳目錄
- 自動展開為當前用戶的家目錄
- 例如：`/home/username/pico_uploads` 或 `/root/pico_uploads`

#### 自定義路徑配置

在 `.env` 檔案中設定：

```bash
# 範例 1：系統 www 目錄
CUSTOM_UPLOAD_DIR="/var/www/images/"

# 範例 2：外部儲存
CUSTOM_UPLOAD_DIR="/mnt/storage/uploads/"

# 範例 3：OneDrive 同步目錄
CUSTOM_UPLOAD_DIR="/root/OneDrive/WebImage/"
```

**配置優先級**：
1. 如果設定 `CUSTOM_UPLOAD_DIR`，使用自定義路徑
2. 如果未設定，使用預設路徑 `$HOME/pico_uploads`

#### 權限處理

部署腳本會自動：
1. 創建目錄（如果不存在）
2. 設定目錄擁有者為當前用戶
3. 設定目錄權限為 755
4. 測試寫入權限

手動權限設定：
```bash
# 設定權限
sudo chown -R $(whoami):$(whoami) "/your/custom/path"
chmod 755 "/your/custom/path"

# 測試權限
touch "/your/custom/path/.test" && rm "/your/custom/path/.test"
```

### 🛡️ 上傳限制配置

#### 檔案類型限制

```bash
# 允許的副檔名（用逗號分隔，不區分大小寫）
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,bmp,svg"
```

**特點**：
- 不區分大小寫（JPG 和 jpg 都接受）
- 不需要包含點號（使用 `jpg` 而不是 `.jpg`）
- 前端和後端都會驗證

**範例配置**：
```bash
# 只允許常見圖片格式
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif"

# 允許更多格式包括向量圖
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,bmp,svg,tiff"
```

#### 檔案大小限制

```bash
# 單檔最大大小（MB），-1 表示無限制
MAX_FILE_SIZE_MB=10
```

**範例配置**：
```bash
# 限制 5MB
MAX_FILE_SIZE_MB=5

# 限制 50MB
MAX_FILE_SIZE_MB=50

# 無限制
MAX_FILE_SIZE_MB=-1
```

#### 儲存空間限制

```bash
# 上傳目錄總空間限制（MB），-1 表示無限制
MAX_STORAGE_SIZE_MB=1000
```

**範例配置**：
```bash
# 限制總空間 500MB
MAX_STORAGE_SIZE_MB=500

# 限制總空間 5GB
MAX_STORAGE_SIZE_MB=5000

# 無限制
MAX_STORAGE_SIZE_MB=-1
```

#### 建議配置

**個人使用**：
```bash
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp"
MAX_FILE_SIZE_MB=5
MAX_STORAGE_SIZE_MB=500
```

**小團隊使用**：
```bash
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,bmp,svg"
MAX_FILE_SIZE_MB=10
MAX_STORAGE_SIZE_MB=2000
```

**大型部署**：
```bash
ALLOWED_EXTENSIONS="jpg,jpeg,png,gif,webp,bmp,svg,tiff"
MAX_FILE_SIZE_MB=50
MAX_STORAGE_SIZE_MB=10000
```

### 🔄 動態配置重載

PicoUploader 支援即時配置更新，無需重啟服務：

#### 自動重載
- 修改 `.env` 檔案後，系統會自動檢測變化
- 使用 watchdog 監聽 + 輪詢機制雙重保護
- 最多 2 秒內生效

#### 手動重載
```bash
# 手動觸發配置重載
curl -X POST \
  -H "Authorization: Bearer your-token" \
  http://localhost:8765/debug/reload-config
```

#### 監控配置變化
```bash
# 查看容器日誌
docker logs -f picouploader-prod

# 預期看到的日誌：
# 📝 檢測到 .env 檔案變化
# 🔄 開始載入配置...
# ✅ 配置已更新
```

### 🔍 API 端點

#### 公開端點

**健康檢查**
```bash
GET /
```

**配置資訊**
```bash
GET /config
```
回傳：
```json
{
  "allowed_extensions": ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"],
  "max_file_size_mb": 10,
  "max_storage_size_mb": 1000,
  "current_storage_size_mb": 245.67
}
```

**檔案上傳**
```bash
POST /upload
Authorization: Bearer your-token
Content-Type: multipart/form-data
```

#### 除錯端點（需要驗證）

**詳細配置資訊**
```bash
GET /debug/config
Authorization: Bearer your-token
```

**手動重載配置**
```bash
POST /debug/reload-config
Authorization: Bearer your-token
```

### 🧪 測試工具

#### 配置測試
```bash
# 測試自定義路徑配置
./test-custom-upload-dir.sh

# 測試路徑解析
./test-paths.sh

# 測試環境變數更新
./test-env-update.sh
```

#### 快速測試流程
```bash
# 1. 啟動服務
./deploy-production.sh

# 2. 測試基本功能
curl http://localhost:8765/

# 3. 測試配置更新
echo 'STATIC_BEARER_TOKEN="new-token-123"' >> .env

# 4. 驗證更新（2秒內）
curl http://localhost:8765/debug/config
```

### 🚨 故障排除

#### 常見問題

**1. 容器啟動失敗**
```bash
# 檢查日誌
docker logs picouploader-prod

# 檢查映像
docker images | grep picouploader

# 重新建置
docker build -t picouploader .
```

**2. 權限問題**
```bash
# 檢查目錄權限
ls -la /your/upload/path

# 手動設定權限
sudo chown -R $(whoami):$(whoami) /your/upload/path
chmod 755 /your/upload/path
```

**3. 配置不生效**
```bash
# 檢查 .env 檔案格式
cat .env | grep -v '^#'

# 確保格式正確（等號前後不能有空格）
# 正確：CUSTOM_UPLOAD_DIR="/path/"
# 錯誤：CUSTOM_UPLOAD_DIR = "/path/"
```

**4. 檔案上傳失敗**
```bash
# 檢查檔案類型限制
curl http://localhost:8765/config

# 檢查檔案大小
ls -lh your-file.jpg

# 檢查儲存空間
df -h /your/upload/path
```

#### 完全重置
```bash
# 停止並移除所有相關容器
docker stop $(docker ps -q --filter ancestor=picouploader)
docker rm $(docker ps -aq --filter ancestor=picouploader)

# 移除所有相關映像
docker rmi $(docker images -q picouploader)

# 清理系統
docker system prune -f

# 重新部署
./deploy-production.sh
```

### 🔒 安全建議

1. **Token 安全**：使用強隨機字串作為 Bearer Token
2. **路徑選擇**：避免使用系統敏感目錄
3. **權限控制**：確保只有必要用戶可存取上傳目錄
4. **定期備份**：建立定期備份機制
5. **磁碟監控**：定期監控磁碟使用量
6. **檔案清理**：考慮實施自動清理舊檔案機制

### 📦 備份與維護

#### 自動備份腳本
```bash
#!/bin/bash
# 讀取實際使用的上傳目錄
UPLOAD_DIR="${CUSTOM_UPLOAD_DIR:-$HOME/pico_uploads}"

# 創建備份
BACKUP_NAME="uploads-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$BACKUP_NAME" "$UPLOAD_DIR/"

echo "✅ 備份完成: $BACKUP_NAME"
```

#### 更新注意事項
- 更新後，自定義路徑設定會保持不變
- 確保 `.env` 檔案在更新過程中不會被覆蓋
- 如需修改路徑，只需編輯 `.env` 檔案

### 🔧 開發環境設定

```bash
# 設定開發環境
./setup-dev-environment.sh

# 本地開發啟動
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8765 --reload
```

### 📚 相關文件

- **專案架構**：`../project-guideline/README.md`
- **前端代碼**：`../frontend/`
- **Docker 配置**：`Dockerfile`
- **環境變數範本**：`.env.example`

---

**版本**：v2.0  
**更新日期**：2024-12-19  
**相容性**：向後兼容所有現有配置  
**授權**：MIT License