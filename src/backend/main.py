import os
import uuid
import time
import asyncio
from pathlib import Path
from threading import Thread

import aiofiles
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration Management ---
class EnvConfig:
    """
    管理環境變數的類別，支援動態重新載入。
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.last_mtime = 0
            # 可以通過環境變數控制是否啟用輪詢
            self.polling_enabled = os.getenv("ENABLE_POLLING", "true").lower() == "true"
            self.load_config()
            self._initialized = True

    def load_config(self):
        """從 .env 檔案載入或重新載入環境變數。"""
        print(f"🔄 開始載入配置...")
        
        # 優先檢查當前目錄的 .env 檔案（掛載的檔案）
        env_path = Path(".env")
        
        if env_path.exists():
            current_mtime = env_path.stat().st_mtime
            print(f"📁 找到 .env 檔案: {env_path.absolute()}")
            print(f"📊 檔案大小: {env_path.stat().st_size} bytes")
            print(f"🕐 檔案修改時間: {current_mtime}")
            print(f"🕐 上次修改時間: {self.last_mtime}")
            
            # 更新最後修改時間
            self.last_mtime = current_mtime
            
            # 先清除相關的環境變數
            if "STATIC_BEARER_TOKEN" in os.environ:
                del os.environ["STATIC_BEARER_TOKEN"]
            if "HOST_URL" in os.environ:
                del os.environ["HOST_URL"]
            # 新增：清除 CUSTOM_UPLOAD_DIR
            if "CUSTOM_UPLOAD_DIR" in os.environ:
                del os.environ["CUSTOM_UPLOAD_DIR"]
            # 清除新增的環境變數
            if "ALLOWED_EXTENSIONS" in os.environ:
                del os.environ["ALLOWED_EXTENSIONS"]
            if "MAX_FILE_SIZE_MB" in os.environ:
                del os.environ["MAX_FILE_SIZE_MB"]
            if "MAX_STORAGE_SIZE_MB" in os.environ:
                del os.environ["MAX_STORAGE_SIZE_MB"]
            
            # 重新載入 .env 檔案
            success = load_dotenv(env_path, override=True)
            print(f"📥 dotenv 載入結果: {success}")
            
            # 讀取檔案內容進行除錯
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"📄 .env 檔案內容預覽:")
                    for i, line in enumerate(content.split('\n')[:10], 1):
                        if line.strip() and not line.strip().startswith('#'):
                            print(f"   {i}: {line}")
            except Exception as e:
                print(f"❌ 讀取 .env 檔案失敗: {e}")
                
        else:
            # 如果當前目錄沒有 .env，則使用 find_dotenv 尋找
            dotenv_path = find_dotenv()
            if dotenv_path:
                load_dotenv(dotenv_path, override=True)
                print(f"載入 .env 檔案: {dotenv_path}")
            else:
                print("⚠️  .env 檔案未找到，使用預設值或現有環境變數")

        # 讀取環境變數並去除可能的引號
        raw_token = os.getenv("STATIC_BEARER_TOKEN", "default-token")
        raw_host = os.getenv("HOST_URL", "http://localhost:8765")
        # 新增：讀取 CUSTOM_UPLOAD_DIR
        raw_upload_dir = os.getenv("CUSTOM_UPLOAD_DIR", "") # 預設為空字串
        # 新增：讀取新的環境變數
        raw_allowed_extensions = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif,webp,bmp,svg")
        raw_max_file_size = os.getenv("MAX_FILE_SIZE_MB", "10")
        raw_max_storage_size = os.getenv("MAX_STORAGE_SIZE_MB", "1000")

        print(f"🔍 原始環境變數:")
        print(f"   STATIC_BEARER_TOKEN (raw): '{raw_token}'")
        print(f"   HOST_URL (raw): '{raw_host}'")
        print(f"   CUSTOM_UPLOAD_DIR (raw): '{raw_upload_dir}'") # 新增日誌
        print(f"   ALLOWED_EXTENSIONS (raw): '{raw_allowed_extensions}'")
        print(f"   MAX_FILE_SIZE_MB (raw): '{raw_max_file_size}'")
        print(f"   MAX_STORAGE_SIZE_MB (raw): '{raw_max_storage_size}'")
        
        self.STATIC_BEARER_TOKEN = raw_token.strip('"').strip("'")
        self.HOST_URL = raw_host.strip('"').strip("'")
        # 新增：處理 CUSTOM_UPLOAD_DIR
        self.CUSTOM_UPLOAD_DIR = raw_upload_dir.strip('"').strip("'")
        # 新增：處理新的環境變數
        self.ALLOWED_EXTENSIONS = [ext.strip().lower() for ext in raw_allowed_extensions.strip('"').strip("'").split(',') if ext.strip()]
        try:
            self.MAX_FILE_SIZE_MB = int(raw_max_file_size.strip('"').strip("'"))
        except ValueError:
            self.MAX_FILE_SIZE_MB = 10  # 預設值
        try:
            self.MAX_STORAGE_SIZE_MB = int(raw_max_storage_size.strip('"').strip("'"))
        except ValueError:
            self.MAX_STORAGE_SIZE_MB = 1000  # 預設值
        
        print(f"✅ 配置已更新:")
        print(f"   STATIC_BEARER_TOKEN: {self.STATIC_BEARER_TOKEN[:8]}..." if len(self.STATIC_BEARER_TOKEN) > 8 else f"   STATIC_BEARER_TOKEN: {self.STATIC_BEARER_TOKEN}")
        print(f"   HOST_URL: {self.HOST_URL}")
        print(f"   CUSTOM_UPLOAD_DIR: {self.CUSTOM_UPLOAD_DIR if self.CUSTOM_UPLOAD_DIR else '[未設定，將使用預設路徑]'}") # 新增日誌
        print(f"   ALLOWED_EXTENSIONS: {self.ALLOWED_EXTENSIONS}")
        print(f"   MAX_FILE_SIZE_MB: {self.MAX_FILE_SIZE_MB} {'(無限制)' if self.MAX_FILE_SIZE_MB == -1 else 'MB'}")
        print(f"   MAX_STORAGE_SIZE_MB: {self.MAX_STORAGE_SIZE_MB} {'(無限制)' if self.MAX_STORAGE_SIZE_MB == -1 else 'MB'}")
        print(f"🔚 配置載入完成\n")

    def check_file_changed(self):
        """檢查 .env 檔案是否有變化"""
        env_path = Path(".env")
        if env_path.exists():
            current_mtime = env_path.stat().st_mtime
            if current_mtime != self.last_mtime:
                print(f"📝 檢測到 .env 檔案變化 (輪詢): {self.last_mtime} -> {current_mtime}")
                self.load_config()
                return True
        return False

class ConfigHandler(FileSystemEventHandler):
    """
    處理 .env 檔案變化的事件處理器。
    """
    def __init__(self, config: EnvConfig):
        super().__init__()
        self.config = config
        self.last_reload_time = 0

    def _should_reload(self, file_path):
        """檢查是否應該重新載入配置"""
        return (file_path.endswith(".env") or 
                file_path.endswith("/.env") or 
                file_path.split('/')[-1] == ".env")

    def _reload_with_delay(self, event_type, file_path):
        """延遲重新載入配置，避免重複觸發"""
        current_time = time.time()
        if current_time - self.last_reload_time < 1.0:  # 1秒內不重複載入
            print(f"⏭️  跳過重複的 {event_type} 事件: {file_path}")
            return
        
        self.last_reload_time = current_time
        print(f"🔄 檢測到 .env 檔案{event_type}: {file_path}")
        print(f"⏱️  等待檔案寫入完成...")
        time.sleep(1.0)  # 增加延遲時間確保檔案寫入完成
        self.config.load_config()

    def on_modified(self, event):
        if not event.is_directory and self._should_reload(event.src_path):
            self._reload_with_delay("修改", event.src_path)
    
    def on_moved(self, event):
        if not event.is_directory and self._should_reload(event.dest_path):
            self._reload_with_delay("移動/重命名", event.dest_path)
    
    def on_created(self, event):
        if not event.is_directory and self._should_reload(event.src_path):
            self._reload_with_delay("創建", event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory and self._should_reload(event.src_path):
            print(f"⚠️  檢測到 .env 檔案被刪除: {event.src_path}")
    
    def on_any_event(self, event):
        # 記錄所有事件用於除錯
        if not event.is_directory and (".env" in event.src_path or (hasattr(event, 'dest_path') and ".env" in event.dest_path)):
            print(f"🔍 檔案系統事件: {event.event_type} - {event.src_path}" + 
                  (f" -> {event.dest_path}" if hasattr(event, 'dest_path') else ""))

# --- Initial Setup ---
config = EnvConfig() # 初始化配置管理器

# 應用程式內部始終使用相對路徑 "uploads"
# 實際的儲存位置由 Docker volume 掛載決定
UPLOADS_DIR = Path("uploads")
print(f"🚀 應用程式內部上傳目錄: {UPLOADS_DIR.absolute()}")

# 確保上傳目錄存在
# 在 Docker 環境中，這會創建 /app/uploads
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


# --- Helper Functions ---
async def verify_token(authorization: str = Header(...)):
    """依賴注入函數，用於驗證 Bearer Token"""
    # 從動態配置中獲取最新的 STATIC_BEARER_TOKEN
    if authorization != f"Bearer {config.STATIC_BEARER_TOKEN}":
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Token")

def validate_file_extension(filename: str) -> bool:
    """驗證檔案副檔名是否被允許"""
    if not filename:
        return False
    
    file_ext = Path(filename).suffix.lower().lstrip('.')
    return file_ext in config.ALLOWED_EXTENSIONS

def validate_file_size(file_size: int) -> bool:
    """驗證檔案大小是否符合限制"""
    if config.MAX_FILE_SIZE_MB == -1:  # 無限制
        return True
    
    max_size_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024
    return file_size <= max_size_bytes

def get_directory_size(directory: Path) -> int:
    """計算目錄總大小（位元組）"""
    total_size = 0
    try:
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except Exception as e:
        print(f"計算目錄大小時發生錯誤: {e}")
    return total_size

def validate_storage_space(new_file_size: int) -> bool:
    """驗證儲存空間是否足夠"""
    if config.MAX_STORAGE_SIZE_MB == -1:  # 無限制
        return True
    
    current_size = get_directory_size(UPLOADS_DIR)
    max_size_bytes = config.MAX_STORAGE_SIZE_MB * 1024 * 1024
    
    return (current_size + new_file_size) <= max_size_bytes

# --- API Endpoint ---
@app.post("/upload", dependencies=[Depends(verify_token)])
async def upload_image(file: UploadFile = File(...)):
    """
    處理圖片上傳。
    - 驗證 Bearer Token。
    - 驗證檔案副檔名。
    - 驗證檔案大小。
    - 驗證儲存空間。
    - 使用 UUID 作為檔名。
    - 儲存檔案。
    - 回傳公開 URL。
    """
    try:
        # 驗證檔案副檔名
        if not validate_file_extension(file.filename):
            allowed_exts = ', '.join(config.ALLOWED_EXTENSIONS)
            raise HTTPException(
                status_code=400, 
                detail=f"不支援的檔案類型。允許的副檔名: {allowed_exts}"
            )
        
        # 讀取檔案內容以檢查大小
        file_content = await file.read()
        file_size = len(file_content)
        
        # 驗證檔案大小
        if not validate_file_size(file_size):
            max_size_mb = config.MAX_FILE_SIZE_MB
            raise HTTPException(
                status_code=400, 
                detail=f"檔案太大。最大允許大小: {max_size_mb}MB"
            )
        
        # 驗證儲存空間
        if not validate_storage_space(file_size):
            max_storage_mb = config.MAX_STORAGE_SIZE_MB
            current_size_mb = get_directory_size(UPLOADS_DIR) / (1024 * 1024)
            raise HTTPException(
                status_code=400, 
                detail=f"儲存空間不足。目前使用: {current_size_mb:.1f}MB，最大限制: {max_storage_mb}MB"
            )
        
        # 產生唯一檔名，保留原始副檔名
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOADS_DIR / unique_filename

        # 寫入檔案（使用已讀取的內容）
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(file_content)

        # 組合公開 URL
        # 從動態配置中獲取最新的 HOST_URL
        public_url = f"{config.HOST_URL}/images/{unique_filename}"
        
        return JSONResponse(
            status_code=200,
            content={"url": public_url}
        )
    except HTTPException:
        # 重新拋出 HTTPException
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

# --- Root Endpoint (for health check) ---
@app.get("/")
def read_root():
    return {"status": "PicoUploader API is running"}

# --- Configuration Endpoint ---
@app.get("/config")
def get_upload_config():
    """取得上傳配置資訊（公開端點，供前端使用）"""
    return {
        "allowed_extensions": config.ALLOWED_EXTENSIONS,
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
        "max_storage_size_mb": config.MAX_STORAGE_SIZE_MB,
        "current_storage_size_mb": round(get_directory_size(UPLOADS_DIR) / (1024 * 1024), 2)
    }

# --- Debug Endpoints ---
@app.get("/debug/config", dependencies=[Depends(verify_token)])
def get_current_config():
    """取得目前的配置資訊（除錯用，需要驗證）"""
    env_path = Path(".env")
    current_storage_size = get_directory_size(UPLOADS_DIR)
    return {
        "STATIC_BEARER_TOKEN": config.STATIC_BEARER_TOKEN[:8] + "..." if len(config.STATIC_BEARER_TOKEN) > 8 else config.STATIC_BEARER_TOKEN,
        "HOST_URL": config.HOST_URL,
        "CUSTOM_UPLOAD_DIR": config.CUSTOM_UPLOAD_DIR,
        "ALLOWED_EXTENSIONS": config.ALLOWED_EXTENSIONS,
        "MAX_FILE_SIZE_MB": config.MAX_FILE_SIZE_MB,
        "MAX_STORAGE_SIZE_MB": config.MAX_STORAGE_SIZE_MB,
        "current_storage_size_bytes": current_storage_size,
        "current_storage_size_mb": round(current_storage_size / (1024 * 1024), 2),
        "env_file_exists": env_path.exists(),
        "env_file_path": str(env_path.absolute()) if env_path.exists() else None,
        "env_file_size": env_path.stat().st_size if env_path.exists() else None,
        "env_file_mtime": env_path.stat().st_mtime if env_path.exists() else None,
        "last_known_mtime": config.last_mtime,
        "polling_enabled": config.polling_enabled,
        "watchdog_active": hasattr(app.state, "observer") and app.state.observer and app.state.observer.is_alive()
    }

@app.post("/debug/reload-config", dependencies=[Depends(verify_token)])
def reload_config():
    """手動重新載入配置（除錯用，需要驗證）"""
    print("🔧 手動觸發配置重新載入...")
    config.load_config()
    return {"message": "配置已重新載入", "success": True}

# --- Background Tasks ---
async def file_polling_task():
    """背景任務：定期檢查 .env 檔案變化"""
    print("🔄 啟動 .env 檔案輪詢任務...")
    while config.polling_enabled:
        try:
            config.check_file_changed()
            await asyncio.sleep(2)  # 每 2 秒檢查一次
        except Exception as e:
            print(f"❌ 輪詢任務錯誤: {e}")
            await asyncio.sleep(5)  # 錯誤時等待更長時間

# --- Watchdog Setup ---
# 在應用程式啟動時啟動 watchdog 觀察者和輪詢任務
@app.on_event("startup")
async def startup_event():
    print("啟動 .env 檔案監聽器...")
    
    # 檢查 .env 檔案是否存在
    env_path = Path(".env")
    if env_path.exists():
        print(f"找到 .env 檔案: {env_path.absolute()}")
    else:
        print("警告: .env 檔案不存在，請確保已正確掛載")
    
    # 啟動 watchdog 觀察者
    event_handler = ConfigHandler(config)
    observer = Observer()
    
    # 監聽當前目錄（.env 檔案所在的目錄）
    # 使用絕對路徑確保監聽正確的目錄
    watch_path = str(Path(".").absolute())
    print(f"監聽目錄: {watch_path}")
    observer.schedule(event_handler, path=watch_path, recursive=False)
    observer.start()
    
    # 將 observer 儲存起來，以便在應用程式關閉時停止它
    app.state.observer = observer
    print("✅ .env 檔案 watchdog 監聽器已啟動")
    
    # 啟動輪詢任務作為備用方案
    asyncio.create_task(file_polling_task())
    print("✅ .env 檔案輪詢任務已啟動")

@app.on_event("shutdown")
async def shutdown_event():
    print("停止 .env 檔案監聽器...")
    
    # 停止輪詢任務
    config.polling_enabled = False
    print("✅ 輪詢任務已停止")
    
    # 停止 watchdog 觀察者
    if hasattr(app.state, "observer") and app.state.observer:
        app.state.observer.stop()
        app.state.observer.join()
        print("✅ watchdog 觀察者已停止")