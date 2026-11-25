# Actual validation results — 2026-11-25

Environment: Windows AMD64, Python 3.13.15, installed desktop Chrome, NVIDIA RTX 3070 Ti 8 GB. This record separates working application components from blocked/unverified generative inference. Raw reports and screenshots are in `test-results/`.

## Application tests

Command:

```powershell
.venv\Scripts\python.exe -m pytest tests -q --junitxml=test-results/api-tests.xml
```

**33 passed, 0 failed, 0 skipped**. The last run took 54.58 seconds while the expanded upstream suite ran concurrently; the previous standalone run took 9.62 seconds. One dependency deprecation warning about Starlette's AnyIO portal alias; no application test failure.

Coverage includes JPEG/JPEG-extension/PNG/WebP validation; original preservation; invalid/unsupported/truncated uploads; file size limits; rotation/crop; ordered convex floor corners; homography quadrant orientation; guided-job completion/provenance; measured dimension labels; settings validation; accurate failed-AI status without fallback substitution; mocked preflight/OOM/dependency/weight failure classifications; save/load; portable project round trips; GLB scale and independent object identity; GLB reopening in trimesh; missing asset/duplicate ID rejection; external texture URI rejection; invalid ZIP paths; cross-origin browser mutation rejection; pending-job restart behavior; non-finite metadata rejection; and guided processing of a **real photograph**.

The real-photo test did run and pass; it was not skipped on the recorded run. Fixture: upstream official living-room photograph (Spacejoy/Unsplash), 1400×738 pixels, 208,286 bytes. Guided mode creates a textured rectangular shell and no automatically detected objects. This test is not evidence of AI reconstruction.

## Browser acceptance

Commands, with the launcher/server running:

```powershell
.venv\Scripts\python.exe scripts/browser_smoke.py
.venv\Scripts\python.exe scripts/gizmo_smoke.py
```

**15 browser checks passed, with 0 console errors/unhandled page exceptions**, plus a separately verified **real pointer-drag check**. These ran in the installed Windows Chrome (headless), without downloading another browser.

Verified in the UI:

1. Studio initializes and renders all 14 local procedural asset previews.
2. Furniture can be added, selected, renamed, moved numerically and rotated.
3. Object dimensions edit correctly; extreme movement is constrained to procedural room bounds.
4. Duplicate/delete/undo/redo operate on scene state.
5. A camera-projected click on rendered furniture selects the object.
6. Perspective, top, walk and wireframe controls execute without errors. This is not a full walkthrough collision/comfort audit.
7. Room dimensions, user-measured label, furniture and camera survive save/reload.
8. Browser GLB export reopens in trimesh: **48 geometries**, named sofa retained.
9. A real photograph uploads and produces a guided floor texture and separate 3D shell; no fake furniture detections appear.
10. Reopening the saved photo project retrieves its preserved original for another processing attempt.
11. Selecting WorldBuilder AI on the actual 8 GB GPU yields **insufficient_vram**, displays a recommended fix, and preserves the current scene.
12. Genuine upstream `scene_lite.glb` imports as **43 separate named mesh objects** and renders in the viewport. Import used upstream's `estimated_metric_scale` = **2.879699468612671**.
13. An imported textured mesh can be selected, renamed, rotated, saved and reloaded.
14. The edited real reconstructed scene reexports and opens in trimesh with embedded textured meshes.
15. No browser console errors or unhandled JavaScript exceptions.

The separate gizmo test clicked and dragged an actual X transform handle: the chair moved from `[0,0,0]` to `[0.5237455069779744,0,0]`. This checks pointer manipulation independently of numeric fields.

Screenshots: `studio-empty.png`, `studio-furnished.png`, `photo-guided.png`, `real-photo-room.png`, `official-worldbuilder-scene.png`, and `gizmo-drag.png`. Export artifacts: `browser-export.glb`, `imported-roundtrip.glb`. Browser report: `browser-results.json`.

## Original upstream tests

The untouched upstream suite was attempted. Full collection was blocked by missing CPU PyTorch in `test_segmentation_helpers.py`. A run excluding that file initially reached **9 texture-test failures because OpenCV (`cv2`) was unavailable**. These were dependency failures; upstream source was not changed to suppress them. After resolving Windows cache/file-lock and slow-download problems, OpenCV, fast-simplification and xatlas were installed from SHA-256-verified official PyPI wheels, and the expanded suite passed. These extras are optional for the application.

The final expanded CPU suite was run with only the Torch-dependent segmentation-helper file excluded:

```powershell
Push-Location upstream\WorldBuilder
..\..\.venv\Scripts\python.exe -m pytest tests -q -ra `
  --ignore=tests/test_segmentation_helpers.py `
  --junitxml=../../test-results/upstream-cpu-tests.xml
Pop-Location
```

**91 passed, 3 skipped, 0 failed, 0 errors** (56.86 seconds while app tests ran concurrently). The three skips are missing PyTorch3D, Flask and MuJoCo. Texture, room-shell, relief, built-in box and lite-export tests now pass with the optional dependencies installed. This remains a scoped CPU result, not a full upstream-suite or AI-inference pass. Final report: `upstream-cpu-tests.xml`. The earlier `upstream-independent-tests.xml` (79 passed, 4 skipped) and `upstream-tests.xml` (missing-dependency failures) are historical intermediate reports superseded by this expanded run. Optional prerequisites are in `requirements-upstream-tests.txt`; install CPU PyTorch separately if you want to run the segmentation helper tests. No model weights are needed for these CPU helper tests.

The upstream Git status was checked after testing and had **no tracked changes**. Its MIT license and GPL Blender-extension license are intact.

## Launch and static checks

- `launch.ps1 -NoBrowser` was executed successfully and served the same application at http://127.0.0.1:5174; Chrome acceptance ran against that launcher process.
- `/api/health` returned `{ "ok": true, "version": "1.0.0" }`.
- Python compile checks passed for `stageai` and `scripts`.
- Viewer dependencies, fonts (system), icons and furniture previews are local; no runtime CDN dependency is needed.
- Installed direct app package versions were checked against `requirements.txt`.
- `setup.ps1 -Dev` completed successfully; tested package versions are recorded in `constraints.txt`.

## Explicitly unverified or incomplete

- Full local GPU detection → SAM 3 segmentation → SAM 3D/MoGe → room fitting pipeline **was not run**. Linux, a compatible larger GPU, gated checkpoints and the model environments are unavailable here. The actual upstream entry point is wired and the real-hardware preflight failure was tested. Successful inference and its progress transitions remain unverified.
- OOM and missing-weight failures were checked through classifiers/preflight tests; no actual GPU allocation failure was induced and no gated weights were downloaded.
- The official reconstructed GLB was downloaded (23,067,072 bytes) for testing; its generation happened upstream. It is never used as an output for newly uploaded photos.
- Exports were reopened in trimesh and rendered through Three.js on import. The Blender application itself was not launched, so Blender import is documented but not independently verified in Blender.
- Full upstream test suite, independent wall handles, non-rectangular shell layouts, automatic opening cutouts, physics/overlap prevention, wall alignment snapping, automatic failed-mesh substitution, full GLB parenting/animation fidelity, OBJ and FBX remain incomplete. See README for practical limits.

