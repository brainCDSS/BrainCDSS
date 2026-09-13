"""PID 1 supervisor for the public FastAPI gateway and internal MOSEC server."""

import os
import signal
import subprocess
import sys
import time


def main():
    env = os.environ.copy()
    public_port = env.get("PORT", "8100")
    mosec_port = env.get("MOSEC_PORT", "8101")
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "src.mosec_server", "--host", "127.0.0.1", "--port", mosec_port],
            env=env,
        ),
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", public_port],
            env=env,
        ),
    ]

    def stop(_signum=None, _frame=None):
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    finally:
        stop()
        for process in processes:
            process.wait(timeout=15)
    return next((process.returncode for process in processes if process.returncode), 0)


if __name__ == "__main__":
    raise SystemExit(main())
