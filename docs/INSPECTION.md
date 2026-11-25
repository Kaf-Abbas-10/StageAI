# Repository inspection and implementation record

Inspected before implementation on 2026-11-25: README, SETUP, HARDWARE, ARCHITECTURE, requirements.txt, pyproject.toml, LICENSE, main.py, webapp/server.py, webapp/static, viewer_generator.py, scene_export.py, room_layout.py, tests, and official demo manifests. Source: https://github.com/AdamRolander/WorldBuilder. Commit `2852e3b6a833465455d625608c9341cc5747374c`, package 0.4.1. Original files were left untouched.

## What upstream actually does

1. Local Qwen3-VL (or optional cloud Gemini) lists object labels and expected counts. A postprocessor removes duplicates and unwanted labels.
2. SAM 3 performs instance segmentation plus structural floor/wall/ceiling/window masks. This is not SAM 3D.
3. SAM 3D Objects produces individual textured objects and poses. Its MoGe point map is computed once for the full photo and reused. Stage-3 meshes, poses, intrinsics, and point maps are cached.
4. WorldBuilder's CPU code estimates gravity/floor and Manhattan-aligned walls from that point map, optimizes placement against silhouettes/support, creates textured room shell/relief, completes unseen materials, and exports.

SAM 3D Objects alone does not reconstruct a complete room. Upstream's own geometry and scene assembly stages supply the shell. Single-photo scale is predicted from optional MoGe-2 or a camera-height prior; neither is a user measurement. Hidden geometry/materials are invented or extrapolated.

## Reused vs implemented

| Capability | Upstream | StageAI |
| --- | --- | --- |
| Full AI chain and model memory management | Already implemented | Thin isolated Python subprocess, `process_image(..., detector='qwen')` |
| GPU model loading, sequential offloading | Already implemented | Unchanged; preflight blocks unsupported installations |
| CPU room fitting, support, textures | Already implemented | Used through the AI chain, not reimplemented |
| Upload API and job progress | Flask web app exists | Separate local FastAPI wrapper with actual-image validation, original preservation, durable status |
| Viewer, quick edits and GLB export | Generated Three.js viewer exists | Dedicated editor required to add a furniture library and portable project model |
| Existing reusable asset library | No general furniture library found | 14 self-authored procedural models; no asset-license downloads |
| Guided low-resource operation | Not supplied | User-marked floor projection + explicitly approximate room shell |
| Scene persistence | Upstream edits.json for generated scenes | Versioned scene JSON and portable bundled projects |
| Upstream functionality/license preservation | Required | Entire clone retained, no tracked upstream source edits |

## Plan and outcome

- Phase 1: inspect and obtain upstream; measure hardware; determine whether original pipeline can run. **Blocked for model inference** by native Windows, 8 GB VRAM, missing Linux model environment/checkpoints and gated access. Full-stack GPU downloads were deliberately avoided. CPU helper tests were run separately.
- Phase 2: implement a usable real-photo workflow independent of blocked inference. **Guided prototype implemented and tested** with the actual Spacejoy living-room photograph. The separate AI entry point and failure reporting are implemented, but its GPU success path remains unverified.
- Phases 3–5: implement room viewport, independent objects, procedural furniture, transforms/history, project storage, GLB validation/export and import. **Implemented and tested** in Chrome/API tests.
- Phase 6: ship Windows launcher, setup, requirements, hardware/format documentation, and validation records. Known missing features are listed in README.

## Environment findings

- Windows, NVIDIA GeForce RTX 3070 Ti, **8,192 MiB total**, approximately 6,470 MiB free at the first check (free memory changes during desktop use).
- Driver `621.01`; nvidia-smi advertised CUDA compatibility `13.5`. This is **driver compatibility, not an installed CUDA toolkit or PyTorch build**. No usable nvcc/toolkit or CUDA inference environment was established.
- `python` resolves to a Windows Store alias that cannot execute. `python3.13` was usable (3.13.15), and the application has its own `.venv`. No Node/npm was on PATH, so the app avoids a JS build tool dependency.
- WSL inspection returned `Wsl/E_ACCESSDENIED` in the tool environment. WSL availability was not established, and WSL/driver/system configuration was not modified.
- Free space on the workspace drive was measured at approximately 1.03 TiB; disk capacity is not the blocker. Hardware details are saved in `test-results/hardware.json`.
- Upstream requires Linux x86-64, Python 3.11 for its documented model setup, approximately 60 GB storage and 48–64 GB practical host RAM; its documented SAM 3D allocated peak is about 19–20 GB. The 8 GB card is below the supported minimum even if WSL becomes available.

## Download/API inventory

The app itself uses no paid API and no cloud inference. Network is needed only for initial installation and optional QA downloads. Three.js r160 is bundled locally; no font/CDN requests are needed during normal editing.

Full AI requires separately cloned SAM 3, SAM 3D Objects, and PyTorch3D; approved Meta gated checkpoints (~3.4 GB + ~12 GB); automatic MoGe weights; optional MoGe-2 (~1.3 GB); and local Qwen3-VL-8B (~17 GB). MoGe and Qwen may trigger legitimate first-use network downloads on a configured inference machine. Accept their licenses yourself. No model weights were downloaded here. See upstream [SETUP](../upstream/WorldBuilder/docs/SETUP.md) and [HARDWARE](../upstream/WorldBuilder/docs/HARDWARE.md).

