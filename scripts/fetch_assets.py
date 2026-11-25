"""Fetch pinned, MIT licensed viewer dependencies once; runtime is offline."""
import urllib.request
from pathlib import Path

base=Path(__file__).resolve().parents[1]/"stageai/static/vendor"
files={
    "three.module.js":"build/three.module.js",
    "OrbitControls.js":"examples/jsm/controls/OrbitControls.js",
    "TransformControls.js":"examples/jsm/controls/TransformControls.js",
    "GLTFLoader.js":"examples/jsm/loaders/GLTFLoader.js",
    "GLTFExporter.js":"examples/jsm/exporters/GLTFExporter.js",
    "BufferGeometryUtils.js":"examples/jsm/utils/BufferGeometryUtils.js",
    "TextureUtils.js":"examples/jsm/utils/TextureUtils.js",
    "THREE-LICENSE.txt":"LICENSE",
}
base.mkdir(parents=True,exist_ok=True)
for name,source in files.items():
    url="https://cdn.jsdelivr.net/npm/three@0.160.0/"+source
    content=urllib.request.urlopen(url,timeout=90).read()
    if name=="GLTFLoader.js":content=content.replace(b"../utils/BufferGeometryUtils.js",b"./BufferGeometryUtils.js")
    if name=="GLTFExporter.js":content=content.replace(b"./../utils/TextureUtils.js",b"./TextureUtils.js")
    (base/name).write_bytes(content)
    print(name,len(content))

