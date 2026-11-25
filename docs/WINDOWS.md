# Windows setup

The lightweight editor supports native Windows, independent of CUDA, WSL, conda, or Node. Use recent desktop Chrome/Edge with WebGL enabled.

1. Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/) if missing. Reopen PowerShell so PATH is refreshed.
2. In the StageAI directory, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1`. Python is installed locally into `.tools/python` if needed; app packages go in `.venv`. Viewer modules are already bundled, or can be downloaded with `scripts/fetch_assets.py`.
3. Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\launch.ps1`. The browser opens after the local server becomes ready. Double-clicking `launch.cmd` uses the same launcher.
4. Stop with Ctrl+C. Reopen with the same command to resume. Saved scenes live in `data/`; use .stageai downloads as portable backups.

`launch.ps1 -NoBrowser -Port 5175` runs without opening a browser. It binds only `127.0.0.1`; it is a local single-user service without remote authentication. Do not expose it to the public network. `STAGEAI_DATA` can select a different local storage directory before launch.

If script execution policy blocks direct `.\launch.ps1`, use the explicit `powershell -ExecutionPolicy Bypass -File` command above, which changes policy only for that process. The launch script does not alter the machine's persistent policy.

No internet is required for guided layout, furniture placement, saving, GLB import/export, or reopening an existing project after setup. The optional AI pipeline has a separate model environment; do not install WorldBuilder's CUDA pins into the editor's Python 3.13 environment.

For development run `setup.ps1 -Dev`. Browser QA uses installed Chrome at `C:\Program Files\Google\Chrome\Application\chrome.exe`; edit `scripts/browser_smoke.py` if your Chrome path differs. No Playwright-managed browser is required.

