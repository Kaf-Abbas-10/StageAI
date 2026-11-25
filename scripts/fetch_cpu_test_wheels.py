"""Fetch optional test wheels from canonical PyPI, avoiding broken local caches."""
import json
import urllib.request
import subprocess
from pathlib import Path

out=Path(__file__).resolve().parents[1]/'.tools/wheels';out.mkdir(parents=True,exist_ok=True)
for package,version,tag in [('opencv-python-headless','4.11.0.86','cp37-abi3-win_amd64'),('fast-simplification','0.1.11','cp313-cp313-win_amd64'),('xatlas','0.0.11','cp313-cp313-win_amd64')]:
    with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=30) as r:metadata=json.load(r)
    files=[f for f in metadata['urls'] if tag in f['filename']]
    if not files:raise RuntimeError(f'No compatible wheel for {package} {version} ({tag})')
    f=files[0];dest=out/f['filename']
    print('Downloading',f['filename'],flush=True)
    # Some Windows networks advertise broken IPv6 routes for the wheel CDN.
    for attempt in range(4):
        if dest.exists() and dest.stat().st_size==f['size']:break
        command=['curl.exe','-4','--fail','--location','--connect-timeout','10','--max-time','90','--silent','--show-error','--output',str(dest)]
        if dest.exists():command+=['--continue-at','-']
        result=subprocess.run(command+[f['url']])
        if result.returncode==0:break
        if result.returncode!=28:raise RuntimeError(f'Download failed: curl exit {result.returncode}')
        print('Slow download; retained bytes for a bounded resumed attempt.',flush=True)
    content=dest.read_bytes()
    import hashlib
    if hashlib.sha256(content).hexdigest()!=f['digests']['sha256']:raise RuntimeError('Wheel hash mismatch')
    dest.write_bytes(content)
    print(len(content),'bytes; SHA-256 verified',flush=True)
