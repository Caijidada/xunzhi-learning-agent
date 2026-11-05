"""Start the local API and Vue dev server; Ctrl+C stops both."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not (ROOT / 'web/node_modules').exists():
        sys.exit('请先运行 npm --prefix web ci')
    children = []
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server.app.main:app', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT, start_new_session=True))
        children.append(subprocess.Popen(['npm', '--prefix', 'web', 'run', 'dev'], cwd=ROOT, start_new_session=True))
        print('循知启动中：http://127.0.0.1:5173/  |  Ctrl+C 停止', flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in children:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
        for p in children:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()


if __name__ == '__main__':
    main()
