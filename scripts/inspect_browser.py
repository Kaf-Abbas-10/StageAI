"""Capture startup diagnostics without modifying projects."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    page=b.new_page(viewport={"width":1600,"height":1000})
    page.on('pageerror',lambda e:print('PAGE ERROR:',e))
    page.on('console',lambda m:print('CONSOLE:',m.type,m.text) if m.type in ('warning','error') else None)
    page.goto('http://127.0.0.1:5174',wait_until='networkidle');page.wait_for_function('window.stageai?.ready')
    page.locator('[data-kind="sofa"]').click();page.wait_for_timeout(500)
    page.screenshot(path='test-results/selected-layout.png')
    print(page.locator('#object-properties').bounding_box(),page.locator('.warnings-section').bounding_box())
    b.close()
