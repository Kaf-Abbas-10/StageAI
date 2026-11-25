# StageAI: self-contained project recreation prompt

Copy this entire file into a new coding-agent or LLM session with filesystem and terminal access. It contains the requirements needed to recreate StageAI without access to the original conversation or generated application source.

---

## Your task

Act as a senior computer vision, 3D graphics, and full-stack engineer. **Implement, launch, debug, test, and document a working local application named StageAI.** Do not stop after proposing an architecture or providing installation instructions.

The application is a desktop-oriented browser workspace for this workflow:

**Room photograph → editable room layout → inspect and arrange furniture → save project → export GLB.**

Use [WorldBuilder](https://github.com/AdamRolander/WorldBuilder) as the foundation for genuine AI reconstruction. Preserve its original implementation and licenses in a separate upstream checkout. Build a lightweight editor and integration layer around it.

This brief recreates an application with three distinct workflows:

1. **Guided photo layout:** practical on the target Windows PC; the user marks the floor and supplies or estimates room dimensions.
2. **Import reconstructed GLB:** load an actual WorldBuilder output and edit its independent textured meshes locally.
3. **Full WorldBuilder AI:** invoke the real upstream pipeline only on a compatible, configured machine; report unsupported hardware and missing prerequisites accurately.

Do not describe guided projection or imported examples as a newly completed AI reconstruction.

## Target environment and constraints

The original target was a Windows x64 desktop with an NVIDIA GeForce RTX 3070 Ti and **8 GB VRAM**. Recheck the actual machine instead of assuming its configuration is unchanged.

The inspected upstream version was WorldBuilder 0.4.1, commit:

```text
2852e3b6a833465455d625608c9341cc5747374c
```

Use that commit for reproducibility when available. If you use another version, inspect its interfaces and document the differences.

At that revision, upstream documented Linux x86-64 and at least 24 GB VRAM for full inference, with 32 GB tested. Its SAM 3D stage used approximately 19–20 GB allocated GPU memory. WSL2 was unverified upstream and would not remove an 8 GB VRAM limit. Verify these claims against the checked-out documentation before planning installation.

Requirements:

- Run the editor, guided mode, furniture library, persistence, and import/export natively on Windows.
- No paid cloud inference API, Gemini dependency, or API key is required for these workflows.
- Use local Qwen detection for the full AI workflow; do not silently switch to cloud detection.
- Do not download large model stacks or gated weights onto incompatible hardware merely to attempt a run that cannot fit.
- Keep the editor environment separate from the inference environment.
- The editor must work offline after installation and initial asset downloads.
- Use workspace-local dependencies and relative project paths. Do not hard-code another project's Python installation or a specific Windows username.
- Never assume a driver-advertised CUDA version means the CUDA toolkit or a compatible PyTorch build is installed.

## Inspect upstream before implementation

Read the repository structure, README, setup/hardware/architecture documentation, dependency files, licenses, CLI entry point, web app, viewer, exporters, examples, and tests.

Confirm the actual reconstruction chain. At the pinned revision it was:

1. Qwen3-VL local detector lists objects.
2. SAM 3 produces object-instance and structural masks.
3. SAM 3D Objects reconstructs individual meshes and poses, sharing a MoGe scene point map.
4. WorldBuilder's own CPU stages fit room structure, optimize object placement/support, generate textures and relief, and export scenes.

**SAM 3D Objects alone is not a complete-room reconstruction system.** Reuse upstream's room fitting, placement, export, and model memory-management code through its public entry point.

Measure OS, usable Python, NVIDIA GPU, total/free VRAM, driver, toolkit availability, disk capacity, and WSL availability where accessible. Document unknowns honestly. Identify checkpoints, gated access, model licenses, first-use downloads, and external services.

Give a concise implementation plan, then proceed without routine approval questions. If GPU inference is blocked, continue all independent application work and document the unverified AI stages.

## Required architecture

Use the simplest architecture matching this application:

- **Backend:** Python, FastAPI, Uvicorn, Pillow, NumPy, trimesh, SciPy, and validated Pydantic schemas.
- **Frontend:** buildless HTML/CSS and native JavaScript ES modules with Three.js. No Node/npm, React, TypeScript, Babel, or frontend build step is required for this recreation.
- **3D controls:** Three.js OrbitControls and TransformControls.
- **3D I/O:** GLTFLoader and GLTFExporter, with server-side GLB validation using trimesh.
- **Storage:** local project directories, atomic JSON saves, and portable ZIP-based `.stageai` bundles.
- **Jobs:** a background worker with one reconstruction running at a time and bounded queueing. Do not block the HTTP event loop during long inference or expensive mesh processing.
- **Inference adapter:** a subprocess using a separately configured upstream Python executable, passed as an argument array rather than a shell command.

The following were the original editor's direct dependency pins. Treat them as a reproducibility baseline, verify installation, and document justified changes:

```text
fastapi==0.115.12
uvicorn==0.34.2
python-multipart==0.0.20
pillow==11.2.1
numpy==2.2.5
trimesh==4.6.8
scipy==1.15.2
requests==2.32.5
python-dotenv==1.2.4
```

Developer dependencies:

```text
pytest==8.3.5
httpx==0.28.1
playwright==1.51.0
```

The editor originally used Python 3.13. Upstream's documented inference environment used Python 3.11 and different NumPy/CUDA pins. Keep those environments isolated. Record actually tested transitive versions in a constraints file.

Vendor Three.js **0.160.0 / r160** locally, including its MIT license and these modules plus any imports they require:

```text
three.module.js
OrbitControls.js
TransformControls.js
GLTFLoader.js
GLTFExporter.js
BufferGeometryUtils.js
TextureUtils.js
```

Use a local import map. Adjust relative module imports if using a flat vendor directory. No runtime CDN or remote font dependency is allowed.

## Workflow A: guided photo layout

### Upload and preprocessing

Provide a modal with file selection and drag-and-drop upload, preview, clockwise 90-degree rotation, normalized cropping, room type, dimensions, dimension provenance, processing mode, and progress/error display.

- Accept JPG, JPEG, PNG, and WebP.
- Maximum upload: 25 MB; minimum side: 64 pixels; maximum decoded area: 30 megapixels.
- Validate extension, actual image format, image integrity, and decoded content. Reject truncated images and decompression bombs with actionable errors.
- Preserve the original upload byte-for-byte, even after processing fails.
- Apply EXIF orientation, clockwise rotation, then crop in the same order in the preview and backend.
- Crop is `[left, top, right, bottom]`, normalized to 0–1, with at least 10% extent per axis. Reject a final crop smaller than 32 pixels per side.
- Limit the prepared image to 2560 pixels on its longest side.
- Let a saved project reopen its original photograph for processing with different settings, without requiring another upload.

### Guided geometry

Display four draggable, numbered floor-corner handles on the processed preview, ordered:

**back-left, back-right, front-right, front-left.**

Validate normalized finite coordinates, convexity, non-intersection, and a minimum useful area. Compute an inverse homography mapping a rectangular output texture to the selected photograph quadrilateral. Use Pillow's perspective transform and a 768×768 output floor texture.

Build real, separate 3D floor, wall, and optional ceiling meshes around that texture. Use a rectangular shell with defaults of width 5 m, depth 4 m, and height 2.7 m. A sampled upper-image colour may provide an approximate wall finish.

Allow room width/depth 1–50 m and height 1.8–10 m. Room types are living room, bedroom, office, and other.

Display explicit notes:

- This is a user-guided rectangular approximation, without AI detection, segmentation, or depth estimation.
- The floor texture includes photographed furniture/occlusions in the selected region.
- Hidden surfaces and exact dimensions cannot be recovered from this operation.
- Dimensions are estimated unless the user explicitly supplies measured values.

**Do not automatically add fake detected furniture.** Users add editable assets themselves in guided mode.

## Workflow B: genuine reconstructed-scene import

Accept self-contained GLB 2.0 files, preferably WorldBuilder's `scene_lite.glb`. Provide a **metres per source unit** setting. For WorldBuilder, explain that this comes from `3d_models/layout.json` → `estimated_metric_scale`; already-metric GLBs use 1.

- Preserve independent named mesh objects and embedded materials/textures.
- Bake each mesh node's original world transform, then normalize geometry around a bottom-centre pivot.
- Recenter the assembled scene horizontally and place its lowest point at Y=0 while preserving relative object placement.
- Store original mesh identity and asset/node references so edits survive saving and reopening.
- Classify identifiable room-floor/wall/ceiling nodes as structure.
- Imported geometry can be moved, rotated, resized, duplicated, and deleted independently.
- Room-dimension corrections on imported scenes scale the whole scene along the affected axis, including object positions and dimensions.

Validate GLB headers, version, declared lengths, embedded resources, faces, finite vertices/transforms, reasonable scale, and nonempty meshes. Reject external buffer/texture URIs. Limits: 150 MB, 1,500 independent mesh nodes, and five million triangles. Import scale range: 0.0001–10,000 metres per unit.

Full skeletal animation, original parenting semantics, Draco, and KTX2 decoding are outside the baseline scope. Explain that flattening multi-primitive scenes can produce multiple editable mesh objects.

## Workflow C: real WorldBuilder inference

Use an environment variable such as `STAGEAI_WB_PYTHON` to select the separate inference interpreter. Run the actual upstream entry point:

```python
from main import process_image
process_image(image_path, output_dir, detector="qwen", quality=quality)
```

Adapt the call only if inspection confirms a different interface. Use medium/high quality settings actually supported upstream.

- Check compatible platform, total GPU memory, configured interpreter existence, and checkpoint paths before starting.
- Show all relevant unmet prerequisites, not merely a generic failure.
- At the pinned revision, checkpoint paths included `checkpoints/sam3.pt` and `sam3d_objects_repo/checkpoints/hf/pipeline.yaml` inside upstream.
- Reuse upstream's sequential GPU loading/offloading rather than maintaining another model stack in the editor.
- Preserve upstream output artifacts and a project-local `pipeline.log`.
- Derive progress from real detection, segmentation, stage-3, and scene artifacts. Do not animate simulated AI progress.
- Set a bounded inference timeout, such as two hours, and terminate the owned worker process on timeout.
- Require a real generated scene GLB before marking the job complete.
- Import that GLB into the editor using upstream's metric-scale metadata.
- If user-measured dimensions are supplied, calibrate the scene bounds and explain that local object/hidden-surface geometry remains estimated.
- Report failed individual object reconstructions in scene notes; users can manually add replacements from the library.
- Preserve the current saved scene when an inference attempt fails.

Provide actionable codes/messages/fixes for insufficient VRAM, unsupported platform, missing environment/dependencies/weights, GPU out-of-memory, local VLM failure, timeout, missing meshes, invalid scale, and other inference errors.

Do not claim native Windows full inference, practical CPU generative inference, or successful inference on 8 GB without evidence. Do not substitute a static demo or guided shell for failed AI.

## Interactive room editor

Use a right-handed **Y-up coordinate system in metres**.

- Orbit, pan, zoom, reset camera, perspective view, top-down view, and wireframe inspection.
- Practical walkthrough navigation: WASD, right-drag to look, Escape to exit.
- Click mesh selection and scene-tree selection.
- Bottom-centre object pivots.
- Move furniture on the floor with a real transform gizmo; rotate around Y; scale and edit exact dimensions.
- Numeric X/Y/Z, width/height/depth, vertical-axis rotation, name, and procedural finish colour.
- Duplicate, delete, undo, redo; retain up to 60 scene snapshots during the session.
- Clamp object bottoms above the floor. In procedural rooms, constrain furniture using its rotated footprint; offer 10 cm movement snapping.
- Do not silently distort oversized furniture to fit a room; make resizing available.
- Floor, wall, and ceiling visibility switches. Procedural walls automatically cut away based on camera position; imported room surfaces can be hidden using their classification.
- Update room dimensions and distinguish `estimated` from `user-measured`.
- Keep camera, scene selection, gizmos, materials, history, and displayed properties synchronized across edits and reloads.
- Preserve shared imported textures correctly and manage disposal/cache invalidation when rebuilding or reopening projects.

Suggested shortcuts: G move, R rotate, S scale, Delete remove, Ctrl+D duplicate, Ctrl+Z undo, Ctrl+Y/Ctrl+Shift+Z redo, Ctrl+S save, Home reset camera.

## Procedural furniture library

Create 14 well-proportioned, genuinely 3D procedural assets:

1. Sofa
2. Lounge chair
3. Coffee table
4. Double bed
5. Writing desk
6. Wardrobe
7. Sideboard/cabinet
8. Bookshelf
9. Floor lamp
10. Area rug
11. Potted plant
12. Ceramic vase
13. Door marker
14. Window marker

Use boxes, cylinders, and simple leaf/rounded geometries with distinct parts and sensible materials. Generate real 3D thumbnail previews locally. Include library search, categories, add buttons, and object identity. Furniture edits must never require model inference.

Door/window markers are manually placed geometry and **do not cut holes in walls**. Label that limitation. Imported materials retain their textures; a colour override is only required for procedural assets.

## Visual design

Recreate a clean desktop room studio, not a marketing landing page:

- Dark graphite side panels and toolbar, forest-green viewport background, mint accents, warm wood and muted upholstery on assets.
- Reference colours: panels `#192124`, toolbar `#161d20`, viewport `#293b31`, accent `#b1e7ca`.
- System typography such as Segoe UI, approximately 16 px body text, readable labels, restrained rounded corners and borders.
- Top toolbar around 76 px: StageAI branding, editable project name/save status, Projects, Save, Export GLB.
- Left panel around 270–290 px: photo action, Furniture library/Scene tabs, searchable thumbnail grid, hierarchy, import action and local hardware status.
- Central full-height Three.js viewport: view modes at the top, provenance/dimensions label, transform/undo tools and navigation help at the bottom.
- Right panel around 280–300 px: room dimensions/provenance, visibility/placement controls, selected-object properties, scene notes.
- Bottom status bar around 31 px: job/editor status, object count, units/local-storage context.
- Upload modal: large annotated photo preview on the left and processing settings/progress on the right.
- Additional dialogs for projects, GLB import, hardware capabilities and help.
- Provide an empty-state prompt, accessible button labels, clear errors, and restrained notifications.

Panels must scroll without controls overlapping. Preserve a usable narrower layout, while prioritizing desktop operation. Avoid remote stock imagery or image generation for elements better built as native 3D geometry.

## Persistence and portable project format

Save local projects under `data/<32-hex-project-id>/` with atomic replacement of `scene.json`. Preserve:

- Original and prepared photograph, when present.
- Room geometry parameters and dimension provenance.
- Separate furniture/decorative/structural objects, transforms, identities and materials.
- Imported GLB mesh assets and textures.
- Camera/view/visibility/placement configuration.
- Reconstruction settings, scale metadata, warnings, provenance and schema version.
- Durable job status and actionable failures. Pending jobs become interrupted/failed after restart; never mark them complete without results.

Use a version-1 scene structure resembling:

```json
{
  "version": 1,
  "name": "My room",
  "room": {"width": 5, "depth": 4, "height": 2.7, "source": "estimated"},
  "room_type": "living",
  "shell": true,
  "floor_texture": "floor.png",
  "wall_color": "#e1e5e2",
  "objects": [{
    "id": "chair1", "name": "Reading chair", "kind": "chair",
    "group": "furniture", "position": [1, 0, 0],
    "rotation": 45, "dimensions": [0.75, 0.92, 0.78],
    "color": "#c2aa89", "asset": null, "mesh_name": null,
    "visible": true, "evidence": "Procedural asset; manually placed"
  }],
  "camera": {}, "settings": {}, "warnings": [],
  "provenance": "guided-photo-projection"
}
```

Object `position` is `[x,y,z]` at bottom-centre; `dimensions` is `[width,height,depth]`; `rotation` is degrees about Y. A procedural shell uses `shell=true`; imported structure uses `shell=false`. Provenance values distinguish `manual`, `guided-photo-projection`, `imported-glb`, and `worldbuilder`.

Offer a Projects list, new room, explicit save, and portable download/open. A `.stageai` file is a ZIP containing scene JSON and every referenced photo/texture/mesh asset, plus relevant input metadata. It excludes heavyweight inference caches, logs and session undo history.

Validate finite numeric state, unique IDs, bounded metadata, valid asset references, archive sizes and file paths. Reject ZIP traversal, duplicate entries, external asset references and missing assets. Suggested bundle limits: 250 MB compressed and 500 MB expanded.

## Export

Export self-contained GLB with independent named objects, reasonable metric scale, and embedded materials/textures. Exclude editor grids, selection outlines, transform gizmos, and other editor helpers. Inspection visibility switches must not accidentally omit the shell from the exported room.

Validate the browser-generated GLB on the backend before returning the download. Reopen it in an independent reader and verify geometry, names, scale, and textures.

Document Blender's File → Import → glTF 2.0 workflow. Only claim Blender-application validation if Blender was actually launched and tested. OBJ/FBX export is outside the required baseline.

## API and source layout

Provide these routes or equivalent documented contracts:

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness/version |
| GET | `/api/capabilities` | Hardware and AI prerequisites |
| POST | `/api/projects/upload` | Multipart image upload |
| POST | `/api/projects/{id}/reconstruct` | Queue guided/AI job |
| GET | `/api/projects/{id}/job` | Progress/errors |
| GET/POST | `/api/projects` | List/create projects |
| GET/PUT | `/api/projects/{id}` | Load/save scene, indicate original-photo availability |
| GET | `/api/projects/{id}/assets/{filename}` | Validated project-local asset |
| POST | `/api/import/glb?scale=1` | Import reconstructed geometry |
| POST | `/api/projects/{id}/export` | Validate/return generated GLB |
| GET | `/api/projects/{id}/bundle` | Portable project download |
| POST | `/api/import/project` | Portable project import |

Bind to `127.0.0.1:5174` by default. This is a trusted local single-user app. Reject cross-origin browser mutations; do not introduce cloud authentication or hosting.

Organize the source approximately as follows:

```text
StageAI/
  README.md
  setup.ps1
  launch.ps1
  launch.cmd
  requirements.txt
  requirements-dev.txt
  requirements-upstream-tests.txt
  constraints.txt
  LICENSE
  THIRD_PARTY_NOTICES.md
  stageai/
    __init__.py
    models.py
    pipeline.py
    storage.py
    server.py
    static/
      index.html
      style.css
      app.js
      furniture.js
      favicon.svg
      vendor/
  upstream/WorldBuilder/
  scripts/
    serve.py
    wb_worker.py
    fetch_assets.py
    fetch_test_scene.py
    browser_smoke.py
    gizmo_smoke.py
  tests/
    test_api.py
    fixtures/
  docs/
    WINDOWS.md
    GPU.md
    INSPECTION.md
    PROJECT_FORMAT.md
    TEST_RESULTS.md
    TROUBLESHOOTING.md
  data/                       # ignored, private user projects
  test-results/               # ignored QA artifacts
```

Ignore virtual environments, caches, tools/downloads, user projects, test artifacts, secrets and Python-generated files. Preserve all upstream licenses, including its Blender extension's separate license. Do not redistribute gated weights.

## Installation and launch

Provide an idempotent PowerShell setup script using Git and uv, a workspace-local Python/virtual environment, tested dependency constraints, the pinned upstream checkout, and local viewer assets.

Provide these commands:

```powershell
.\setup.ps1
.\setup.ps1 -Dev
.\launch.ps1
.\launch.ps1 -NoBrowser -Port 5175
```

Also provide `launch.cmd` for double-click launching. Open the browser only after the server is ready. Keep the server in the launching terminal and stop it with Ctrl+C. Avoid persistent execution-policy changes or unrelated system modifications.

After setup, a user must not need to run separate Python preprocessing scripts for every photograph. All routine processing, editing, saving and export belong in the UI.

## Tests and acceptance criteria

Write meaningful API and browser tests, run them, fix failures, and record actual results. Do not copy historical pass counts into a fresh test report.

Cover:

1. Application setup and local launch.
2. Every accepted image format; invalid, renamed, truncated, oversized and unsafe image rejection.
3. Byte-for-byte original preservation; rotation/crop consistency; reopening originals after project reload.
4. Convex ordered floor-corner validation and homography orientation using independently distinguishable image regions.
5. Guided processing of a **real room photograph**, producing actual room geometry with explicit guided provenance and no invented detections.
6. Background jobs, durable status, interruption/restart handling and bounded queueing.
7. Real-hardware preflight and actionable failure classification for missing dependencies/weights and GPU OOM. Clearly identify mocked versus actually induced errors.
8. Real WorldBuilder invocation on compatible hardware, or explicit documentation that its success path remains unverified.
9. Library asset creation, click selection, actual pointer dragging of a transform handle, numeric transforms, resizing, rotation, deletion, duplication, undo/redo and room clamping.
10. Camera/view/visibility controls and saved camera state.
11. Project save/reload and portable project round trips with meshes, textures and original photographs.
12. Genuine WorldBuilder GLB import with independent identities, scale conversion, rendered meshes and textures.
13. Export/reopen in an independent reader, verifying object names and embedded textures after edits.
14. Invalid meshes, non-finite state, missing assets, external URIs and invalid archives.
15. No unhandled JavaScript exceptions or unexpected browser console errors.
16. Upstream source/license preservation and relevant CPU tests, with explicit skips/exclusions for unavailable dependencies.

Use installed Chrome/Edge with Playwright when available, rather than downloading another browser unnecessarily. Collect screenshots and machine-readable reports. Prefer an isolated QA data directory so acceptance tests do not clutter user projects.

An optional real fixture is available from the upstream demo:

```text
Photo: https://adamrolander.github.io/worldbuilder-demo/assets/living-room-photo.jpg
Scene: https://adamrolander.github.io/worldbuilder-demo/living-room/
GLB:   https://adamrolander.github.io/worldbuilder-demo/living-room/scene_lite.glb
```

Verify availability and attribution before use. The original demo credited Spacejoy on Unsplash. Obtain scale metadata from that scene's layout rather than hard-coding it. A downloaded reconstructed example is only an import fixture and must never become a result for a new user upload.

At the original pinned revision, optional CPU test dependencies included OpenCV headless 4.11.0.86, fast-simplification 0.1.11, and xatlas 0.0.11. Some tests additionally require Torch, PyTorch3D, Flask or MuJoCo. Install only appropriate extras, document exclusions, and never modify upstream tests merely to hide missing dependencies or failures.

## Scope boundaries and truthful delivery

The baseline does not require non-rectangular parametric rooms, independent wall-position handles, automatic window/door cutouts, furniture-to-furniture collision, imported-room walking collision, wall snapping, automatic failed-object asset substitution, texture editing, animation-preserving GLB hierarchy import, or FBX/OBJ export. Document these limits instead of implying they are present. Improvements are welcome once the required workflows are working and tested.

Finish with:

- Working source code and a concise directory overview.
- A verified one-command launch path and dependency/environment configuration.
- Windows setup, hardware/model/checkpoint requirements, and legitimate download/license instructions.
- Guidance for photo processing, editing, saving/reopening projects and Blender-compatible export.
- Actual automated/browser/upstream test results and artifact locations.
- Explicit blocked, incomplete and unverified features, especially full GPU inference.

Start by inspecting the workspace and upstream repository. Implement incrementally, run the application, and continue until the supported local workflows are usable. Ask for input only when a genuine unresolved dependency on the user prevents progress.
