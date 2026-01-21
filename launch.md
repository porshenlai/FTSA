沒問題，針對 **Linux (Systemd)** 與 **Windows (PowerShell)** 的背景服務管理，我們需要分別建立其專屬的設定方式。

這套設計會確保您的 `Worker` 在開機時自動啟動，並在崩潰時自動重啟，同時將 PID（進程識別碼）紀錄於固定位置，方便您的 `Hub Server` 透過 `SIGUSR1` 進行喚醒。

---

### 1. Linux: Systemd Service 設定檔

請將以下內容存為 `/etc/systemd/system/fsta-worker.service`（FSTA 為 Financial Series Token Analyzer 縮寫）。

```ini
[Unit]
Description=FSTA Background Worker Service
After=network.target

[Service]
# gemini-helpme: 請根據實際路徑修改 User 與 WorkingDirectory
Type=simple
User=your_username
WorkingDirectory=/path/to/your/project/worker
ExecStart=/usr/bin/python3 worker_app.py
Restart=always
RestartSec=5

# 將 PID 寫入檔案，方便 Hub Server 讀取發送信號
PIDFile=/tmp/fsta_worker.pid
ExecStartPost=/bin/sh -c 'echo $MAINPID > /tmp/fsta_worker.pid'

[Install]
WantedBy=multi-user.target

```

**啟用指令：**

```bash
sudo systemctl daemon-reload
sudo systemctl enable fsta-worker.service
sudo systemctl start fsta-worker.service

```

---

### 2. Windows: PowerShell 啟動與管理腳本

Windows 原生服務設定較為繁瑣，通常建議使用 `nssm` 或直接透過 PowerShell 腳本包裝。以下提供一個 `Start-Worker.ps1`，它會啟動 Worker、記錄 PID 並在背景執行。

```powershell
# gemini-helpme: Start-Worker.ps1
# 1. 啟動 Python Worker
# 2. 將 PID 存入 worker.pid 供 Hub Server 讀取
# 3. 確保不重複啟動

$PidFile = Join-Path $PSScriptRoot "worker.pid"

# 檢查是否已有運行中的 Worker
if (Test-Path $PidFile) {
    $OldPid = Get-Content $PidFile
    if (Get-Process -Id $OldPid -ErrorAction SilentlyContinue) {
        Write-Host "Worker 已經在執行中 (PID: $OldPid)" -ForegroundColor Yellow
        exit
    }
}

# 啟動 Worker 並隱藏視窗 (或使用虛擬終端)
$Process = Start-Process python -ArgumentList "worker_app.py" -WindowStyle Hidden -PassThru

# 紀錄 PID
$Process.Id | Out-File $PidFile -Encoding ascii

Write-Host "Worker 已啟動，PID: $($Process.Id)" -ForegroundColor Green

```

---

### 3. 技術整合說明

為了讓您的 **Hub Server** 能同時在兩個平台上順利發送 `SIGUSR1`（注意：Windows 原生不支援 SIGUSR1，通常需透過傳遞其他事件或 Socket 通知，但 Python 在 Windows 上可以模擬特定信號），您的 Python 代碼可以這樣讀取 PID：

```python
## gemini-helpme: 跨平台讀取 PID 並發送喚醒通知
def get_worker_pid():
    pid_path = "/tmp/fsta_worker.pid" if os.name != 'nt' else "worker.pid"
    if os.path.exists(pid_path):
        with open(pid_path, 'r') as f:
            return int(f.read().strip())
    return None

def wake_up_worker():
    pid = get_worker_pid()
    if pid:
        if os.name != 'nt':
            os.kill(pid, signal.SIGUSR1)
        else:
            # Windows 下的替代方案：可以使用特定 event 或簡單的 UDP ping
            print(f"Windows 下喚醒 PID: {pid}")

```

### 接下來的建議

您的安裝與服務化腳本已經完備。隨著您即將進入「實際開發階段」，**您是否需要我幫您準備第一份測試用的「資料抓取 Task JSON」範例，以及對應的 Python 爬蟲解析結構？** 這能讓您在建立好伺服器後立即進行端對端的測試。
