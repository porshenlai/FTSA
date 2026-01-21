import asyncio
import signal
import os
import sqlite3
from aiohttp import web

## gemini-helpme: 
## 1. 建立一個異步 Web 伺服器運行在 8081 埠。
## 2. 實作 GET /data?symbol_year 路由處理快取讀取。
## 3. 實作 POST /api/commit 路由接收 Worker 回報。
## 4. 實作發送 SIGUSR1 給 Worker 的邏輯。

class HubServer:
    def __init__(self):
        self.worker_pid = None  # 需從設定或環境變數取得 Worker 的 PID
        self.db_path = "financial_data.db"
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 資料庫結構"""
        with sqlite3.connect(self.db_path) as conn:
            # 任務追蹤表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    year INTEGER,
                    status TEXT, -- Pending, Running, Success, Fail
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 這裡可以預留 PriceData 索引表

    async def handle_get_data(self, request):
        """處理前端資料請求: ?2330_TW-2025"""
        query = request.query_string
        print(f"收到資料請求: {query}")
        
        # 模擬 L2/L3 快取檢查
        # if data_not_found:
        #     await self.trigger_worker_task("2330.TW", 2025)
        #     return web.json_response({"status": "Syncing"})
        
        return web.json_response({"status": "Success", "data": [0, {"O": 100, "C": 105}]})

    async def handle_commit_task(self, request):
        """處理 Worker 任務回報"""
        data = await request.json()
        task_id = request.query.get("taskID")
        print(f"任務 {task_id} 已由 Worker 回報成功")
        
        # 更新資料庫狀態
        return web.json_response({"status": "Acknowledged"})

    async def trigger_worker_task(self, symbol, year):
        """向 Worker 發送 SIGUSR1 信號"""
        if self.worker_pid:
            print(f"發送 SIGUSR1 至 Worker (PID: {self.worker_pid})")
            os.kill(self.worker_pid, signal.SIGUSR1)
        else:
            print("警告: 尚未偵測到運行的 Worker PID")

    def make_app(self):
        app = web.Application()
        app.router.add_get('/data', self.handle_get_data)
        app.router.add_post('/api/commit', self.handle_commit_task)
        return app

if __name__ == "__main__":
    hub = HubServer()
    app = hub.make_app()
    web.run_app(app, port=8081)
