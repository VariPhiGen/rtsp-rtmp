#!/usr/bin/env python3
import subprocess
import time
import signal
import socket
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

RTSP_URL = os.getenv("RTSP_URL")
RTMP_URL = os.getenv("RTMP_URL")
INITIAL_RETRY_DELAY = int(os.getenv("RETRY_INITIAL", 5))
MAX_RETRY_DELAY = int(os.getenv("RETRY_MAX", 60))

if not RTSP_URL or not RTMP_URL:
    raise ValueError("RTSP_URL and RTMP_URL must be defined in .env file")

def check_port(host, port, timeout=3):
    """Check if a host:port is reachable"""
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception:
        return False

def parse_host_port(url, default_port):
    """Parse host and port from RTSP/RTMP URL"""
    host = url.split("//")[1].split("/")[0]
    if ":" in host:
        h, p = host.split(":")
        return h, int(p)
    return host, default_port

def start_ffmpeg():
    """Start ffmpeg process"""
    return subprocess.Popen([
        "ffmpeg",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-rtsp_transport", "tcp",
        "-i", RTSP_URL,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        RTMP_URL,
        "-loglevel", "error"
    ])

def stream_forever():
    retry_delay = INITIAL_RETRY_DELAY
    rtsp_host, _ = parse_host_port(RTSP_URL, 554)
    rtmp_host, rtmp_port = parse_host_port(RTMP_URL, 1935)

    while True:
        if not check_port(rtsp_host, 554):
            print(f"⚠️ RTSP offline. Retrying in {retry_delay}s…")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            continue

        if not check_port(rtmp_host, rtmp_port):
            print(f"⚠️ RTMP server unreachable. Retrying in {retry_delay}s…")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            continue

        print("🚀 Streaming RTSP → RTMP…")
        process = start_ffmpeg()
        process.wait()

        print("❌ Stream lost! Reconnecting…")
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)

def shutdown(*args):
    print("🛑 Service stopped.")
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    stream_forever()
