# Third-party notices

- **WorldBuilder** by Adam Rolander: https://github.com/AdamRolander/WorldBuilder — unmodified full clone at `upstream/WorldBuilder`, commit `2852e3b6a833465455d625608c9341cc5747374c`. Main code: MIT, retained at `upstream/WorldBuilder/LICENSE`. Blender extension: GPL-3.0-or-later, retained at `upstream/WorldBuilder/integrations/blender_worldbuilder/LICENSE`. StageAI does not copy the Blender extension into its own code.
- **Three.js r160**: https://github.com/mrdoob/three/tree/r160 — MIT, Copyright © 2010–2023 three.js authors. License is bundled in `stageai/static/vendor/THREE-LICENSE.txt`; the loader/exporter relative imports were adjusted for the flat local vendor directory.
- **Living-room test photograph**: Spacejoy on Unsplash, credited by upstream in its README, downloaded from https://adamrolander.github.io/worldbuilder-demo/assets/living-room-photo.jpg . Used as a test fixture, not a generated reconstruction. Unsplash license: https://unsplash.com/license . No ownership of this photograph is claimed.
- **Optional official reconstructed test scene**: https://adamrolander.github.io/worldbuilder-demo/living-room/scene_lite.glb — generated upstream output corresponding to the above photo. Downloaded into ignored `test-results/` only for import validation; not shipped as a result for user photographs.
- **SAM 3 and SAM 3D Objects**: Meta SAM license and gated model access; not bundled or downloaded. Obtain from https://huggingface.co/facebook/sam3 and https://huggingface.co/facebook/sam-3d-objects and review the model cards/licenses.
- **MoGe**: https://github.com/microsoft/MoGe — code MIT; review specific weight/model-card terms. Not bundled. Optional MoGe-2 has its own weight terms.
- **Qwen3-VL**: https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct — review model-card terms (upstream identifies Apache-2.0). Not bundled.
- **PyTorch3D**: https://github.com/facebookresearch/pytorch3d — BSD; not bundled. The optional CPU test environment uses CPU PyTorch without checkpoints.

The furniture models in `stageai/static/furniture.js` are authored procedurally for this app. No third-party furniture mesh library or paid model-generation service is required. Python dependencies retain their distributed package licenses in the virtual environment.

