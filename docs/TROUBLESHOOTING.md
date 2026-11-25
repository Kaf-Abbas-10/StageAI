# Troubleshooting

| Symptom | Action |
| --- | --- |
| `python` cannot run or opens Microsoft Store | Use the launch/setup scripts; they use `.venv\Scripts\python.exe`, not the Store alias. |
| Missing app package | Run `setup.ps1` again. For tests use `setup.ps1 -Dev`. |
| Port 5174 already in use | Stop the previous studio or use `launch.ps1 -Port 5175`. |
| Blank viewport / WebGL unavailable | Enable graphics acceleration in Chrome/Edge, restart browser, check graphics driver. Read browser console for initialization errors. |
| Invalid image | Use decoded JPG/PNG/WebP, at least 64 pixels each side, ≤25 MB and ≤30 MP. Renaming an arbitrary file to .jpg is not supported. |
| Twisted floor texture | Mark a convex, ordered floor region. Handles must not cross. Projection includes photographed occlusions. |
| Wrong guided room layout | Guided mode assumes a rectangular room. Edit dimensions, floor corners and furniture manually; it has no AI structure detection. |
| `insufficient_vram` | The supported model chain requires 24 GB+ VRAM; this 8 GB GPU cannot run it. Use guided layout or import a real GLB. |
| `unsupported_platform` | SAM 3D dependencies need Linux; native Windows AI inference is unsupported. See GPU.md. |
| `missing_environment` / `missing_dependency` | Install upstream's separate Linux environments. Configure `STAGEAI_WB_PYTHON`; do not change the editor's NumPy/Python pins to match CUDA models. |
| `missing_weights` | Request/receive gated Hugging Face access, accept licenses, download to the exact upstream paths. See GPU.md. |
| `gpu_out_of_memory` | Stop other GPU workloads and restart the model environment to release model memory. Use supported hardware; no static scene is substituted. |
| `inference_failed` | Read `data/<id>/pipeline.log`; check the local VLM server and upstream TROUBLESHOOTING.md. |
| `server_restarted` | Original photo and last saved scene are preserved. Open the photo and start the job again. |
| Imported room looks tiny | Supply `estimated_metric_scale` from upstream `3d_models/layout.json`. Default import scale 1 does not turn arbitrary units into measured metres. |
| Walls obscure imported objects | Turn Walls off, or select an object using Scene hierarchy. Imported walls have inspection switches but no automatic cutaway. |
| Imported GLB won't load | Use self-contained glTF 2.0 GLB with ordinary embedded textures and meshes; Draco/KTX2 decoding isn't included. Prefer upstream's scene_lite.glb. |
| Furniture exceeds a wall | Resize oversized furniture. Room clamping cannot fit an object larger than the room. It also does not prevent furniture-to-furniture overlap. |
| Edit lost on browser close | Save before closing. Unsaved edits live in browser memory; project persistence is explicit. |

The app shows exact job errors and a recommended fix; it does not claim failed GPU inference succeeded. A user can reconstruct the same preserved original with different preprocessing/settings. This replaces the generated scene for that project; download/save a separate portable project before doing so if you need both versions.

