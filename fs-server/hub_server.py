import asyncio
import signal
import os
import sqlite3
from aiohttp import web

# 1. 建立一個異步 Web 伺服器運行在 8081 埠。
# 2. 實作 GET /data?symbol_year 路由處理快取讀取。
# 3. 實作 POST /api/commit 路由接收 Worker 回報。
# 4. 實作發送 SIGUSR1 給 Worker 的邏輯。

#@Gemini:
# DBRoot 的目錄結構範例如下:
#	2330_2024.json
#	2330_2025.json
#	2330_2026.db
#	1201_2026.db ......
# 檔案對應到年度與目標(股票)代碼，當年度的資料以 sqlite 保存，跨年度資料以 JSON 格式保存。
# JSON 格式為長度366的物件串列對應到該年的每一天，沒資料填 NULL，
# 物件應包含至少 C O H L V (close,open,high,low,volumn) 等五的屬性
# JSON 轉換至該年度的標格應包含 D C O H L V X (date,close,open,high,low,volumn,extra data) 七個欄位，
# D 為索引欄 (也是使用該年度第幾天的整數型態即可), X 欄為可變程度字串，
# 內容為扣除 C O H L V 屬性後剩餘資料的 JSON 表示。

class HubServer:
    def __init__(self):
		# 需從設定或環境變數取得 Worker 的 PID
        self.worker_pid = None
		# 資料庫根目錄
		self.db_root = "db/"
		# 運行中 syncer 的資料表
        self.syncer_db = self.db_root+"syncer.db"
		self.max_syncer_retry = 3;
		# 可允許最大同時開啟的當年度快取資料庫數量 (記憶體與效率的平衡)，不包含 syncer_db
		self.max_db_caches = 3
		self.db_caches = []
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 資料庫結構"""
		#@Gemini: if db_root not exist then make directory(db_root)

        with sqlite3.connect(self.syncer_db) as conn:
            # 任務追蹤表
			# symbol: 目標 ID
			# year: 資料年度
			# start: 從該年度第幾天開始取得資料
			# status: 擷取狀態
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    year INTEGER,
					begin INTEGER,
                    status TEXT, -- Pending, Running, Success, Fail
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 這裡可以預留 PriceData 索引表

	async def db2json(self,dbn,jsn);
		""" 將 dbn 所儲存的年度資料表格轉換程 JSON 檔案，並回傳 Dictionary Object """
		#@Gemini:
		# 1. if dbn not in cache, open database(dbn)
		# 2. select all its data and do the conversion task to create data_list
		# 3. if jsn then
		#		write(data_list, jsn)
		#  		delete dbn
		# 4. return data_list

	async def schedule_task(self, symbol, year, begin):
		"""設定 Syncer 資料並觸發之"""
		#@Gemini:
		# if SELECT WHERE symbol and year, return False
		# INSERT max_id, symbol, year, begin, "Pending"

        # 向 Worker 發送 SIGUSR1 信號
        if self.worker_pid:
            print(f"發送 SIGUSR1 至 Worker (PID: {self.worker_pid})")
            os.kill(self.worker_pid, signal.SIGUSR1)
        else:
            print("警告: 尚未偵測到運行的 Worker PID")
		return True // pending

	async def prepare_data(self, symbol, year):
		"""準備要回應請求的資料"""
		#@Gemini:
		# if year not this-year
		#	if ${symbol}_${year}.json exists then return read(${symbol}_${year}.json)
		#	if ${symbol}_${year}.db exists then return self.db2json(${symbol}_${year}.db, ${symbol}_${year}.json);
		#	return schedule_task(symbol,year,0)
		# else
		#	if ${symbol}_${year}.db exists and {maximal date in db} <= today then
		#		return self.db2json(${symbol}_${year}.db, ${symbol}_${year}.json)
		#	return schedule_task(symbol,year,${symbol}_${year}.db 的最大資料日期)

    async def handle_get_data(self, request):
        """處理前端資料請求: ?2330_TW-2025"""
        query = request.query_string
		#@Gemini:
		# tid,yid = query.split('-')
        # return web.json_response({"status": "Suceess", "data": prepare_data(tid, int(yid))};

	async def handle_get_task(self,request):
		"""處理 Worker 任務要求"""
		#@Gemini:
		# foreach SELECT task_id,symbol,year,begin WHERE status="Pending"
		#   UPDATE status="Running" where task_id="${task_id}"
		#   return web.json_response({
		#     "TaskID": ${task_id}, "Script": "yfinance_worker",
		#     "Args": { "Symbol": ${symbol}, "Year": ${year}, "Begin": ${begin}, "Interval": "1d" }
		#   })
		# return return web.json_response({})

    async def handle_commit_task(self, request):
        """處理 Worker 任務回報"""
        data = await request.json()
        task_id = request.query.get("taskID")
        print(f"任務 {task_id} 已由 Worker 回報成功")
		#@Gemini:
		# foreach SELECT task_id,symbol,year,begin WHERE status="Running" and task_id="${task_id}"
		#   if data=="FAILED" then
		#     rc=isDigit(status) ? int(status) : 0
		#     if rc<self.max_syncer_retry :
		#       UPDATE status=str(rc+1) where task_id="${task_id}"
		#       continue
		#   DELETE where status="Running" and task_id="${task_id}"
		#   if data != "FAILED" :
		#     db = ${symbol}_${year} in db_cache ? db_cache[${symbol}_${year}] : open(${symbol}_${year}.db)
		#     foreach row in data :
		#       insert row to db
		#     if ${year} < this.year then
		#       self.db2json(${symbol}_${year}.db, ${symbol}_${year}.json)
		return web.json_response({"status": "Acknowledged"})

    def make_app(self):
        app = web.Application()
        app.router.add_get('/data', self.handle_get_data)
        app.router.add_post('/api/request', self.handle_get_task)
        app.router.add_post('/api/commit', self.handle_commit_task)
        return app

if __name__ == "__main__":
    hub = HubServer()
    app = hub.make_app()
    web.run_app(app, port=8081)
