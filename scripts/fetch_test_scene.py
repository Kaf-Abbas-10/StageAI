"""Download a real photograph and optional official reconstruction for QA only.

The photograph is by Spacejoy on Unsplash, credited in upstream README.
These fixtures are not used as reconstructed results by the application.
"""
import json
import re
import urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]
fixture=root/"tests/fixtures";fixture.mkdir(exist_ok=True)
out=root/"test-results";out.mkdir(exist_ok=True)
base="https://adamrolander.github.io/worldbuilder-demo/"
for url,path in [(base+"assets/living-room-photo.jpg",fixture/"living-room.jpg"),(base+"living-room/scene_lite.glb",out/"official-living-room.glb")]:
    if not path.exists():
        print("Downloading",url,flush=True)
        path.write_bytes(urllib.request.urlopen(url,timeout=180).read())
    print(path.name,path.stat().st_size,flush=True)
html=urllib.request.urlopen(base+"living-room/",timeout=60).read().decode()
layout=json.loads(re.search(r"const LAYOUT\s*=\s*(\{.*?\});",html).group(1))
(out/"official-layout.json").write_text(json.dumps(layout,indent=2),encoding="utf-8")
print("Upstream metres per unit:",layout["estimated_metric_scale"])
