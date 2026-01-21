import asyncio
import signal
import sys
import os

## gemini-helpme:
## 1. 監聽 SIGUSR1 信號。
## 2. 接收信號後，透過 API 向 Hub 索取任務。
## 3. 執行完畢後透過 POST API 回報結果。

class WorkerApp:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.is_processing = False

    def handle_signal(self):
        """SIGUSR1 信號處理程式"""
        print("收到 SIGUSR1: 喚醒並檢查工作池...")
        if not self.is_processing:
            asyncio.ensure_future(self.process_tasks())

    async def process_tasks(self):
        self.is_processing = True
        
        # 模擬向 Hub 索取工作 (GET /tasks/next)
        print("Worker: 正在執行任務...")
        await asyncio.sleep(2) # 模擬爬蟲執行時間
        
        # 模擬回報任務 (POST /api/commit)
        print("Worker: 任務完成，回報結果。")
        
        self.is_processing = False
        print("Worker: 進入休眠模式。")

    def run(self):
        # 註冊信號
        signal.signal(signal.SIGUSR1, lambda sig, frame: self.handle_signal())
        print(f"Worker 已啟動，PID: {os.getpid()}")
        print("等待 SIGUSR1 信號中...")
        self.loop.run_forever()

if __name__ == "__main__":
    worker = WorkerApp()
    worker.run()
