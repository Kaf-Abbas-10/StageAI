from __future__ import annotations

import io
import json
import os
import threading
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from stageai.models import Reconstruction, SceneState
from stageai.pipeline import ROOT, PipelineError, guided, preflight, run_worldbuilder
from stageai.storage import ASSET_RE, ID_RE, atomic_json, import_glb, validate_assets, validate_glb

MAX_IMAGE=25*1024*1024
MAX_GLB=150*1024*1024
Image.MAX_IMAGE_PIXELS=30_000_000


def now():return datetime.now(timezone.utc).isoformat()


def create_app(data_dir=None):
    data=Path(data_dir or os.environ.get("STAGEAI_DATA",ROOT/"data")).resolve()
    data.mkdir(parents=True,exist_ok=True)
    executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix="room-reconstruction")
    jobs={}
    lock=threading.RLock()

    def project(pid):
        if not ID_RE.fullmatch(pid):raise HTTPException(404,"Unknown project")
        p=data/pid
        if not p.is_dir():raise HTTPException(404,"Unknown project")
        return p

    def get_scene(p):
        if not (p/"scene.json").is_file():raise HTTPException(404,"Project has no scene yet")
        return json.loads((p/"scene.json").read_text(encoding="utf-8"))

    def update_job(pid,**changes):
        with lock:
            jobs[pid].update(changes,updated_at=now())
            atomic_json(data/pid/"job.json",jobs[pid])

    def run(pid,settings):
        p=data/pid
        def progress(stage,message,fraction):
            update_job(pid,status="running",stage=stage,message=message,progress=fraction)
        try:
            if settings.mode=="worldbuilder":
                glb,scale,layout=run_worldbuilder(p,settings,progress)
                state=import_glb(p,glb.read_bytes(),scale,"worldbuilder")
                rec=json.loads((p/"worldbuilder/reconstruction_results.json").read_text())
                state["settings"].update(settings.model_dump())
                state["settings"]["upstream_layout"]=layout
                if settings.dimensions.source=="user-measured":
                    desired=settings.dimensions.model_dump()
                    factors=[desired["width"]/state["room"]["width"],desired["height"]/state["room"]["height"],desired["depth"]/state["room"]["depth"]]
                    for obj in state["objects"]:
                        obj["position"]=[v*f for v,f in zip(obj["position"],factors)]
                        obj["dimensions"]=[v*f for v,f in zip(obj["dimensions"],factors)]
                    state["room"]=desired
                    state["warnings"].append("Scene bounds were calibrated to your supplied dimensions by scaling each room axis. Local object geometry remains estimated.")
                state["warnings"].extend(f"Object reconstruction failed: {x}" for x in rec.get("failed",[])[:100])
                state["warnings"].append("Scale is predicted from monocular depth or camera-height priors, not a measured room dimension.")
            else:
                state=guided(p,settings,progress)
            checked=SceneState.model_validate(state)
            validate_assets(checked,p)
            atomic_json(p/"scene.json",checked.model_dump())
            update_job(pid,status="complete",stage="complete",message="Guided room ready" if settings.mode=="guided" else "WorldBuilder reconstruction completed",progress=1,warnings=state["warnings"])
        except Exception as exc:
            e=exc if isinstance(exc,PipelineError) else PipelineError("processing_failed",str(exc),"Review the selected image and settings. See docs/TROUBLESHOOTING.md.")
            update_job(pid,status="failed",stage="failed",message=str(e),error={"code":e.code,"message":str(e),"fix":e.fix})

    @asynccontextmanager
    async def lifespan(app):
        for f in data.glob("*/job.json"):
            try:
                j=json.loads(f.read_text(encoding="utf-8"))
                if j.get("status") in ("running","queued"):
                    j.update(status="failed",error={"code":"server_restarted","message":"The server stopped during processing.","fix":"Open this project's preserved photograph and start reconstruction again."})
                    atomic_json(f,j)
            except (OSError,ValueError):pass
        yield
        executor.shutdown(wait=False,cancel_futures=True)

    app=FastAPI(title="StageAI local room studio",version="1.0.0",lifespan=lifespan)
    app.state.data_dir=data
    app.state.executor=executor

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request,exc):
        # Do not echo non-finite input into JSONResponse (which would itself
        # throw while trying to serialize NaN/Infinity in a validation error).
        return JSONResponse(status_code=422,content={"detail":[{"loc":list(e["loc"]),"msg":e["msg"],"type":e["type"]} for e in exc.errors()]})

    @app.middleware("http")
    async def local_mutations(request,call_next):
        origin=request.headers.get("origin")
        if request.method in ("POST","PUT","DELETE","PATCH") and origin:
            if urlsplit(origin).netloc!=request.headers.get("host"):
                return Response("Cross-origin mutation blocked",status_code=403)
        response=await call_next(request)
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    async def read_limited(file,limit):
        content=await file.read(limit+1)
        if len(content)>limit:raise HTTPException(413,f"File exceeds {limit//1024//1024} MB limit")
        return content

    @app.get("/api/health")
    def health():return {"ok":True,"version":"1.0.0"}

    @app.get("/api/capabilities")
    def capabilities():return preflight()

    @app.post("/api/projects/upload",status_code=201)
    async def upload(image:UploadFile=File(...)):
        if Path(image.filename or "").suffix.lower() not in (".jpg",".jpeg",".png",".webp"):
            raise HTTPException(415,"Choose a JPG, JPEG, PNG, or WebP photograph")
        content=await read_limited(image,MAX_IMAGE)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error",Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as im:
                    if im.format not in ("JPEG","PNG","WEBP"):raise ValueError("Image content must be JPEG, PNG, or WebP")
                    if min(im.size)<64:raise ValueError("Image must be at least 64 pixels on each side")
                    dims=im.size
                    im.verify()
                with Image.open(io.BytesIO(content)) as decoded:
                    decoded.load()
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning) as e:
            raise HTTPException(422,f"Invalid image: {e}") from e
        pid=uuid.uuid4().hex
        p=data/pid;p.mkdir()
        (p/"original").write_bytes(content)
        atomic_json(p/"metadata.json",{"filename":Path(image.filename).name,"uploaded_at":now(),"image_size":dims})
        return {"id":pid,"image_url":f"/api/projects/{pid}/assets/original","image_size":dims}

    @app.post("/api/projects/{pid}/reconstruct",status_code=202)
    def reconstruct(pid:str,settings:Reconstruction):
        p=project(pid)
        if not (p/"original").is_file():raise HTTPException(400,"This project has no photograph. Upload a photograph first.")
        with lock:
            active=[j for j in jobs.values() if j["status"] in ("queued","running")]
            if any(j["id"]==pid for j in active):raise HTTPException(409,"This project is already processing")
            if len(active)>=3:raise HTTPException(429,"Three jobs are already queued. Wait for one to finish.")
            jobs[pid]={"id":pid,"status":"queued","stage":"queued","message":"Waiting for the local worker","progress":0,"mode":settings.mode,"created_at":now(),"error":None}
            atomic_json(p/"job.json",jobs[pid])
            atomic_json(p/"reconstruction.json",settings.model_dump())
            executor.submit(run,pid,settings)
            return jobs[pid].copy()

    @app.get("/api/projects/{pid}/job")
    def job(pid:str):
        p=project(pid)
        with lock:
            if pid in jobs:return jobs[pid].copy()
        if (p/"job.json").is_file():return json.loads((p/"job.json").read_text(encoding="utf-8"))
        raise HTTPException(404,"No reconstruction job for this project")

    @app.get("/api/projects")
    def projects():
        out=[]
        for f in data.glob("*/scene.json"):
            try:
                s=json.loads(f.read_text(encoding="utf-8"))
                out.append({"id":f.parent.name,"name":s["name"],"provenance":s["provenance"],"objects":len(s["objects"]),"modified":f.stat().st_mtime})
            except (OSError,ValueError,KeyError):pass
        return sorted(out,key=lambda x:-x["modified"])

    @app.post("/api/projects",status_code=201)
    def blank():
        pid=uuid.uuid4().hex;p=data/pid;p.mkdir()
        state=SceneState(name="Untitled room",warnings=["Manual room: dimensions are estimated until you supply measurements."]).model_dump()
        atomic_json(p/"scene.json",state)
        return {"id":pid,"scene":state}

    @app.get("/api/projects/{pid}")
    def load(pid:str):
        p=project(pid)
        return {"id":pid,"scene":get_scene(p),"has_original":(p/"original").is_file()}

    @app.put("/api/projects/{pid}")
    def save(pid:str,scene:SceneState):
        p=project(pid)
        with lock:
            if jobs.get(pid,{}).get("status") in ("running","queued"):
                raise HTTPException(409,"Wait for reconstruction before saving")
        try:validate_assets(scene,p)
        except ValueError as e:raise HTTPException(422,str(e)) from e
        atomic_json(p/"scene.json",scene.model_dump())
        return {"id":pid,"saved_at":now()}

    @app.get("/api/projects/{pid}/assets/{name}")
    def asset(pid:str,name:str):
        p=project(pid)
        if not ASSET_RE.fullmatch(name) or not (p/name).is_file():raise HTTPException(404,"Unknown asset")
        mime=None
        if name=="original":
            with Image.open(p/name) as im:mime=Image.MIME.get(im.format,"application/octet-stream")
        return FileResponse(p/name,media_type=mime)

    @app.post("/api/import/glb",status_code=201)
    async def glb_import(file:UploadFile=File(...),scale:float=1):
        if not .0001<=scale<=10000:raise HTTPException(422,"Scale must be .0001..10000 metres per unit")
        content=await read_limited(file,MAX_GLB)
        pid=uuid.uuid4().hex;p=data/pid;p.mkdir()
        try:state=await run_in_threadpool(import_glb,p,content,scale)
        except Exception as e:raise HTTPException(422,f"GLB import failed: {e}") from e
        atomic_json(p/"scene.json",state)
        return {"id":pid,"scene":state}

    @app.post("/api/projects/{pid}/export")
    async def export(pid:str,file:UploadFile=File(...)):
        project(pid)
        content=await read_limited(file,MAX_GLB)
        try:await run_in_threadpool(validate_glb,content)
        except Exception as e:raise HTTPException(422,f"Export validation failed: {e}") from e
        return Response(content,media_type="model/gltf-binary",headers={"Content-Disposition":'attachment; filename="stageai-room.glb"'})

    @app.get("/api/projects/{pid}/bundle")
    def bundle(pid:str):
        p=project(pid);scene=SceneState.model_validate(get_scene(p));validate_assets(scene,p)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("scene.json",json.dumps(scene.model_dump(),indent=2))
            refs={"original","prepared.jpg","metadata.json","reconstruction.json",scene.floor_texture}
            refs.update(o.asset for o in scene.objects)
            for name in sorted(x for x in refs if x):
                if (p/name).is_file():z.write(p/name,name)
        return Response(buf.getvalue(),media_type="application/zip",headers={"Content-Disposition":'attachment; filename="room.stageai"'})

    @app.post("/api/import/project",status_code=201)
    async def import_project(file:UploadFile=File(...)):
        content=await read_limited(file,250*1024*1024)
        pid=uuid.uuid4().hex;p=data/pid
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                entries=z.infolist()
                if len(entries)>1600 or sum(e.file_size for e in entries)>500*1024*1024:raise ValueError("Project is too large")
                names=[e.filename for e in entries]
                if len(names)!=len(set(names)):raise ValueError("Duplicate entries in project")
                for name in names:
                    if name not in ("scene.json","metadata.json","reconstruction.json") and not ASSET_RE.fullmatch(name):raise ValueError("Invalid file in project archive")
                if "scene.json" not in names or z.getinfo("scene.json").file_size>5*1024*1024:raise ValueError("Missing or oversized scene.json")
                state=SceneState.model_validate_json(z.read("scene.json"))
                for ref in [state.floor_texture]+[o.asset for o in state.objects]:
                    if ref and (not ASSET_RE.fullmatch(ref) or ref not in names):raise ValueError("Missing project asset")
                p.mkdir()
                for name in names:
                    payload=z.read(name)
                    if name.endswith(".glb"):validate_glb(payload)
                    if name in ("original","prepared.jpg","floor.png"):
                        with Image.open(io.BytesIO(payload)) as im:im.verify()
                    (p/name).write_bytes(payload)
                validate_assets(state,p)
                atomic_json(p/"scene.json",state.model_dump())
        except Exception as e:
            # Invalid archives never become listed projects.
            (p/"scene.json").unlink(missing_ok=True) if p.exists() else None
            raise HTTPException(422,f"Project import failed: {e}") from e
        return {"id":pid,"scene":state.model_dump()}

    static=ROOT/"stageai/static"
    app.mount("/",StaticFiles(directory=static,html=True),name="studio")
    return app


app=create_app()

