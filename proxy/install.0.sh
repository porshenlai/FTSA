#!/bin/sh

CWD=$(which $0)
CWD=${CWD%/*}

cat << CFG
	// Please copy the following section to nginx cfg file to replace the default web root setting.

	location / {
		root $(realpath ${CWD}/../web/);
		add_header 'Access-Control-Allow-Origin' '*';
		add_header 'Access-Control-Allow-Methods' 'GET, OPTIONS';
		add_header 'Access-Control-Allow-Headers' 'Range';
		add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
		types {
			application/json json;
			application/octet-stream bin;
		}
	}

	# gemini-helpme: 請幫我 rewrite url 將 _fs_ 換成 api 後，proxy 到 8081 port
	location /_fs_/ {
		rewrite ...
		proxy_pass http://localhost:8081/api;
	}

	# gemini-helpme: 請幫我 rewrite url 將 _ts_ 換成 api 後，proxy 到 8082 port
	location /_ts_/ {
		rewrite ...
		proxy_pass http://localhost:8082/api;
	}
CFG

