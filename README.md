# StageAI — local room studio

A Windows-ready room editor built around an untouched checkout of [WorldBuilder](https://github.com/AdamRolander/WorldBuilder), pinned to `2852e3b6a833465455d625608c9341cc5747374c` (0.4.1).

**This PC can run the editor, guided photo layout, project persistence, and GLB import/export. It cannot run the supported full WorldBuilder AI pipeline on its 8 GB RTX 3070 Ti.** Upstream requires Linux and 24 GB+ VRAM; its tested configuration has 32 GB. Guided mode is explicitly identified throughout the UI and never reported as AI reconstruction.

## Start

The workspace environment and local viewer assets are already installed. From this directory:

```powershell
.\launch.ps1
```

Or double-click `launch.cmd`. Open **http://127.0.0.1:5174**. Keep the terminal open; Ctrl+C stops the server. For a different port: `.\launch.ps1 -Port 5175`. The launcher does not require Node, npm, an API key, or internet access after setup.

For a fresh checkout, install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\launch.ps1
```

Setup creates a workspace virtual environment with Python 3.13 and installs lightweight app dependencies. It does **not** install GPU stacks, accept model licenses, or download gated checkpoints. See [Windows setup](docs/WINDOWS.md).

## Three supported workflows

### Guided photo layout — available on this PC

1. Click **Start with a photograph** and choose JPG/JPEG/PNG/WebP (25 MB maximum; at least 64 pixels per side; up to 30 megapixels). Upload validation checks actual decoded image content, not only the filename.
2. Rotate or crop as needed. Drag the four numbered handles around a visible floor region in order: back-left, back-right, front-right, front-left. Corners refer to the rotated/cropped image.
3. Select room type and enter width, depth, and height. Check the measured-dimensions option only when you supplied measurements. Defaults are estimates.
4. Choose **Guided layout** and **Create guided room**. The server uses a projective transform to rectify the selected photograph region into a floor texture, then builds an editable rectangular room shell. The upper image supplies an approximate wall colour; it is not a segmented wall texture.
5. Add furniture from the library. Nothing is automatically detected in this mode. The original image is preserved byte-for-byte for repeated processing.

This produces real separate 3D geometry, but **does not recover the room from AI depth or segmentation**. Furniture can remain visible in the projected texture, and a photograph cannot reveal hidden surfaces. Scene notes explain this clearly.

### Import a genuine WorldBuilder scene — available on this PC

1. Obtain `scene_lite.glb` (preferred) or `scene.glb` from an actual WorldBuilder run.
2. Click **Import WorldBuilder / GLB**. Supply **metres per source unit** from `3d_models/layout.json` → `estimated_metric_scale`; use 1 for already-metric GLBs.
3. Each mesh node becomes an independently selectable object. Textures and node names are retained; the scene is recentered horizontally and placed on the floor while preserving relative geometry.
4. Use Scene hierarchy to select small objects. Turn off Walls or Ceiling to inspect a closed imported room. Imported walls do not automatically cut away.

GLB files must embed their buffers and textures. Draco/KTX2 compressed assets are not supported. Import rejects external URIs, missing faces, invalid vertices/transforms, extreme scales, >150 MB files, >1,500 nodes, and >5 million triangles. Files with multiple primitives can appear as multiple named mesh objects; skeletal animation and object parenting semantics are not retained by the mesh normalization step.

### Full WorldBuilder AI — implemented, blocked on this PC

The AI option calls the real upstream `main.process_image` in a separate Linux Python process with `detector="qwen"`. It never switches to Gemini or a paid service. It uses upstream's medium/high quality option and reads progress from actual stage artifacts. Only one reconstruction job runs at a time.

Preflight reports unsupported native Windows, insufficient VRAM, missing inference environment, and missing checkpoints. Failed inference does not replace an existing scene. See [GPU and checkpoint requirements](docs/GPU.md) for the supported Linux workflow. **GPU inference has not been executed or verified here.** WSL2 does not resolve the 8 GB VRAM limit.

## Arrange and edit

- Orbit with left drag, pan with right drag, zoom with the wheel. Home resets the camera.
- Click an object or a row in **Scene** to select. **G** moves on the horizontal plane, **R** rotates around Y, **S** scales. Drag handles or use numeric properties.
- Edit name, X/Y/Z, width/height/depth, rotation, and procedural finish colour. Imported materials retain their original textures and have no colour override.
- **Ctrl+D** duplicates; Delete removes; **Ctrl+Z** undoes; **Ctrl+Y** or Ctrl+Shift+Z redoes. Undo history is session-local (60 snapshots).
- Room width/depth/height edit the procedural shell. On imported scenes they calibrate the entire scene along that axis, including furniture. Mark supplied measurements explicitly.
- Furniture is clamped to the floor and, in procedural rooms, constrained to room bounds using its rotated footprint. Enable 10 cm movement snapping if desired. Oversized objects can still exceed the room and need resizing; there is no furniture-to-furniture collision system.
- **Top view**, **Perspective**, **Walk**, and **Wireframe** are available. Walk uses WASD and right drag to look; Esc returns to orbit. The procedural room constrains the walking camera to its rectangle. Imported-room collision is not implemented.
- Floor/wall/ceiling switches control inspection. Procedural walls cut away automatically in orbit view. Export includes the whole shell, regardless of these inspection switches.
- The 14 procedural library assets cover sofas, chairs, tables, beds, desks, wardrobes, cabinets, shelves, lamps, rugs, plants, vases, door markers, and window markers. Markers do not cut holes in walls. Add them manually where you see openings.

## Save, resume, and export to Blender

**Save** / Ctrl+S writes to `data/<project-id>/` on this PC. Projects lists saved scenes. **Download project** saves a portable `.stageai` ZIP containing the original photograph (when present), prepared photograph, floor texture, imported meshes, settings, scene hierarchy, camera/visibility configuration, dimensions and their provenance, and the versioned scene JSON. Open it using **Projects → Open .stageai file**. [Project format](docs/PROJECT_FORMAT.md).

**Export GLB** saves the project, exports separate named mesh nodes and materials in metres, validates the binary scene on the server, then downloads it. The editor grid, selection box, lights, and transform handles are excluded. Procedural assets retain nested mesh parts under their named object group. In Blender 4.2+, use **File → Import → glTF 2.0**, choose the exported GLB, and select objects in the Outliner. Textures are embedded. FBX/OBJ export is not implemented.

## Source layout

```text
StageAI/
  launch.ps1, launch.cmd      one-command Windows launcher
  setup.ps1                  lightweight local installation
  requirements*.txt          app, developer and optional CPU test dependencies
  constraints.txt            tested dependency versions for reproducible setup
  stageai/
    models.py                validated project/settings schema
    pipeline.py              guided projection, hardware checks, upstream runner
    storage.py               GLB validation and normalized mesh import
    server.py                local FastAPI API and durable project/job storage
    static/
      index.html, style.css  desktop studio interface
      app.js                 editor, upload UI, history, navigation, GLB export
      furniture.js           procedural furniture and previews
      vendor/                pinned Three.js r160 modules and MIT license
  upstream/WorldBuilder/     complete unmodified upstream Git checkout and licenses
  scripts/                   launch, asset downloads, AI subprocess and browser tests
  tests/                     API, geometry import and failure-path tests
  tests/fixtures/            credited real photograph for acceptance testing
  docs/                      inspection, installation, GPU, format and test records
  data/                      generated private projects (ignored)
  test-results/              reports, screenshots and exported validation files (ignored)
```

React/TypeScript was unnecessary for the existing buildless interface: this separate frontend uses browser ES modules and Three.js, served by Python. Upstream's Flask/React app and generated viewer remain usable unchanged in their own environment. No model logic was copied or rewritten.

## Tests and limits

See [actual test results](docs/TEST_RESULTS.md) and [repository inspection](docs/INSPECTION.md). Run app tests:

```powershell
.\setup.ps1 -Dev
.venv\Scripts\python.exe -m pytest tests -q
# With the local studio running and Chrome installed:
.venv\Scripts\python.exe scripts/browser_smoke.py
```

The optional real-photo fixture comes from the upstream demo and is used only for testing. `scripts/fetch_test_scene.py` downloads it and a genuine precomputed GLB; these are never substituted for generated results. Browser acceptance is implemented using the installed Windows Chrome, so it needs no Playwright browser download.

Known incomplete work: full AI run on compatible hardware; automatic furniture generation on 8 GB; automatic door/window cutouts; non-rectangular parametric rooms; individual wall-position handles (change room dimensions or edit imported wall meshes); physics/collision between furniture; snapping to walls; automatic asset substitution for failed upstream objects (failures are reported and library assets can be added manually); texture editing; full import hierarchy/animation fidelity; FBX/OBJ export; and opening an export in the Blender application itself. Do not interpret imported demo validation as a locally executed inference result.

StageAI code is MIT. WorldBuilder's MIT code, GPL Blender extension, and notices remain intact. Its model weights have separate licenses and are not redistributed. Three.js is MIT. Photo credits and model links: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

