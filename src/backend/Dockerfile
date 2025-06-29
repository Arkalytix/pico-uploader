# 使用官方 Python 基礎鏡像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式程式碼（排除 .env 檔案）
COPY main.py .
# 不複製 .env 檔案，因為會透過 volume 掛載

# 容器對外暴露的端口
EXPOSE 8765

# 容器啟動時運行的命令
# 使用 0.0.0.0 讓容器外部可以訪問
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]