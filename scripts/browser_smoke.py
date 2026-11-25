"""Real Chrome acceptance test; run against the local server, no browser download."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"test-results";OUT.mkdir(exist_ok=True)


def main():
    errors=[];checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True,args=['--disable-gpu-sandbox'])
        page=browser.new_page(viewport={"width":1600,"height":1000},device_scale_factor=1,accept_downloads=True)
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("console",lambda m:errors.append(m.text) if m.type=="error" else None)
        page.on("dialog",lambda d:d.accept())
        page.goto("http://127.0.0.1:5174",wait_until="networkidle")
        page.wait_for_function("window.stageai?.ready",timeout=60000)
        assert page.locator('.furniture-card').count()==14
        checks.append("Studio initializes with 14 local procedural asset previews")
        page.screenshot(path=str(OUT/"studio-empty.png"))
        page.get_by_role('button',name='Add Sofa',exact=True).click()
        page.wait_for_function("window.stageai.getState().objects.length===1")
        page.locator('#object-name').fill('My sofa');page.locator('#object-name').press('Tab')
        page.locator('#object-x').fill('1.1');page.locator('#object-x').press('Tab')
        page.locator('#object-rotation').fill('45');page.locator('#object-rotation').press('Tab')
        page.wait_for_timeout(150)
        obj=page.evaluate('window.stageai.getState().objects[0]')
        assert obj['name']=='My sofa' and obj['rotation']==45 and abs(obj['position'][0]-1.1)<.001,obj
        checks.append("Furniture added, selected, renamed, moved and rotated")
        page.locator('#object-width').fill('1.8');page.locator('#object-width').press('Tab')
        page.wait_for_timeout(200)
        assert page.evaluate('window.stageai.getState().objects[0].dimensions[0]')==1.8
        page.locator('#object-x').fill('100');page.locator('#object-x').press('Tab')
        page.wait_for_timeout(200)
        assert page.evaluate('window.stageai.getState().objects[0].position[0]')<2
        checks.append("Furniture dimensions edit correctly and wall bounds constrain extreme movement")
        page.locator('#duplicate-btn').click();page.wait_for_function("window.stageai.getState().objects.length===2")
        page.locator('#delete-btn').click();page.wait_for_function("window.stageai.getState().objects.length===1")
        page.locator('#undo-btn').click();page.wait_for_function("window.stageai.getState().objects.length===2")
        page.locator('#redo-btn').click();page.wait_for_function("window.stageai.getState().objects.length===1")
        checks.append("Duplicate, delete, undo and redo preserve scene state")
        # Camera-space click hits a mesh and selects its editable root.
        page.evaluate('window.stageai.select(null)')
        point=page.evaluate("""async()=>{const T=await import('three');const n=window.stageai.world.getObjectByName('My sofa');const center=new T.Box3().setFromObject(n).getCenter(new T.Vector3());center.project(window.stageai.camera());const r=window.stageai.renderer.domElement.getBoundingClientRect();return {x:r.x+(center.x+1)/2*r.width,y:r.y+(-center.y+1)/2*r.height};}""")
        page.mouse.click(point['x'],point['y']);page.wait_for_function('window.stageai.getSelected()!==null')
        checks.append("Clicking rendered furniture selects it in the viewport")
        page.locator('#top-btn').click();page.locator('#perspective-btn').click();page.locator('#walk-btn').click();page.keyboard.press('w');page.keyboard.press('Escape')
        page.locator('#wireframe-btn').click();page.locator('#wireframe-btn').click()
        checks.append("Top view, perspective, walkthrough and wireframe controls execute")
        page.locator('#room-width').fill('6');page.locator('#room-width').press('Tab')
        page.locator('#measured').check()
        page.locator('#save-btn').click();page.wait_for_function("document.querySelector('#save-state').textContent==='Saved locally'")
        before=page.evaluate('window.stageai.getState()')
        pid=page.evaluate('window.stageai.projectId()')
        page.reload(wait_until='networkidle');page.wait_for_function('window.stageai?.ready',timeout=60000)
        after=page.evaluate('window.stageai.getState()');assert before==after
        checks.append("Edited room dimensions, user-measured label, furniture and camera survive save/reload")
        page.evaluate("window.stageai.addFurniture('chair');window.stageai.addFurniture('table');window.stageai.addFurniture('plant');window.stageai.addFurniture('rug');")
        page.wait_for_timeout(700);page.evaluate('window.stageai.select(null)')
        page.screenshot(path=str(OUT/"studio-furnished.png"))
        with page.expect_download(timeout=60000) as d:page.locator('#export-btn').click()
        d.value.save_as(str(OUT/'browser-export.glb'))
        import trimesh
        scene=trimesh.load(OUT/'browser-export.glb',force='scene',process=False)
        assert len(scene.geometry)>10 and 'My sofa' in str(scene.graph.nodes)
        checks.append(f"Browser GLB export opens in trimesh ({len(scene.geometry)} geometries, named sofa retained)")
        # Exercise photo upload using a real photograph, never a synthetic UI fixture.
        fixture=ROOT/'tests/fixtures/living-room.jpg'
        if fixture.exists():
            page.locator('#photo-btn').click();page.locator('#photo-file').set_input_files(str(fixture));page.wait_for_function("!document.querySelector('#photo-preview').hidden")
            page.screenshot(path=str(OUT/'photo-guided.png'))
            page.locator('#reconstruct-btn').click();page.wait_for_function("window.stageai.getState().provenance==='guided-photo-projection'",timeout=60000)
            page.wait_for_function("!document.querySelector('#photo-dialog').open && document.querySelector('#loading').hidden")
            assert page.evaluate('window.stageai.getState().objects.length')==0
            page.screenshot(path=str(OUT/'real-photo-room.png'))
            checks.append("Real room photograph uploads, projects a floor texture, produces a guided 3D shell, and invents no detected furniture")
            page.reload(wait_until='networkidle');page.wait_for_function('window.stageai?.ready',timeout=60000)
            page.locator('#photo-btn').click();page.wait_for_function("document.querySelector('#photo-size').textContent==='Preserved original'")
            checks.append("Saved project reopens its preserved original photograph for repeated reconstruction")
            page.locator('#processing-mode').select_option('worldbuilder');page.locator('#reconstruct-btn').click()
            page.wait_for_function("document.querySelector('#progress-detail').textContent.includes('insufficient_vram')",timeout=30000)
            assert page.evaluate('window.stageai.getState().provenance')=='guided-photo-projection'
            checks.append("WorldBuilder inference attempt on 8 GB GPU fails visibly with insufficient_vram; current scene is preserved")
            page.locator('#photo-dialog .close').click()
        # Actual imported WorldBuilder output is optional and separate from inference.
        glb=ROOT/'test-results/official-living-room.glb'
        if glb.exists():
            page.locator('#import-glb-btn').click();page.locator('#import-glb-file').set_input_files(str(glb));page.locator('#import-scale').fill(str(json.loads((OUT/'official-layout.json').read_text())['estimated_metric_scale']));page.locator('#import-confirm').click()
            page.wait_for_function("window.stageai.getState().provenance==='imported-glb'",timeout=120000)
            page.wait_for_function("!document.querySelector('#import-dialog').open && document.querySelector('#loading').hidden",timeout=120000)
            assert page.evaluate('window.stageai.getState().objects.length')>3
            page.locator('#show-walls').uncheck();page.wait_for_timeout(1000)
            page.screenshot(path=str(OUT/'official-worldbuilder-scene.png'))
            checks.append("Genuine upstream reconstructed GLB imports into independently editable named meshes (not generated here)")
            page.locator('#scene-tab').click();page.locator('.scene-item[data-object-id]').first.click()
            original=page.locator('#object-name').input_value()
            page.locator('#object-name').fill('Verified imported mesh');page.locator('#object-name').press('Tab')
            page.locator('#object-rotation').fill('15');page.locator('#object-rotation').press('Tab')
            page.wait_for_timeout(500)
            page.locator('#save-btn').click();page.wait_for_function("document.querySelector('#save-state').textContent==='Saved locally'")
            page.reload(wait_until='networkidle');page.wait_for_function('window.stageai?.ready',timeout=120000)
            assert page.evaluate("window.stageai.getState().objects.some(o=>o.name==='Verified imported mesh'&&o.rotation===15)")
            checks.append("Imported textured mesh can be selected, renamed, rotated, saved and reloaded")
            with page.expect_download(timeout=120000) as d:page.locator('#export-btn').click()
            d.value.save_as(str(OUT/'imported-roundtrip.glb'))
            imported=trimesh.load(OUT/'imported-roundtrip.glb',force='scene',process=False)
            assert len(imported.geometry)>3 and any(g.visual.kind=='texture' for g in imported.geometry.values())
            checks.append("Edited real WorldBuilder scene exports and reopens with embedded textured meshes")
        assert not errors,errors
        checks.append("No browser console errors or unhandled JavaScript exceptions")
        browser.close()
    result={'checks':checks,'console_errors':errors}
    (OUT/'browser-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
