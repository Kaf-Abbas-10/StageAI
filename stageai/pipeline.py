"""No model replacement: guided photogrammetric texture projection is explicit.

The generative path executes upstream main.process_image in a separate configured
Python, so its CUDA/NumPy pins cannot contaminate the lightweight editor env.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "WorldBuilder"
GPU_REQUIREMENT_MB = 24000


class PipelineError(RuntimeError):
    def __init__(self, code, message, fix):
        super().__init__(message)
        self.code, self.fix = code, fix


def hardware():
    gpu = []
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=8)
        for line in r.stdout.strip().splitlines():
            name,total,free,driver = [x.strip() for x in line.split(",")]
            gpu.append(dict(name=name,total_mb=int(total),free_mb=int(free),driver=driver))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return {"os":platform.system(),"python":sys.version.split()[0],"gpus":gpu,"upstream":UPSTREAM.exists(),"inference_python_configured":bool(os.environ.get("STAGEAI_WB_PYTHON")),"required_vram_mb":GPU_REQUIREMENT_MB}


def preflight(info=None):
    info = info or hardware()
    problems=[]
    if not info["gpus"] or max(g["total_mb"] for g in info["gpus"]) < GPU_REQUIREMENT_MB:
        problems.append({"code":"insufficient_vram","message":"WorldBuilder's supported full pipeline needs at least 24 GB VRAM; this GPU does not meet that requirement.","fix":"Use guided mode or import an existing WorldBuilder GLB. Full inference needs a compatible Linux NVIDIA machine with 24 GB+; 32 GB is upstream's tested configuration."})
    if info["os"] != "Linux":
        problems.append({"code":"unsupported_platform","message":"SAM 3D Objects' dependencies require Linux x86-64. Native Windows inference is unsupported.","fix":"Run the pipeline on Linux. WSL2 is plausible but upstream has not verified it; WSL does not increase your VRAM."})
    if not os.environ.get("STAGEAI_WB_PYTHON"):
        problems.append({"code":"missing_environment","message":"No WorldBuilder inference environment is configured.","fix":"Follow docs/GPU.md and set STAGEAI_WB_PYTHON to the Linux worldbuilder-main Python executable before launching this server."})
    elif not Path(os.environ["STAGEAI_WB_PYTHON"]).is_file():
        problems.append({"code":"missing_environment","message":"STAGEAI_WB_PYTHON does not point to an existing interpreter.","fix":"Supply the absolute Python executable path in the configured Linux worldbuilder-main environment."})
    for p in [UPSTREAM/"checkpoints/sam3.pt",UPSTREAM/"sam3d_objects_repo/checkpoints/hf/pipeline.yaml"]:
        if not p.is_file():
            problems.append({"code":"missing_weights","message":f"Missing checkpoint: {p.relative_to(UPSTREAM).as_posix()}","fix":"Request access to facebook/sam3 and facebook/sam-3d-objects on Hugging Face, accept their model licenses, then follow upstream docs/SETUP.md. No weights are bundled."})
    return {**info,"ai_available":not problems,"issues":problems}


def prepare_image(source: Path, target: Path, settings):
    with Image.open(source) as raw:
        im = ImageOps.exif_transpose(raw).convert("RGB")
        im = im.rotate(-settings.rotation,expand=True)
        w,h=im.size
        l,t,r,b=settings.crop
        im=im.crop((round(l*w),round(t*h),round(r*w),round(b*h)))
        if min(im.size)<32:
            raise PipelineError("invalid_crop","Cropped image is too small.","Keep at least 32 pixels on each side.")
        im.thumbnail((2560,2560))
        im.save(target,quality=95)
        return im.copy()


def project_floor(im:Image.Image,corners, target:Path):
    """Inverse homography from a user-defined rectangle to photograph pixels."""
    size=768
    dst=[(0,0),(size,0),(size,size),(0,size)]
    src=[(x*im.width,y*im.height) for x,y in corners]
    a,b=[],[]
    for (u,v),(x,y) in zip(dst,src):
        a.extend([[u,v,1,0,0,0,-u*x,-v*x],[0,0,0,u,v,1,-u*y,-v*y]])
        b.extend([x,y])
    try:
        coeff=np.linalg.solve(np.array(a),np.array(b))
    except np.linalg.LinAlgError as e:
        raise PipelineError("invalid_floor","Floor corners are degenerate.","Mark four different corners around the floor in order.") from e
    im.transform((size,size),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC).save(target)


def guided(project:Path,settings,progress):
    progress("preparing", "Preparing image", .1)
    im=prepare_image(project/"original",project/"prepared.jpg",settings)
    progress("geometry","Projecting the marked floor and building the room shell",.45)
    project_floor(im,settings.floor_corners,project/"floor.png")
    # Wall colour is a photograph sample, not a segmented wall material.
    sample=im.crop((0,0,im.width,max(1,int(im.height*.4)))).resize((1,1)).getpixel((0,0))
    color="#"+"".join(f"{round(c*.3+225*.7):02x}" for c in sample)
    warnings=["Guided layout: floor corners are marked by you. Walls and ceiling are a rectangular approximation, not AI reconstruction.","The floor texture projects the selected photo region, including any furniture or occlusions. Hidden surfaces cannot be recovered.","No furniture, doors, or windows were automatically detected. Add editable assets from the library."]
    if settings.dimensions.source=="estimated":
        warnings.append("Room dimensions are estimated defaults, not measured dimensions.")
    progress("assembly","Assembling editable room",.8)
    return {"version":1,"name":"My room","room":settings.dimensions.model_dump(),"room_type":settings.room_type,"shell":True,"floor_texture":"floor.png","wall_color":color,"objects":[],"camera":{},"settings":settings.model_dump(),"warnings":warnings,"provenance":"guided-photo-projection"}


def classify_failure(message):
    low=message.lower()
    if any(s in low for s in ("out of memory","outofmemoryerror","cuda error: memory")):
        return PipelineError("gpu_out_of_memory",message[-1800:],"Stop other GPU workloads and restart the inference environment to release model memory. Use a 24 GB+ NVIDIA GPU (32 GB tested); guided mode remains available.")
    if any(s in low for s in ("no module named","modulenotfounderror","dll load failed")):
        return PipelineError("missing_dependency",message[-1800:],"Install the dependencies in WorldBuilder's separate Linux environment using upstream docs/SETUP.md; check STAGEAI_WB_PYTHON.")
    if any(s in low for s in ("checkpoint","filenotfounderror","gated repo","401 client","403 client")):
        return PipelineError("missing_weights",message[-1800:],"Check Hugging Face access approval and checkpoint paths in docs/GPU.md.")
    return PipelineError("inference_failed",message[-1800:],"Read the pipeline log in the project folder. Check local Qwen VLM server, checkpoint access, and upstream docs/TROUBLESHOOTING.md.")


def run_worldbuilder(project, settings, progress):
    check=preflight()
    if check["issues"]:
        p=check["issues"][0]
        raise PipelineError(p["code"],p["message"],p["fix"])
    prepare_image(project/"original",project/"prepared.jpg",settings)
    out=project/"worldbuilder"
    cmd=[os.environ["STAGEAI_WB_PYTHON"],str(ROOT/"scripts/wb_worker.py"),str(project/"prepared.jpg"),str(out),settings.quality]
    progress("detect","Detecting objects with local Qwen VLM",.1)
    with (project/"pipeline.log").open("w",encoding="utf-8") as log:
        proc=subprocess.Popen(cmd,cwd=UPSTREAM,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,"PYTHONUNBUFFERED":"1","WORLDBUILDER_DETECTOR":"qwen"})
        import time
        started=time.monotonic()
        while proc.poll() is None:
            if time.monotonic()-started>7200:
                proc.kill(); proc.wait()
                raise PipelineError("timeout","Inference exceeded two hours.","Inspect pipeline.log and verify the local VLM and GPU.")
            stages=[("detected_objects.json","segment","Segmenting objects and room surfaces",.25),("segmentation_results.json","depth","Estimating depth and reconstructing individual meshes",.45),("3d_models/stage3/raw.json","assembly","Fitting room geometry and assembling scene",.8)]
            for artifact,stage,label,fraction in reversed(stages):
                if (out/artifact).exists():
                    progress(stage,label,fraction); break
            time.sleep(.8)
        if proc.returncode:
            raise classify_failure((project/"pipeline.log").read_text(encoding="utf-8",errors="replace"))
    glb=out/"scene_lite.glb"
    if not glb.exists(): glb=out/"scene.glb"
    if not glb.exists():
        raise PipelineError("missing_mesh","Upstream returned without a scene GLB.","Inspect pipeline.log and reconstruction_results.json; no reconstruction was substituted.")
    layout=out/"3d_models/layout.json"
    layout=json.loads(layout.read_text()) if layout.exists() else {}
    scale=layout.get("estimated_metric_scale",1)
    if not isinstance(scale,(float,int)) or not np.isfinite(scale) or not .0001<scale<10000:
        raise PipelineError("invalid_scale","Upstream produced an invalid scene scale.","Inspect layout.json before importing the scene.")
    return glb,scale,layout

