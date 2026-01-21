#!/bin/sh

CWD=$(which $0)
CWD=${CWD%/*}

cat << CFG
	// Please copy the following section to nginx cfg file to replace the default web root setting.

	location / {
		root $(realpath ${CWD}/../web/);
		add_header 'Access-Control-Allow-Origin' '*';
		add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
		add_header 'Access-Control-Allow-Headers' 'Range, Content-Type';
		add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		types {
			application/json json;
			application/octet-stream bin;
		}
	}

	# gemini-helpme: 將 /_fs_/path 重寫為 /api/path 並轉發至 8081
	location /_fs_/ {
		rewrite ^/_fs_/(.*)$ /api/\$1 break;
		proxy_pass http://localhost:8081;
		proxy_set_header Host \$host;
		proxy_set_header X-Real-IP \$remote_addr;
	}

	# gemini-helpme: 將 /_ts_/path 重寫為 /api/path 並轉發至 8082
	location /_ts_/ {
		rewrite ^/_ts_/(.*)$ /api/\$1 break;
		proxy_pass http://localhost:8082;
		proxy_set_header Host \$host;
		proxy_set_header X-Real-IP \$remote_addr;
	}
CFG
