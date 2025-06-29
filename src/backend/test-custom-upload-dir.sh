#!/bin/bash

# 測試自定義上傳目錄配置的腳本
# 用於驗證環境變數是否正確載入

echo "🔍 測試自定義上傳目錄配置..."
echo ""

# 載入 .env 文件（如果存在）
if [ -f ".env" ]; then
    echo "✅ 找到 .env 文件"
    source .env
    echo "📄 .env 文件內容（CUSTOM_UPLOAD_DIR 相關）："
    grep -E "^CUSTOM_UPLOAD_DIR" .env || echo "   未找到 CUSTOM_UPLOAD_DIR 設定"
else
    echo "⚠️  .env 文件不存在"
fi

echo ""

# 測試路徑解析
UPLOAD_DIR="${CUSTOM_UPLOAD_DIR:-$HOME/pico_uploads}"

echo "📁 路徑解析結果："
echo "   CUSTOM_UPLOAD_DIR: ${CUSTOM_UPLOAD_DIR:-'(未設定)'}"
echo "   HOME: $HOME"
echo "   最終使用路徑: $UPLOAD_DIR"

echo ""

# 檢查路徑狀態
echo "🔍 路徑狀態檢查："

if [ -d "$UPLOAD_DIR" ]; then
    echo "   ✅ 目錄存在: $UPLOAD_DIR"
    echo "   📊 目錄資訊:"
    ls -ld "$UPLOAD_DIR"
    
    # 測試寫入權限
    TEST_FILE="$UPLOAD_DIR/.test_write_permission"
    if touch "$TEST_FILE" 2>/dev/null; then
        echo "   ✅ 寫入權限正常"
        rm -f "$TEST_FILE"
    else
        echo "   ❌ 寫入權限測試失敗"
    fi
else
    echo "   ❌ 目錄不存在: $UPLOAD_DIR"
    
    # 檢查父目錄
    parent_dir=$(dirname "$UPLOAD_DIR")
    if [ -d "$parent_dir" ]; then
        echo "   📁 父目錄存在: $parent_dir"
        echo "   📊 父目錄權限:"
        ls -ld "$parent_dir"
    else
        echo "   ❌ 父目錄也不存在: $parent_dir"
    fi
fi

echo ""

# 顯示建議
echo "💡 建議："
if [ -z "$CUSTOM_UPLOAD_DIR" ]; then
    echo "   - 當前使用預設路徑"
    echo "   - 如需自定義路徑，請在 .env 文件中添加："
    echo "     CUSTOM_UPLOAD_DIR=\"/your/custom/path/\""
else
    echo "   - 當前使用自定義路徑"
    if [ ! -d "$UPLOAD_DIR" ]; then
        echo "   - 建議執行: ./deploy-production.sh 來創建目錄並部署"
    fi
fi

echo ""
echo "🎉 測試完成！"