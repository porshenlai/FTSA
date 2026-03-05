#!/bin/sh
ROOT=$(realpath $0)
ROOT=${ROOT%/*/*}

case $(uname) in
MINGW*)
	SYSD=/tmp
	;;
*)
	SYSD=/etc/systemd/system
	;;
esac

function pip() {
	while True; do
		read cmd
		test "${cmd}" || break
		echo ${cmd#\#}
	done
}
# grep -h '^#pip ' ${ROOT}/services/*.py | pip

# Environment="VIRTUAL_ENV=${ROOT}/venv"
# Environment="PATH=$VIRTUAL_ENV/bin:$PATH"
cat << HUB > ${SYSD}/fsta-hub.service
[Unit]
Description=FS Hub Server
After=network.target

[Service]
WorkingDirectory=${ROOT}
ExecStart=${ROOT}/venv/bin/python3 ${ROOT}/hub_server.py
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
HUB

# WorkingDirectory=${ROOT}
cat << WORKER > ${SYSD}/fsta-worker@.service
[Unit]
Description=FS Worker Instance %i
After=network.target

[Service]
ExecStart=${ROOT}/venv/bin/python3 ${ROOT}/worker_app.py
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
WORKER

# sudo systemctl start fsta-hub
# sudo systemctl start fsta-worker@1
