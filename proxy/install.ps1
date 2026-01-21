# 取得目前腳本所在的目錄路徑
$CWD = Split-Path -Parent $MyInvocation.MyCommand.Path

# 取得網頁根目錄的絕對路徑 (假設在腳本上一層的 web 目錄)
$WebRoot = [System.IO.Path]::GetFullPath((Join-Path $CWD "..\web\"))

# 格式化 Nginx 設定內容
$NginxCfg = @"
	// Please copy the following section to nginx cfg file to replace the default web root setting.

	location / {
		root "$($WebRoot.Replace('\', '/'))";
		add_header 'Access-Control-Allow-Origin' '*';
		add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
		add_header 'Access-Control-Allow-Headers' 'Range, Content-Type';
		add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		types {
			application/json json;
			application/octet-stream bin;
		}
	}

	# 將 /_fs_/path 重寫為 /api/path 並轉發至 8081
	location /_fs_/ {
		rewrite ^/_fs_/(.*)$ /api/`$1 break;
		proxy_pass http://localhost:8081;
		proxy_set_header Host `$host;
		proxy_set_header X-Real-IP `$remote_addr;
	}

	# 將 /_ts_/path 重寫為 /api/path 並轉發至 8082
	location /_ts_/ {
		rewrite ^/_ts_/(.*)$ /api/`$1 break;
		proxy_pass http://localhost:8082;
		proxy_set_header Host `$host;
		proxy_set_header X-Real-IP `$remote_addr;
	}
"@

# 輸出到控制台
Write-Output $NginxCfg
