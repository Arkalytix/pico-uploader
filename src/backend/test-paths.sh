#!/bin/bash

# 測試路徑展開的腳本

echo "🔍 測試路徑變數展開..."
echo ""

# 測試 HOME 變數
echo "當前用戶: $(whoami)"
echo "HOME 變數: $HOME"
echo "展開後的上傳目錄: $HOME/pico_uploads"
echo ""

# 測試目錄是否可以創建（不實際創建）
# 讀取自定義上傳目錄路徑，如果沒有設定則使用預設路徑
UPLOAD_DIR="${CUSTOM_UPLOAD_DIR:-$HOME/pico_uploads}"
echo "完整路徑: $UPLOAD_DIR"
echo "父目錄是否存在: $([ -d "$(dirname "$UPLOAD_DIR")" ] && echo "是" || echo "否")"
echo "父目錄權限: $(ls -ld "$(dirname "$UPLOAD_DIR")" 2>/dev/null | awk '{print $1}' || echo "無法讀取")"
echo ""

# 測試 Docker 命令中的路徑展開
echo "Docker 掛載命令預覽:"
echo "  -v \"$UPLOAD_DIR:/app/uploads\""
echo ""

echo "✅ 路徑測試完成"