"""Exercise a real pointer drag of a Three.js transform handle in Chrome."""
import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    page=b.new_page(viewport={'width':1600,'height':1000})
    page.on('pageerror',lambda e:print('PAGE ERROR',e))
    page.goto('http://127.0.0.1:5174',wait_until='networkidle');page.wait_for_function('window.stageai?.ready')
    page.locator('[data-kind="chair"]').click();page.wait_for_timeout(300)
    result=page.evaluate('''async()=>{const T=await import('three');const c=window.stageai.world.children.find(n=>n.isTransformControls);const meshes=c._gizmo.gizmo.translate.children.filter(n=>n.name==='X'&&n.isMesh);const r=window.stageai.renderer.domElement.getBoundingClientRect();return meshes.map(n=>{n.geometry.computeBoundingBox();const center=n.geometry.boundingBox.getCenter(new T.Vector3()).applyMatrix4(n.matrixWorld).project(window.stageai.camera());return {x:r.x+(center.x+1)*r.width/2,y:r.y+(1-center.y)*r.height/2};});}''')
    before=page.evaluate('window.stageai.getState().objects[0].position')
    dragged=False
    for point in result:
        page.mouse.move(point['x'],point['y']);page.wait_for_timeout(100)
        axis=page.evaluate('window.stageai.world.children.find(n=>n.isTransformControls).axis')
        if axis=='X':
            page.mouse.down();page.mouse.move(point['x']+60,point['y'],steps=12);page.mouse.up();page.wait_for_timeout(300);dragged=True;break
    after=page.evaluate('window.stageai.getState().objects[0].position')
    assert dragged and abs(after[0]-before[0])>.01,(result,before,after)
    result={'check':'Real pointer drag on X handle moves selected furniture','before':before,'after':after}
    from pathlib import Path
    Path('test-results/gizmo-result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    page.screenshot(path='test-results/gizmo-drag.png')
    b.close()
