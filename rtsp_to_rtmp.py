#!/usr/bin/env python3
import subprocess
import time
import signal
import socket
import os
from dotenv import load_dotenv

load_dotenv()

RTSP_URL = os.getenv("RTSP_URL")
RTMP_URL = os.getenv("RTMP_URL")
INITIAL_RETRY_DELAY = int(os.getenv("RETRY_INITIAL", 5))
MAX_RETRY_DELAY = int(os.getenv("RETRY_MAX", 60))

if not RTSP_URL or not RTMP_URL:
    raise ValueError("RTSP_URL and RTMP_URL must be defined in .env")


def check_port(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception:
        return False


def parse_host_port(url, default_port):
    """
    Correctly extract host & port from URLs containing username:password@
    Example:
      rtsp://admin:pass@172.16.16.209:554/Streaming/101
    Returns:
      host = 172.16.16.209
      port = 554
    """
    try:
        url = url.split("//", 1)[1]          # remove rtsp://
        url = url.split("@", 1)[-1]          # remove username:password@
        host_port = url.split("/", 1)[0]     # extract host:port

        if ":" in host_port:
            host, port = host_port.split(":")
            return host, int(port)

        return host_port, default_port

    except Exception:
        return None, default_port


def start_ffmpeg():
    return subprocess.Popen([
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-use_wallclock_as_timestamps", "1",
        "-fflags", "+genpts",
        "-i", RTSP_URL,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        RTMP_URL,
        "-loglevel", "error"
    ])


def stream_forever():
    retry_delay = INITIAL_RETRY_DELAY
    rtsp_host, rtsp_port = parse_host_port(RTSP_URL, 554)
    rtmp_host, rtmp_port = parse_host_port(RTMP_URL, 1935)

    print(f"📡 RTSP Host: {rtsp_host}, Port: {rtsp_port}")
    print(f"📡 RTMP Host: {rtmp_host}, Port: {rtmp_port}")

    while True:
        if not check_port(rtsp_host, rtsp_port):
            print(f"⚠️ Camera offline ({rtsp_host}:{rtsp_port}). Retry in {retry_delay}s…")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            continue

        if not check_port(rtmp_host, rtmp_port):
            print(f"⚠️ RTMP server unreachable. Retry in {retry_delay}s…")
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
