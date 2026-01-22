import asyncio
import signal
import os
import sqlite3
import json
from datetime import datetime
from aiohttp import web
import aiofiles

# 1. 建立一個異步 Web 伺服器運行在 8081 埠。
# 2. 實作 GET /data?symbol_year 路由處理快取讀取。
# 3. 實作 POST /api/commit 路由接收 Worker 回報。
# 4. 實作發送 SIGUSR1 給 Worker 的邏輯。

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
		self.worker_pid = int(os.environ.get("WORKER_PID", 0))
		# 資料庫根目錄
		self.db_root = "db/"
		# 運行中 syncer 的資料表
		self.syncer_db = os.path.join(self.db_root, "syncer.db")
		self.max_syncer_retry = 3
		# 可允許最大同時開啟的當年度快取資料庫數量
		self.max_db_caches = 3
		self.db_caches = {} # 改用 dict 儲存 { "symbol_year": connection }
		
		self._init_db()

	def _init_db(self):
		"""初始化 SQLite 資料庫結構"""
		if not os.path.exists(self.db_root):
			os.makedirs(self.db_root)

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
					status TEXT, -- Pending, Running, Success, Fail, or Retry Count
					created_at DATETIME DEFAULT CURRENT_TIMESTAMP
				)
			""")
			conn.commit()

	async def db2json(self, db_name, json_path=None):
		""" 將 db 儲存的年度資料表格轉換成 JSON 檔案，並回傳 List """
		db_path = os.path.join(self.db_root, db_name)
		
		# 簡單起見，這裡直接開關連線，若要高效能可整合進 self.db_caches
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
		
		# 取得所有欄位
		cursor.execute("SELECT D, C, O, H, L, V, X FROM price_data ORDER BY D ASC")
		rows = cursor.fetchall()
		
		data_list = [None] * 366
		for r in rows:
			d_idx = r[0] # D 是索引 (第幾天)
			if 0 <= d_idx < 366:
				# 解析 X (Extra data) JSON 字串並合併
				extra = json.loads(r[6]) if r[6] else {}
				day_data = {
					"C": r[1], "O": r[2], "H": r[3], "L": r[4], "V": r[5]
				}
				day_data.update(extra)
				data_list[d_idx] = day_data
		
		conn.close()

		if json_path:
			full_json_path = os.path.join(self.db_root, json_path)
			async with aiofiles.open(full_json_path, mode='w') as f:
				await f.write(json.dumps(data_list))
			# 轉換完成後刪除 DB
			if os.path.exists(db_path):
				os.remove(db_path)
		
		return data_list

	async def schedule_task(self, symbol, year, begin):
		"""設定 Syncer 資料並觸發之"""
		with sqlite3.connect(self.syncer_db) as conn:
			cursor = conn.cursor()
			# 檢查是否已有相同任務在進行或待命
			cursor.execute("SELECT task_id FROM tasks WHERE symbol=? AND year=? AND (status='Pending' OR status='Running')", (symbol, year))
			if cursor.fetchone():
				return False

			cursor.execute("INSERT INTO tasks (symbol, year, begin, status) VALUES (?, ?, ?, 'Pending')", 
						   (symbol, year, begin))
			conn.commit()

		# 向 Worker 發送 SIGUSR1 信號
		if self.worker_pid:
			try:
				os.kill(self.worker_pid, signal.SIGUSR1)
				print(f"發送 SIGUSR1 至 Worker (PID: {self.worker_pid})")
			except ProcessLookupError:
				print(f"錯誤: 找不到 PID {self.worker_pid} 的行程")
		else:
			print("警告: 尚未偵測到運行的 Worker PID")
		return True

	async def prepare_data(self, symbol, year):
		"""準備要回應請求的資料"""
		this_year = datetime.now().year
		json_file = f"{symbol}_{year}.json"
		db_file = f"{symbol}_{year}.db"
		
		json_path = os.path.join(self.db_root, json_file)
		db_path = os.path.join(self.db_root, db_file)

		if year != this_year:
			if os.path.exists(json_path):
				async with aiofiles.open(json_path, mode='r') as f:
					return json.loads(await f.read())
			
			if os.path.exists(db_path):
				return await self.db2json(db_file, json_file)
			
			await self.schedule_task(symbol, year, 0)
			return "Pending"
		else:
			# 當年度處理
			max_date = 0
			if os.path.exists(db_path):
				with sqlite3.connect(db_path) as conn:
					res = conn.execute("SELECT MAX(D) FROM price_data").fetchone()
					max_date = res[0] if res and res[0] is not None else 0
			
			today_day_of_year = datetime.now().timetuple().tm_yday
			if os.path.exists(db_path) and max_date >= today_day_of_year - 1:
				return await self.db2json(db_file) # 不轉 json 檔，因為還會更新
			
			await self.schedule_task(symbol, year, max_date)
			return "Pending"

	async def handle_get_data(self, request):
		"""處理前端資料請求: ?2330_TW-2025"""
		query = request.query_string
		try:
			tid, yid = query.split('-')
			data = await self.prepare_data(tid, int(yid))
			return web.json_response({"status": "Success", "data": data})
		except Exception as e:
			return web.json_response({"status": "Error", "message": str(e)}, status=400)

	async def handle_get_task(self, request):
		"""處理 Worker 任務要求"""
		with sqlite3.connect(self.syncer_db) as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT task_id, symbol, year, begin FROM tasks WHERE status='Pending' LIMIT 1")
			row = cursor.fetchone()
			
			if row:
				task_id, symbol, year, begin = row
				cursor.execute("UPDATE tasks SET status='Running' WHERE task_id=?", (task_id,))
				conn.commit()
				return web.json_response({
					"TaskID": task_id, 
					"Script": "yfinance_worker",
					"Args": { "Symbol": symbol, "Year": year, "Begin": begin, "Interval": "1d" }
				})
		return web.json_response({})

	async def handle_commit_task(self, request):
		"""處理 Worker 任務回報"""
		payload = await request.json()
		task_id = request.query.get("taskID")
		data = payload.get("data") # 假設 Worker 把結果放在 data 欄位，失敗則為 "FAILED"

		with sqlite3.connect(self.syncer_db) as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT symbol, year FROM tasks WHERE task_id=?", (task_id,))
			task_info = cursor.fetchone()
			
			if not task_info:
				return web.json_response({"status": "Error", "message": "Task not found"}, status=404)
			
			symbol, year = task_info

			if data == "FAILED":
				cursor.execute("SELECT status FROM tasks WHERE task_id=?", (task_id,))
				status = cursor.fetchone()[0]
				rc = int(status) if status.isdigit() else 0
				
				if rc < self.max_syncer_retry:
					cursor.execute("UPDATE tasks SET status=? WHERE task_id=?", (str(rc + 1), task_id))
					conn.commit()
					return web.json_response({"status": "Retrying"})
				
				cursor.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
				conn.commit()
			else:
				# 寫入資料到對應的股票 DB
				db_name = f"{symbol}_{year}.db"
				db_path = os.path.join(self.db_root, db_name)
				
				with sqlite3.connect(db_path) as data_conn:
					data_conn.execute("""
						CREATE TABLE IF NOT EXISTS price_data (
							D INTEGER PRIMARY KEY, C REAL, O REAL, H REAL, L REAL, V INTEGER, X TEXT
						)
					""")
					for item in data:
						# 這裡假設 Worker 回傳格式符合表格欄位
						# 處理 X 欄位：扣除基本欄位後轉 JSON
						base_keys = {'D', 'C', 'O', 'H', 'L', 'V'}
						extra_data = {k: v for k, v in item.items() if k not in base_keys}
						data_conn.execute(
							"INSERT OR REPLACE INTO price_data (D, C, O, H, L, V, X) VALUES (?,?,?,?,?,?,?)",
							(item['D'], item['C'], item['O'], item['H'], item['L'], item['V'], json.dumps(extra_data))
						)
					data_conn.commit()

				cursor.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
				conn.commit()

				# 如果是往年資料，立即轉為 JSON
				if year < datetime.now().year:
					await self.db2json(db_name, f"{symbol}_{year}.json")

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
