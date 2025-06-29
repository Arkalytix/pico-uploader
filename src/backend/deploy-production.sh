#!/bin/bash

# PicoUploader 生產環境的一鍵部署腳本
# 此腳本會自動建置映像、初始化上傳目錄並啟動 Docker 容器

set -e  # 遇到錯誤立即退出

# 載入 .env 檔案中的環境變數
if [ -f ".env" ]; then
  echo "📥 載入 .env 檔案..."
  # 使用 set -a 確保所有變數都被導出，然後使用 set +a 關閉
  set -a
  . ./.env
  set +a
  echo "✅ .env 檔案載入完成"
else
  echo "⚠️  .env 檔案不存在，將使用預設配置"
fi

# 設定變數
# 讀取自定義上傳目錄路徑，如果沒有設定則使用預設路徑
UPLOAD_DIR="${CUSTOM_UPLOAD_DIR:-$HOME/pico_uploads}"
IMAGE_NAME="picouploader"
CONTAINER_NAME="picouploader-prod"
HOST_PORT="8765"
CONTAINER_PORT="8765"

echo "🚀 PicoUploader 生產環境部署開始..."
echo "📁 上傳目錄: $UPLOAD_DIR"

# 步驟 1: 檢查必要文件
echo ""
echo "🔍 檢查必要文件..."

if [ ! -f "Dockerfile" ]; then
    echo "❌ 錯誤: 找不到 Dockerfile"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ 錯誤: 找不到 requirements.txt"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ 錯誤: .env 檔案不存在"
    echo "請先創建 .env 檔案，可以參考 .env.example"
    exit 1
fi

echo "✅ 所有必要文件都存在"

# 步驟 2: 停止並移除現有容器和映像
echo ""
echo "🧹 清理現有容器和映像..."

# 停止並移除現有容器
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo "🛑 停止現有容器: $CONTAINER_NAME"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    echo "🗑️  移除現有容器: $CONTAINER_NAME"
    docker rm $CONTAINER_NAME 2>/dev/null || true
else
    echo "ℹ️  沒有找到現有容器: $CONTAINER_NAME"
fi

# 移除現有映像（可選，但確保使用最新版本）
if docker images | grep -q "^$IMAGE_NAME "; then
    echo "🗑️  移除現有映像: $IMAGE_NAME"
    docker rmi $IMAGE_NAME 2>/dev/null || true
fi

# 步驟 3: 建置 Docker 映像
echo ""
echo "🔨 建置 Docker 映像..."

# 建置映像
docker build -t $IMAGE_NAME:latest .

# 也建置帶時間戳的版本作為備份
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker build -t $IMAGE_NAME:$TIMESTAMP .

echo "✅ Docker 映像建置完成！"
echo "📦 可用映像："
docker images | grep $IMAGE_NAME

# 步驟 4: 初始化上傳目錄
echo ""
echo "📁 初始化上傳目錄..."

if [ -d "$UPLOAD_DIR" ]; then
    echo "✅ 目錄已存在: $UPLOAD_DIR"
else
    echo "📁 創建目錄: $UPLOAD_DIR"
    sudo mkdir -p "$UPLOAD_DIR"
    echo "✅ 目錄創建成功"
fi

# 設定目錄擁有者和權限
echo "👤 設定目錄擁有者為當前用戶: $(whoami)"
sudo chown -R $(whoami):$(whoami) "$UPLOAD_DIR"

echo "🔒 設定目錄權限為 755"
chmod 755 "$UPLOAD_DIR"

# 測試寫入權限
TEST_FILE="$UPLOAD_DIR/.test_write_permission"
if touch "$TEST_FILE" 2>/dev/null; then
    echo "✅ 寫入權限正常"
    rm -f "$TEST_FILE"
else
    echo "❌ 寫入權限測試失敗"
    exit 1
fi

# 步驟 5: 啟動新容器
echo ""
echo "🚀 啟動生產環境容器..."
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p $HOST_PORT:$CONTAINER_PORT \
    -v "$(pwd)/.env:/app/.env:ro" \
    -v "$UPLOAD_DIR:/app/uploads" \
    $IMAGE_NAME:latest

# 步驟 6: 驗證容器狀態
echo ""
echo "🔍 驗證容器狀態..."
sleep 3

if docker ps | grep -q $CONTAINER_NAME; then
    echo "✅ 容器啟動成功！"
    
    # 顯示容器資訊
    echo ""
    echo "📊 容器資訊:"
    docker ps | grep $CONTAINER_NAME
    
    echo ""
    echo "🎉 部署完成！"
    echo ""
    echo "📋 摘要:"
    echo "   容器名稱: $CONTAINER_NAME"
    echo "   映像版本: $IMAGE_NAME:latest, $IMAGE_NAME:$TIMESTAMP"
    echo "   API 端點: http://$HOST_PORT"
    echo "   上傳目錄: $UPLOAD_DIR"
    echo "   目錄擁有者: $(stat -c '%U:%G' "$UPLOAD_DIR")"
    echo "   目錄權限: $(stat -c '%a' "$UPLOAD_DIR")"
    echo ""
    echo "📝 後續步驟:"
    echo "   1. 設定 Nginx 反向代理"
    echo "   2. 配置 SSL 證書"
    echo "   3. 測試 API 功能"
    echo ""
    echo "🔧 管理命令:"
    echo "   查看日誌: docker logs -f $CONTAINER_NAME"
    echo "   停止容器: docker stop $CONTAINER_NAME"
    echo "   重啟容器: docker restart $CONTAINER_NAME"
    echo "   重新部署: ./deploy-production.sh"
    
else
    echo "❌ 容器啟動失敗！"
    echo "查看日誌: docker logs $CONTAINER_NAME"
    exit 1
fi