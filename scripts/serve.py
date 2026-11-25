"""Single local process; optionally open the browser after HTTP becomes ready."""
import argparse
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=5174);p.add_argument('--open',action='store_true');args=p.parse_args()

def open_when_ready():
    for _ in range(60):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/health',timeout=1) as response:
                if response.status==200:
                    webbrowser.open(f'http://127.0.0.1:{args.port}');return
        except OSError:time.sleep(.5)

if args.open:threading.Thread(target=open_when_ready,daemon=True).start()
uvicorn.run('stageai.server:app',host='127.0.0.1',port=args.port,workers=1)

