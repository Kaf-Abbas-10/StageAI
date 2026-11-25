import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient
from PIL import Image

from stageai.models import Reconstruction, SceneState
from stageai.pipeline import PipelineError, classify_failure, preflight
from stageai.server import create_app
from stageai.storage import validate_glb
from stageai.pipeline import project_floor


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:yield c


def photo(fmt="JPEG"):
    b=io.BytesIO();Image.new("RGB",(640,480),(150,120,80)).save(b,fmt);return b.getvalue()


def upload(c,content=None,name="room.jpg"):
    r=c.post("/api/projects/upload",files={"image":(name,content if content is not None else photo())})
    assert r.status_code==201,r.text
    return r.json()["id"]


def wait(c,pid):
    for _ in range(200):
        j=c.get(f"/api/projects/{pid}/job").json()
        if j["status"] in ("complete","failed"):return j
        time.sleep(.025)
    raise AssertionError("Job never finished")


def simple_glb():
    scene=trimesh.Scene()
    for name,x in [("001_chair",-1),("002_table",1)]:
        mesh=trimesh.creation.box([.6,.8,.6]);mesh.apply_translation([x,.4,0]);scene.add_geometry(mesh,node_name=name,geom_name=name)
    return scene.export(file_type="glb")


def test_health_static_and_local_assets(client):
    assert client.get("/api/health").json()["ok"]
    assert "Room studio" in client.get("/").text
    for asset in ("three.module.js","GLTFLoader.js","GLTFExporter.js","TextureUtils.js","THREE-LICENSE.txt"):
        assert client.get("/vendor/"+asset).status_code==200


@pytest.mark.parametrize("fmt,name",[("JPEG","a.jpg"),("JPEG","a.JPEG"),("PNG","a.png"),("WEBP","a.webp")])
def test_image_formats_preserve_original(client,fmt,name):
    content=photo(fmt);pid=upload(client,content,name)
    assert client.get(f"/api/projects/{pid}/assets/original").content==content


@pytest.mark.parametrize("content,name,status",[(b"not an image","a.jpg",422),(b"<svg/>","a.svg",415),(photo(),"a.exe",415)])
def test_invalid_upload(client,content,name,status):
    assert client.post("/api/projects/upload",files={"image":(name,content)}).status_code==status


def test_truncated_jpeg_content_is_decoded_and_rejected(client):
    content=photo()[:1000]
    assert client.post("/api/projects/upload",files={"image":("truncated.jpg",content)}).status_code==422


def test_guided_image_processing_and_provenance(client):
    content=photo();pid=upload(client,content)
    r=client.post(f"/api/projects/{pid}/reconstruct",json={"rotation":90,"crop":[.1,.1,.9,.9],"dimensions":{"width":6,"depth":4.5,"height":2.8,"source":"user-measured"}})
    assert r.status_code==202
    j=wait(client,pid);assert j["status"]=="complete",j
    scene=client.get(f"/api/projects/{pid}").json()["scene"]
    assert scene["provenance"]=="guided-photo-projection"
    assert scene["room"]["source"]=="user-measured" and scene["room"]["width"]==6
    assert not scene["objects"]  # No fake detected furniture.
    assert any("not AI" in w for w in scene["warnings"])
    im=Image.open(io.BytesIO(client.get(f"/api/projects/{pid}/assets/floor.png").content))
    assert im.size==(768,768)
    prepared=Image.open(io.BytesIO(client.get(f"/api/projects/{pid}/assets/prepared.jpg").content))
    assert prepared.height>prepared.width
    assert client.get(f"/api/projects/{pid}/assets/original").content==content


@pytest.mark.parametrize("payload",[{"crop":[.9,0,.1,1]},{"floor_corners":[[0,0],[1,1],[1,0],[0,1]]},{"floor_corners":[[0,0],[0,0],[0,0],[0,0]]},{"dimensions":{"width":0}},{"quality":"invented"}])
def test_invalid_reconstruction_settings(client,payload):
    pid=upload(client)
    assert client.post(f"/api/projects/{pid}/reconstruct",json=payload).status_code==422


def test_worldbuilder_unavailable_never_substitutes_guided(client,monkeypatch):
    import stageai.pipeline as pipeline
    from stageai import server
    def fail(*args):raise PipelineError("insufficient_vram","8 GB GPU cannot fit supported models","Use guided mode or import an existing GLB")
    monkeypatch.setattr(server,"run_worldbuilder",fail)
    pid=upload(client);client.post(f"/api/projects/{pid}/reconstruct",json={"mode":"worldbuilder"})
    j=wait(client,pid)
    assert j["status"]=="failed" and j["error"]["code"]=="insufficient_vram"
    assert client.get(f"/api/projects/{pid}").status_code==404
    assert client.get(f"/api/projects/{pid}/assets/original").status_code==200


def test_preflight_reports_hardware_platform_and_weights(monkeypatch):
    monkeypatch.delenv("STAGEAI_WB_PYTHON",raising=False)
    result=preflight({"os":"Windows","gpus":[{"total_mb":8192}],"python":"3.13","upstream":True})
    codes={i["code"] for i in result["issues"]}
    assert {"insufficient_vram","unsupported_platform","missing_weights","missing_environment"}<=codes
    assert result["ai_available"] is False


@pytest.mark.parametrize("message,code",[("torch.OutOfMemoryError: CUDA out of memory","gpu_out_of_memory"),("ModuleNotFoundError: No module named 'sam3'","missing_dependency"),("FileNotFoundError: checkpoint missing","missing_weights"),("VLM server unreachable","inference_failed")])
def test_actionable_model_errors(message,code):
    e=classify_failure(message);assert e.code==code and len(e.fix)>30


def test_save_reload_and_portable_project(client):
    pid=upload(client);client.post(f"/api/projects/{pid}/reconstruct",json={});assert wait(client,pid)["status"]=="complete"
    state=client.get(f"/api/projects/{pid}").json()["scene"]
    state["name"]="Edited room"
    state["objects"]=[{"id":"chair_1","name":"Reading chair","kind":"chair","position":[1,0,.4],"rotation":45,"dimensions":[.7,.9,.7],"color":"#779988"}]
    state["camera"]={"position":[4,5,6],"target":[0,0,0]}
    assert client.put(f"/api/projects/{pid}",json=state).status_code==200
    saved=client.get(f"/api/projects/{pid}").json()["scene"]
    assert saved["objects"][0]["rotation"]==45
    bundle=client.get(f"/api/projects/{pid}/bundle")
    z=zipfile.ZipFile(io.BytesIO(bundle.content));assert {"original","floor.png","scene.json"}<=set(z.namelist())
    r=client.post("/api/import/project",files={"file":("room.stageai",bundle.content)})
    assert r.status_code==201,r.text
    other=r.json()["id"]
    assert client.get(f"/api/projects/{other}").json()["scene"]==saved
    assert client.get(f"/api/projects/{other}/assets/original").content==photo()


def test_glb_import_retains_named_independent_meshes_and_transforms(client):
    r=client.post("/api/import/glb?scale=2",files={"file":("room.glb",simple_glb())})
    assert r.status_code==201,r.text
    state=r.json()["scene"];assert len(state["objects"])==2
    assert {o["name"] for o in state["objects"]}=={"001_chair","002_table"}
    assert abs(state["objects"][0]["dimensions"][0]-1.2)<1e-6
    assert abs(state["objects"][0]["position"][0])==pytest.approx(2,abs=1e-6)
    asset=state["objects"][0]["asset"]
    assert validate_glb(client.get(f'/api/projects/{r.json()["id"]}/assets/{asset}').content)
    bundle=client.get(f'/api/projects/{r.json()["id"]}/bundle')
    assert asset in zipfile.ZipFile(io.BytesIO(bundle.content)).namelist()


def test_export_is_valid_glb_reopens_in_trimesh(client):
    pid=client.post("/api/projects").json()["id"]
    r=client.post(f"/api/projects/{pid}/export",files={"file":("room.glb",simple_glb())})
    assert r.status_code==200
    scene=trimesh.load(io.BytesIO(r.content),file_type="glb",force="scene")
    assert len(scene.geometry)==2
    assert client.post(f"/api/projects/{pid}/export",files={"file":("bad.glb",b"broken")}).status_code==422


def test_glb_rejects_external_texture_uri():
    import struct
    raw=simple_glb();chunk=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+chunk]);doc['images']=[{'uri':'https://example.com/secret.png'}]
    text=json.dumps(doc).encode();text+=b' ' *((4-len(text)%4)%4);rest=raw[20+chunk:]
    altered=b'glTF'+struct.pack('<IIII',2,20+len(text)+len(rest),len(text),0x4e4f534a)+text+rest
    with pytest.raises(ValueError,match="external URIs"):validate_glb(altered)


def test_scene_rejects_asset_traversal_and_duplicate_ids(client):
    pid=client.post("/api/projects").json()["id"]
    state=SceneState().model_dump();state["floor_texture"]="../somewhere"
    assert client.put(f"/api/projects/{pid}",json=state).status_code==422
    state["floor_texture"]=None
    obj={"id":"same","name":"chair","kind":"chair","position":[0,0,0],"dimensions":[1,1,1]}
    state["objects"]=[obj,obj]
    assert client.put(f"/api/projects/{pid}",json=state).status_code==422


def test_archive_rejects_zip_slip(client):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        z.writestr("scene.json",SceneState().model_dump_json());z.writestr("../escape.txt","bad")
    assert client.post("/api/import/project",files={"file":("bad.stageai",b.getvalue())}).status_code==422


def test_cross_origin_mutations_rejected(client):
    assert client.post("/api/projects",headers={"Origin":"https://evil.example"}).status_code==403
    assert client.post("/api/projects",headers={"Origin":"http://testserver"}).status_code==201


def test_pending_job_is_failed_after_restart(tmp_path):
    pid="a"*32;p=tmp_path/pid;p.mkdir();(p/"job.json").write_text(json.dumps({"id":pid,"status":"running"}))
    with TestClient(create_app(tmp_path)) as c:
        j=c.get(f"/api/projects/{pid}/job").json()
        assert j["status"]=="failed" and j["error"]["code"]=="server_restarted"


def test_floor_homography_uses_photo_corners_in_correct_order(tmp_path):
    # Independent orientation check: four distinct image quadrants must stay
    # in their corresponding output quadrants, not flip or transpose.
    image=Image.new('RGB',(200,200))
    pixels=np.zeros((200,200,3),dtype=np.uint8)
    pixels[:100,:100]=[255,0,0];pixels[:100,100:]=[0,255,0]
    pixels[100:,100:]=[0,0,255];pixels[100:,:100]=[255,255,0]
    path=tmp_path/'floor.png'
    project_floor(Image.fromarray(pixels),[[0,0],[1,0],[1,1],[0,1]],path)
    out=Image.open(path)
    assert out.getpixel((50,50))==(255,0,0)
    assert out.getpixel((700,50))==(0,255,0)
    assert out.getpixel((700,700))==(0,0,255)
    assert out.getpixel((50,700))==(255,255,0)


def test_upload_size_limit_is_enforced(client,monkeypatch):
    import stageai.server as server
    monkeypatch.setattr(server,'MAX_IMAGE',100)
    assert client.post('/api/projects/upload',files={'image':('large.jpg',b'0'*101)}).status_code==413


def test_nonfinite_scene_metadata_rejected(client):
    pid=client.post('/api/projects').json()['id']
    state=SceneState().model_dump();state['camera']={'zoom':float('nan')}
    body=json.dumps(state)
    assert client.put(f'/api/projects/{pid}',content=body,headers={'Content-Type':'application/json'}).status_code==422


def test_photo_from_official_demo_when_available(client):
    path=Path("tests/fixtures/living-room.jpg")
    if not path.exists():pytest.skip("Fetch optional real-room fixture with scripts/fetch_test_scene.py")
    pid=upload(client,path.read_bytes());client.post(f"/api/projects/{pid}/reconstruct",json={})
    assert wait(client,pid)["status"]=="complete"
    state=client.get(f"/api/projects/{pid}").json()["scene"]
    assert state["floor_texture"]=="floor.png" and state["provenance"]=="guided-photo-projection"

