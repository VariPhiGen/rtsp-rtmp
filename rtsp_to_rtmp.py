#!/usr/bin/env python3
import subprocess
import time
import signal
import socket
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

RTSP_URL = os.getenv("RTSP_URL")
RTMP_URL = os.getenv("RTMP_URL")
INITIAL_RETRY_DELAY = int(os.getenv("RETRY_INITIAL", 5))
MAX_RETRY_DELAY = int(os.getenv("RETRY_MAX", 60))

if not RTSP_URL or not RTMP_URL:
    raise ValueError("RTSP_URL and RTMP_URL must be defined in .env file")


def check_port(host, port, timeout=3):
    """Check if host:port is reachable."""
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except Exception:
        return False


def parse_host_port(url, default_port):
    """Parse host and port from RTSP/RTMP URL safely (handles passwords containing ':')."""
    try:
        # Remove protocol (e.g., rtsp:// or rtmp://)
        after_slashes = url.split("//", 1)[1]

        # Extract host:port part (before first "/")
        host_port = after_slashes.split("/", 1)[0]

        # Use RIGHT SPLIT to avoid breaking passwords that contain ':'
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            return host, int(port)

        return host_port, default_port

    except Exception:
        return None, default_port


def start_ffmpeg():
    """Start FFmpeg process for RTSP → RTMP."""
    print("▶️ Starting FFmpeg stream...")
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
        # Check RTSP camera reachability
        if not check_port(rtsp_host, rtsp_port):
            print(f"⚠️ Camera offline ({rtsp_host}:{rtsp_port}). Retry in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            continue

        # Check RTMP server reachability
        if not check_port(rtmp_host, rtmp_port):
            print(f"⚠️ RTMP server unreachable. Retry in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            continue

        print("🚀 Streaming RTSP → RTMP…")

        process = start_ffmpeg()
        process.wait()  # Wait until FFmpeg exits (network drop, error, etc.)

        print("❌ Stream stopped or lost! Reconnecting…")
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)


def shutdown(*args):
    print("🛑 Service stopped by user.")
    os._exit(0)


if __name__ == "__main__":
    # Gracefully handle Ctrl+C or systemd stop
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    stream_forever()
