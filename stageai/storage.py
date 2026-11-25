import io
import json
import math
import os
import re
import uuid
from pathlib import Path

import numpy as np
import trimesh

from stageai.models import SceneState
from stageai.pipeline import PipelineError

ID_RE=re.compile(r"^[a-f0-9]{32}$")
ASSET_RE=re.compile(r"^(original|prepared\.jpg|floor\.png|asset_[a-f0-9]{32}\.glb)$")


def atomic_json(path,data):
    # Unique staging name avoids overlapping API writes sharing a temp file.
    temp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        temp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf-8")
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)


def validate_assets(scene,project):
    refs=[scene.floor_texture]+[o.asset for o in scene.objects]
    ids=[o.id for o in scene.objects]
    if len(ids)!=len(set(ids)):
        raise ValueError("Scene object IDs must be unique")
    for ref in refs:
        if ref and (not ASSET_RE.fullmatch(ref) or not (project/ref).is_file()):
            raise ValueError(f"Missing or invalid local asset: {ref}")
    for o in scene.objects:
        if o.kind=="mesh" and (not o.asset or not o.mesh_name):
            raise ValueError("Imported meshes require an asset and mesh_name")


def validate_glb(data):
    # glTF loaders must not resolve arbitrary HTTP or local file dependencies.
    if len(data)<20 or data[:4]!=b"glTF":
        raise ValueError("Expected a binary glTF 2.0 (.glb) file")
    import struct
    version,length,chunk_len,chunk_type=struct.unpack_from("<IIII",data,4)
    if version!=2 or length!=len(data) or chunk_type!=0x4e4f534a or chunk_len>len(data)-20:
        raise ValueError("Invalid GLB header or JSON chunk")
    doc=json.loads(data[20:20+chunk_len])
    if any("uri" in entry and not entry["uri"].startswith("data:") for key in ("buffers","images") for entry in doc.get(key,[])):
        raise ValueError("GLB must embed its buffers and textures; external URIs are not allowed")
    scene=trimesh.load(io.BytesIO(data),file_type="glb",force="scene",process=False)
    if not scene.geometry:
        raise ValueError("GLB contains no meshes")
    faces=0
    for geom in scene.geometry.values():
        if not isinstance(geom,trimesh.Trimesh) or len(geom.faces)==0 or not np.isfinite(geom.vertices).all():
            raise ValueError("GLB contains missing faces or non-finite mesh vertices")
        faces+=len(geom.faces)
    if faces>5_000_000:
        raise ValueError("GLB exceeds five million triangles; use WorldBuilder's scene_lite.glb")
    for node in scene.graph.nodes_geometry:
        matrix,_=scene.graph[node]
        if not np.isfinite(matrix).all():
            raise ValueError("GLB contains a non-finite node transform")
    return scene


def import_glb(project,data,scale=1.0,provenance="imported-glb"):
    source=validate_glb(data)
    if len(source.graph.nodes_geometry)>1500:
        raise ValueError("GLB exceeds 1500 independent mesh nodes")
    normalized=trimesh.Scene()
    global_bounds=source.bounds*scale
    floor_y=float(global_bounds[0,1])
    center=(global_bounds[0]+global_bounds[1])/2
    asset=f"asset_{uuid.uuid4().hex}.glb"
    objects=[]
    warnings=["Imported mesh dimensions follow the selected metres-per-unit scale; source geometry may include estimated or invented surfaces."]
    for i,node in enumerate(source.graph.nodes_geometry):
        matrix,gname=source.graph[node]
        geom=source.geometry[gname].copy()
        geom.apply_transform(matrix)
        geom.apply_scale(scale)
        lo,hi=geom.bounds
        size=hi-lo
        if not np.isfinite(size).all() or np.max(size)>100 or np.max(np.abs(geom.bounds))>1000:
            raise ValueError("Extreme mesh scale or position. Adjust metres per unit before importing.")
        if np.max(size)<.001:
            warnings.append(f"Skipped tiny or degenerate mesh: {node}"); continue
        base=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])
        geom.apply_translation(-base)
        key=f"import_{i:04d}"
        normalized.add_geometry(geom,node_name=key,geom_name=key)
        name=str(node)
        structural=any(x in name.lower() for x in ("room_floor","room_wall","room_ceiling","room_relief")) or name.lower()=="room"
        objects.append({"id":uuid.uuid4().hex,"name":name[:150],"kind":"mesh","group":"structure" if structural else "furniture","position":[float(base[0]-center[0]),float(base[1]-floor_y),float(base[2]-center[2])],"rotation":0,"dimensions":np.maximum(size,.001).tolist(),"color":"#a8b4ac","asset":asset,"mesh_name":key,"visible":True,"evidence":"upstream generated mesh" if provenance=="worldbuilder" else "imported mesh; scale supplied by user"})
    if not objects: raise ValueError("No usable mesh nodes remain")
    (project/asset).write_bytes(normalized.export(file_type="glb"))
    extent=global_bounds[1]-global_bounds[0]
    scene={"version":1,"name":"Imported room","room":{"width":float(np.clip(extent[0],1,50)),"depth":float(np.clip(extent[2],1,50)),"height":float(np.clip(extent[1],1.8,10)),"source":"estimated"},"room_type":"other","shell":False,"floor_texture":None,"wall_color":"#e1e5e2","objects":objects,"camera":{},"settings":{"import_scale":scale},"warnings":warnings,"provenance":provenance}
    validated=SceneState.model_validate(scene)
    validate_assets(validated,project)
    return validated.model_dump()

