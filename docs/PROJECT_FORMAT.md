# StageAI project format, version 1

Projects are local directories `data/<32-hex-id>/`. `scene.json` is authoritative; saves use an atomic file replacement. `original` is the unmodified upload (JPEG/PNG/WebP content), served with a detected media type. `prepared.jpg` is EXIF-oriented, then clockwise-rotated, cropped and limited to 2560 pixels on its longest side. `floor.png` is a 768-square projectively rectified texture. `reconstruction.json` records submitted settings; `metadata.json` preserves original filename, dimensions and upload time.

`asset_<uuid>.glb` files hold normalized imported meshes and embedded textures. Each mesh has a stable node name; `scene.json` independently stores its bottom-centre pivot, transform and dimensions. Imported scene coordinates are recentered horizontally, and their lowest point becomes floor Y=0. Relative placement is retained. Each node's world transform is baked into its geometry before normalization; instancing and high-level parenting are flattened to mesh instances. Mesh materials and embedded textures are retained.

```json
{
  "version": 1,
  "name": "Reading room",
  "room": {"width": 5, "depth": 4, "height": 2.7, "source": "estimated"},
  "room_type": "living",
  "shell": true,
  "floor_texture": "floor.png",
  "wall_color": "#e1e5e2",
  "objects": [{
    "id": "chair1", "name": "Reading chair", "kind": "chair",
    "group": "furniture", "position": [1,0,0], "rotation": 45,
    "dimensions": [0.75,0.92,0.78], "color": "#c2aa89",
    "asset": null, "node": null, "mesh_name": null,
    "visible": true, "evidence": "Procedural library asset; manually placed"
  }],
  "camera": {"mode":"perspective", "position":[6,5,7], "target":[0,0.4,0]},
  "settings": {}, "warnings": [], "provenance": "guided-photo-projection"
}
```

Coordinates: right-handed, Y-up, metres; `position` is `[x,y,z]` at bottom-centre, `dimensions` is `[width,height,depth]`, `rotation` is degrees around +Y. `room.source` is `estimated` or `user-measured`. `shell=false` means room structure is imported mesh objects, rather than duplicated with a new procedural shell. Groups are `structure`, `furniture`, `decorative`; the camera is stored separately in `camera`. Provenance distinguishes manual, guided-photo-projection, imported-glb, and worldbuilder.

`camera` additionally stores view mode, zoom, inspection visibility switches and placement settings. `settings` stores reconstruction inputs and, for AI results, upstream layout/scale metadata. `job.json` tracks durable queued/running/complete/failed status, stage, message, progress, timestamps and actionable error code/message/fix. Pending jobs become failed with `server_restarted` after a restart; they are not silently marked complete. Jobs share a single worker, with at most three active/queued requests.

`.stageai` is an ordinary ZIP containing `scene.json` and every referenced GLB/texture, plus original/prepared photos and input metadata when available. It excludes logs, heavyweight intermediate model files and cached undo history. Asset names are validated; absolute paths, parent traversal, external GLB URIs and duplicate ZIP members are rejected. Bundle import creates a new project ID and does not overwrite an existing project. ZIP input is capped at 250 MB / 500 MB expanded. GLB input is capped at 150 MB. Missing/invalid mesh references are errors.

## Local API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Local liveness/version |
| GET | `/api/capabilities` | Hardware and AI prerequisites |
| POST | `/api/projects/upload` | Multipart `image`; preserve photo, return project ID |
| POST | `/api/projects/{id}/reconstruct` | Validated reconstruction settings; queue worker |
| GET | `/api/projects/{id}/job` | Durable status and exact failure/fix |
| GET/POST | `/api/projects` | List/create manual projects |
| GET/PUT | `/api/projects/{id}` | Load/save complete versioned scene state |
| GET | `/api/projects/{id}/assets/{filename}` | Serve whitelisted local assets |
| POST | `/api/import/glb?scale=1` | Multipart `file`; retain independent named meshes |
| POST | `/api/projects/{id}/export` | Multipart browser-generated `file`; validate/return GLB |
| GET | `/api/projects/{id}/bundle` | Download portable project |
| POST | `/api/import/project` | Multipart `file`; import portable project |

The API is intended for a trusted local desktop, binds loopback by default, rejects cross-origin browser mutations, and requires no cloud account. It is not a multi-user hosted service. FastAPI's local `/docs` describes request schemas.

