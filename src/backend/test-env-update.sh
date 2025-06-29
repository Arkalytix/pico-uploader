#!/bin/bash

# 測試 .env 檔案即時更新功能的腳本

echo "🧪 開始測試 .env 檔案即時更新功能"
echo "=================================="

# 檢查 Docker 容器是否運行
CONTAINER_NAME="picouploader-app"
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "❌ 容器 $CONTAINER_NAME 沒有運行"
    echo "請先啟動容器："
    echo "docker run -d --name $CONTAINER_NAME -p 8765:8765 -v \"\$(pwd)/.env:/app/.env:ro\" -v \"\$(pwd)/uploads:/app/uploads\" picouploader"
    exit 1
fi

echo "✅ 容器正在運行"

# 檢查 API 是否可訪問
echo "🔍 檢查 API 狀態..."
if curl -s http://localhost:8765/ > /dev/null; then
    echo "✅ API 可訪問"
else
    echo "❌ API 無法訪問"
    exit 1
fi

# 獲取當前 token
CURRENT_TOKEN=$(grep STATIC_BEARER_TOKEN .env | cut -d'"' -f2)
echo "🔑 當前 token: ${CURRENT_TOKEN:0:8}..."

# 顯示當前配置
echo "📊 當前配置:"
curl -s -H "Authorization: Bearer $CURRENT_TOKEN" http://localhost:8765/debug/config | python3 -m json.tool

# 備份原始 .env 檔案
cp .env .env.backup
echo "💾 已備份原始 .env 檔案"

# 生成新的 token
NEW_TOKEN="test-token-$(date +%s)"
echo "🔑 新的 token: $NEW_TOKEN"

# 修改 .env 檔案
echo "✏️  修改 .env 檔案..."
sed -i "s/STATIC_BEARER_TOKEN=.*/STATIC_BEARER_TOKEN=\"$NEW_TOKEN\"/" .env

echo "⏱️  等待 5 秒讓 watchdog 或輪詢檢測變化..."
sleep 5

# 檢查配置是否更新
echo "🔍 檢查更新後的配置:"
curl -s -H "Authorization: Bearer $NEW_TOKEN" http://localhost:8765/debug/config | python3 -m json.tool

# 測試新 token 是否生效
echo "🧪 測試新 token 是否生效..."
echo "測試錯誤的 token:"
curl -s -H "Authorization: Bearer wrong-token" http://localhost:8765/debug/config || echo "❌ 預期的錯誤"

echo "測試正確的 token:"
if curl -s -H "Authorization: Bearer $NEW_TOKEN" http://localhost:8765/debug/config > /dev/null; then
    echo "✅ 新 token 生效！"
else
    echo "❌ 新 token 沒有生效"
fi

# 恢復原始 .env 檔案
mv .env.backup .env
echo "🔄 已恢復原始 .env 檔案"

echo "🏁 測試完成"