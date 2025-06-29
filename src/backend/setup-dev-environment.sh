#!/bin/bash

# PicoUploader 開發環境設定腳本
# 為了保持開發環境與生產環境一致，也使用相同的上傳目錄路徑

# 讀取自定義上傳目錄路徑，如果沒有設定則使用預設路徑
UPLOAD_DIR="${CUSTOM_UPLOAD_DIR:-$HOME/pico_uploads}"

echo "🛠️  設定 PicoUploader 開發環境..."
echo "📁 上傳目錄: $UPLOAD_DIR"

# 檢查是否為開發環境
if [ "$1" = "--dev" ]; then
    echo "🔧 開發模式: 將使用本地 uploads 目錄作為替代"
    UPLOAD_DIR="$(pwd)/uploads"
    echo "📁 開發環境上傳目錄: $UPLOAD_DIR"
fi

# 創建目錄
if [ -d "$UPLOAD_DIR" ]; then
    echo "✅ 目錄已存在: $UPLOAD_DIR"
else
    echo "📁 創建目錄: $UPLOAD_DIR"
    if [[ "$UPLOAD_DIR" == $HOME/* ]]; then
        # 生產環境路徑需要 sudo
        sudo mkdir -p "$UPLOAD_DIR"
        sudo chown -R $(whoami):$(whoami) "$UPLOAD_DIR"
    else
        # 開發環境路徑
        mkdir -p "$UPLOAD_DIR"
    fi
    echo "✅ 目錄創建成功"
fi

# 設定權限
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

echo "🎉 環境設定完成！"
echo ""
echo "📋 摘要:"
echo "   目錄路徑: $UPLOAD_DIR"
echo "   擁有者: $(stat -c '%U:%G' "$UPLOAD_DIR" 2>/dev/null || echo "$(whoami):$(whoami)")"
echo "   權限: $(stat -c '%a' "$UPLOAD_DIR" 2>/dev/null || echo "755")"
echo ""
echo "💡 使用方式:"
echo "   生產環境: ./setup-dev-environment.sh"
echo "   開發環境: ./setup-dev-environment.sh --dev"