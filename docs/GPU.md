# GPU compatibility and legitimate model setup

**Current machine: RTX 3070 Ti, 8 GB. Supported full WorldBuilder inference will not fit.** Editor/guided mode/import/export work independently. Neither reducing photograph resolution nor installing WSL increases available VRAM. CPU execution of SAM 3/SAM 3D is not offered as a practical fallback.

Upstream's [hardware guide](../upstream/WorldBuilder/docs/HARDWARE.md) reports roughly 19–20 GB allocated for SAM 3D and ~21 GB for the local Qwen detector, loaded sequentially. It specifies Linux x86-64, 24 GB minimum (untested there), 32 GB tested, 48–64 GB host RAM and ~60 GB disk. Native Windows is unsupported by CUDA dependencies; WSL2 is plausible but untested upstream. StageAI does not promise it works.

## On a compatible local Linux machine

Move/clone this project to that machine, keeping `upstream/WorldBuilder` inside it. Use the complete [upstream setup instructions](../upstream/WorldBuilder/docs/SETUP.md) and [troubleshooting](../upstream/WorldBuilder/docs/TROUBLESHOOTING.md); they contain the source-build and version details that a thin app requirements file cannot express.

The upstream-known dependency commits are SAM 3 `7b89b8f`, SAM 3D Objects `e19b169`, PyTorch3D `f5f6b78`. Its tested RTX 5090 setup uses Python 3.11, torch 2.8.0/CUDA 12.8, torchvision 0.23.0, numpy 1.26.4, transformers 4.39.3, kaolin 0.18.0, open3d 0.19.0, and editable upstream repos. The model environments include compiled CUDA dependencies. Do not install these into this app's Windows environment or assume driver-advertised CUDA equals toolkit installation.

Request gated access and accept the licenses at:

- [facebook/sam3](https://huggingface.co/facebook/sam3) — SAM 3 checkpoint, SAM license.
- [facebook/sam-3d-objects](https://huggingface.co/facebook/sam-3d-objects) — SAM 3D Objects pipeline/checkpoints, SAM license.

After approval, authenticate locally using `hf auth login` (never put your token into source code), then in WorldBuilder's Linux environment:

```bash
cd upstream/WorldBuilder
mkdir -p checkpoints
hf download facebook/sam3 sam3.pt --local-dir checkpoints
hf download --repo-type model --local-dir sam3d_objects_repo/checkpoints/hf-download \
  --max-workers 1 facebook/sam-3d-objects
# Move hf-download/checkpoints to sam3d_objects_repo/checkpoints/hf
# so the following file exists:
# sam3d_objects_repo/checkpoints/hf/pipeline.yaml
```

Also clone/install the upstream dependency repositories exactly as documented, apply its Hydra patch, and verify its imports (`torch`, `sam3`, `sam3d_objects`, `pytorch3d`, `kaolin`). MoGe is automatically fetched on first use. See source model cards for current license terms rather than assuming all checkpoints share the repository's MIT license.

For **fully local detection**, create WorldBuilder's separate `worldbuilder-vlm` conda environment (newer transformers conflicts with the SAM 3D environment), install `vlm_server/requirements.txt`, and start:

```bash
cd upstream/WorldBuilder
conda activate worldbuilder-vlm
python vlm_server/server.py
```

The server defaults to `http://127.0.0.1:8765` and downloads Qwen3-VL-8B weights on first start. Its unload/reload API lets upstream move models between GPU and CPU to avoid simultaneous large GPU allocations. StageAI preserves that behavior.

In a second terminal, run the editor server on the **same Linux filesystem/machine**, using a lightweight app virtual environment and pointing to the real inference interpreter:

```bash
export STAGEAI_WB_PYTHON=/absolute/path/to/conda/envs/worldbuilder-main/bin/python
export WORLDBUILDER_VLM_URL=http://127.0.0.1:8765
export WORLDBUILDER_DETECTOR=qwen
python -m uvicorn stageai.server:app --host 127.0.0.1 --port 5174
```

StageAI launches `scripts/wb_worker.py` with argument arrays (no shell), sets `detector='qwen'`, and calls the actual upstream `process_image` with medium/high quality. It polls detection, segmentation, and stage-3 artifacts rather than simulating progress. An inference timeout, OOM, dependency failure, missing weights, or absent scene GLB becomes a failed job with a fix and preserved input. Output is saved under `data/<id>/worldbuilder/`, with `pipeline.log` next to it. The process has a two-hour timeout.

The lightweight server's preflight detects total GPU VRAM, native platform, configured interpreter and checkpoint files. Passing preflight is **not** proof of successful inference, compatible compiled dependencies, complete weights, enough free VRAM, or a healthy VLM. Runtime errors remain possible and are reported. Free VRAM is shown in the UI. CUDA models/weights were not loaded or tested in this environment.

Upstream metric scale is read from `layout.json` and applied to the imported geometry. If user-measured dimensions were supplied, scene axes are additionally calibrated to those bounds; the resulting furniture and hidden surfaces still remain estimates.

If models run on a different computer, transfer its finished GLB + `estimated_metric_scale` and import locally. A remote inference service/client and managed WSL launcher are not implemented. This app requires no paid inference service or Gemini key.

