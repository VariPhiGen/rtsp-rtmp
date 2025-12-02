#!/bin/bash

SERVICE_NAME="rtsp-stream"
USER_NAME=$(logname 2>/dev/null || whoami)
BASE_DIR="/home/$USER_NAME/rtsp-service"
PY_FILE="$BASE_DIR/rtsp_to_rtmp.py"
ENV_FILE="$BASE_DIR/.env"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=== Installing dependencies ==="
sudo apt update
sudo apt install -y ffmpeg python3 python3-pip
pip3 install python-dotenv

echo "=== Creating directory at $BASE_DIR ==="
mkdir -p $BASE_DIR

echo "=== Copy your rtsp_to_rtmp.py and .env here ==="
cp rtsp_to_rtmp.py $BASE_DIR/
cp .env $BASE_DIR/

chmod +x $PY_FILE

echo "=== Creating systemd service ==="
cat << EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=RTSP to RTMP Streamer Service
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $PY_FILE
Restart=always
RestartSec=3
EnvironmentFile=$ENV_FILE
StandardOutput=append:/var/log/rtsp_stream.log
StandardError=append:/var/log/rtsp_stream_error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "=== INSTALLATION COMPLETE ==="
echo "Edit URLs in: $ENV_FILE"
echo "Check status using: sudo systemctl status rtsp-stream"
echo "Logs: tail -f /var/log/rtsp_stream.log"
