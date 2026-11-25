import * as THREE from 'three';
import {OrbitControls} from 'three/addons/OrbitControls.js';
import {TransformControls} from 'three/addons/TransformControls.js';
import {GLTFLoader} from 'three/addons/GLTFLoader.js';
import {GLTFExporter} from 'three/addons/GLTFExporter.js';
import {catalog,createFurniture,previewFurniture} from './furniture.js';

const $=id=>document.getElementById(id);
const icons={folder:'M3 7h6l2 2h10v11H3z M3 7V4h6l2 3',save:'M4 3h13l4 4v14H3V3z M7 3v6h10V3 M7 21v-8h10v8',download:'M12 3v12m-5-5 5 5 5-5 M4 17v4h16v-4',image:'M3 3h18v18H3z M3 16l6-6 5 5 3-3 4 4 M15 7h.01',cube:'m12 3 9 5-9 5-9-5 9-5 M3 8v10l9 5 9-5V8 M12 13v10',search:'M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16 M16 16l6 6',import:'M12 3v12m-5-5 5 5 5-5 M3 15v6h18v-6',plan:'M3 3h18v18H3z M3 13h7V3 M10 13h11',walk:'M14 4a1.5 1.5 0 1 0 0-.1 M9 8l4-1 3 5 4 1 M13 7l-2 7-5 6 M11 14l5 2 1 5 M9 8l-3 5',focus:'M3 8V3h5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M8 8h8v8H8z',wire:'M3 3h18v18H3z M3 3l18 18 M21 3 3 21 M12 3v18 M3 12h18',move:'M12 2v20 M2 12h20 M8 6l4-4 4 4 M8 18l4 4 4-4 M6 8l-4 4 4 4 M18 8l4 4-4 4',rotate:'M20 7a9 9 0 1 0 1 9 M20 2v6h-6',scale:'M4 14v6h6 M14 4h6v6 M4 20l6-6 M20 4l-6 6',undo:'M9 5 3 11l6 6 M3 11h11a6 6 0 0 1 6 6',redo:'M15 5l6 6-6 6 M21 11H10a6 6 0 0 0-6 6',select:'M4 3v17l5-5 4 7 4-2-4-7h7z',copy:'M8 8h13v13H8z M16 8V3H3v13h5',trash:'M3 6h18 M9 6V3h6v3 M6 6l1 15h10l1-15 M10 10v7 M14 10v7',info:'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20 M12 10v7 M12 7h.01',plus:'M12 4v16 M4 12h16',sparkles:'m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z'};
const icon=name=>`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[name]||icons.cube}"/></svg>`;
document.querySelectorAll('[data-icon]').forEach(el=>el.insertAdjacentHTML('afterbegin',icon(el.dataset.icon)));
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone=x=>structuredClone(x);
const uuid=()=>crypto.randomUUID().replaceAll('-','');
let toastTimer;
function toast(message,error=false){$('toast').textContent=message;$('toast').classList.toggle('error',error);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,error?11000:4500);}
async function api(path,options={}){
 const r=await fetch(path,options);if(!r.ok){let d;try{d=await r.json();}catch{d={detail:r.statusText};}const detail=Array.isArray(d.detail)?d.detail.map(e=>`${e.loc.join('.')}: ${e.msg}`).join('\n'):(d.detail||d.error||r.statusText);throw new Error(detail);}
 return r.headers.get('content-type')?.includes('application/json')?r.json():r.blob();
}
function jsonOptions(method,data){return {method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)};}
function error(e){console.error(e);toast(e.message||String(e),true);$('status-text').textContent='Action needs attention';}
const initial={version:1,name:'Untitled room',room:{width:5,depth:4,height:2.7,source:'estimated'},room_type:'living',shell:true,floor_texture:null,wall_color:'#d3ddd5',objects:[],camera:{},settings:{},warnings:['Manual room: dimensions are estimates until you supply measurements. Walls use an automatic cutaway so furniture stays visible.'],provenance:'manual'};
let state=clone(initial),projectId=null,hasOriginal=false,selectedId=null,dirty=false,history=[],future=[],transformStart=null,renderToken=0,capabilities=null;
let tool='translate',wireframe=false,topView=false,walk=false,busy=false;
const viewport=$('viewport'),world=new THREE.Scene();world.background=new THREE.Color('#293b31');world.fog=new THREE.Fog('#293b31',24,65);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;viewport.append(renderer.domElement);
let camera=new THREE.PerspectiveCamera(42,1,.05,250);camera.position.set(8,6.5,9);
const ortho=new THREE.OrthographicCamera(-7,7,7,-7,.01,250);ortho.position.set(0,18,0);ortho.up.set(0,0,-1);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.target.set(0,.5,0);orbit.enableDamping=true;orbit.minDistance=.5;orbit.maxDistance=45;orbit.maxPolarAngle=Math.PI*.49;
const controls=new TransformControls(camera,renderer.domElement);controls.setSize(.85);world.add(controls);
const ambient=new THREE.HemisphereLight('#e6f1e8','#566d56',2.3);world.add(ambient);
const sun=new THREE.DirectionalLight('#fff0d6',3.6);sun.position.set(-3,9,5);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-12,right:12,top:12,bottom:-12,near:.1,far:35});sun.shadow.normalBias=.025;sun.shadow.bias=-.0002;sun.shadow.radius=4;world.add(sun);
const fill=new THREE.DirectionalLight('#c5e0d2',1);fill.position.set(5,4,-7);world.add(fill);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:'#293b31',roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.15;ground.receiveShadow=true;world.add(ground);
const grid=new THREE.GridHelper(40,80,'#526955','#3b5141');grid.position.y=-.12;grid.material.transparent=true;grid.material.opacity=.4;world.add(grid);
const content=new THREE.Group();content.name='StageAI';world.add(content);
const selectionBox=new THREE.Box3Helper(new THREE.Box3(),0xb8f2ce);selectionBox.visible=false;world.add(selectionBox);
let shellGroup=new THREE.Group(),wallMeshes=[],objectNodes=new Map(),assetCache=new Map(),textureCache=new Map();
const loader=new GLTFLoader();const textureLoader=new THREE.TextureLoader();
function assetUrl(name){return `/api/projects/${projectId}/assets/${encodeURIComponent(name)}`;}
async function assetScene(asset){const key=`${projectId}/${asset}`;if(!assetCache.has(key))assetCache.set(key,loader.loadAsync(assetUrl(asset)).catch(e=>{assetCache.delete(key);throw new Error(`Cannot load mesh asset ${asset}: ${e.message}`);}));return (await assetCache.get(key)).scene;}
async function floorTexture(){if(!state.floor_texture)return null;const key=`${projectId}/${state.floor_texture}`;if(!textureCache.has(key))textureCache.set(key,textureLoader.loadAsync(assetUrl(state.floor_texture)));const t=await textureCache.get(key);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=Math.min(renderer.capabilities.getMaxAnisotropy(),8);return t;}
function disposeRoot(root){root.traverse(n=>{n.geometry?.dispose();if(n.material)(Array.isArray(n.material)?n.material:[n.material]).forEach(m=>m.dispose());});}
function markDirty(){dirty=true;$('save-state').textContent='Unsaved changes';$('status-text').textContent='Scene updated';}
function pushHistory(){history.push(clone(state));if(history.length>60)history.shift();future=[];}
function recordChange(fn){pushHistory();fn();markDirty();return rebuild().catch(error);}
function constrain(o){
 o.position[1]=Math.max(0,o.position[1]);
 if($('snap-grid').checked){o.position[0]=Math.round(o.position[0]*10)/10;o.position[2]=Math.round(o.position[2]*10)/10;}
 if($('snap-floor').checked&&o.group!=='structure'&&state.shell){const a=THREE.MathUtils.degToRad(o.rotation),c=Math.abs(Math.cos(a)),s=Math.abs(Math.sin(a));const hw=(o.dimensions[0]*c+o.dimensions[2]*s)/2,hd=(o.dimensions[0]*s+o.dimensions[2]*c)/2;const x=Math.max(0,state.room.width/2-hw),z=Math.max(0,state.room.depth/2-hd);o.position[0]=THREE.MathUtils.clamp(o.position[0],-x,x);o.position[2]=THREE.MathUtils.clamp(o.position[2],-z,z);}
}
function boxMesh(w,h,d,color){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:.92}));m.castShadow=true;m.receiveShadow=true;return m;}
async function buildShell(){
 const room=state.room,w=room.width,d=room.depth,h=room.height;
 const shell=new THREE.Group();shell.name='Structure';wallMeshes=[];
 const floor=boxMesh(w,.12,d,'#adbaa7');floor.position.y=-.065;floor.name='room_floor';floor.visible=$('show-floor').checked;shell.add(floor);
 const map=await floorTexture();const surface=new THREE.Mesh(new THREE.PlaneGeometry(w,d),new THREE.MeshStandardMaterial({color:map?'#ffffff':'#a8b49c',map,roughness:1}));surface.rotation.x=-Math.PI/2;surface.position.y=.001;surface.receiveShadow=true;surface.name='room_floor_surface';surface.visible=$('show-floor').checked;shell.add(surface);
 for(const [name,axis,sign] of [['room_wall_x_min','x',-1],['room_wall_x_max','x',1],['room_wall_z_min','z',-1],['room_wall_z_max','z',1]]){const m=boxMesh(axis==='x'?.1:w+.2,h,axis==='z'?.1:d,state.wall_color);m.position.set(axis==='x'?sign*(w/2+.05):0,h/2,axis==='z'?sign*(d/2+.05):0);m.name=name;m.userData.wall={axis,sign};shell.add(m);wallMeshes.push(m);}
 const ceiling=boxMesh(w,.08,d,state.wall_color);ceiling.position.y=h+.04;ceiling.name='room_ceiling';ceiling.visible=$('show-ceiling').checked;shell.add(ceiling);
 return shell;
}
async function buildObject(o){
 const pivot=new THREE.Group();pivot.name=o.name;pivot.userData={objectId:o.id,kind:o.kind,evidence:o.evidence};
 let model;
 if(o.kind==='mesh'){
  const original=(await assetScene(o.asset)).getObjectByName(o.mesh_name);if(!original)throw new Error(`Missing mesh node: ${o.mesh_name}`);
  model=original.clone(true);model.traverse(n=>{if(n.geometry)n.geometry=n.geometry.clone();if(n.material)n.material=Array.isArray(n.material)?n.material.map(m=>m.clone()):n.material.clone();});
  model.position.set(0,0,0);model.updateMatrixWorld(true);
  const bounds=new THREE.Box3().setFromObject(model),size=bounds.getSize(new THREE.Vector3());
  model.position.sub(new THREE.Vector3((bounds.min.x+bounds.max.x)/2,bounds.min.y,(bounds.min.z+bounds.max.z)/2));
  const normalized=new THREE.Group();normalized.add(model);normalized.scale.set(1/Math.max(size.x,.001),1/Math.max(size.y,.001),1/Math.max(size.z,.001));model=normalized;
 }else model=createFurniture(o.kind,o.color);
 pivot.add(model);pivot.position.fromArray(o.position);pivot.rotation.y=THREE.MathUtils.degToRad(o.rotation);pivot.scale.fromArray(o.dimensions);pivot.visible=o.visible;
 pivot.traverse(n=>{if(n.isMesh){n.castShadow=true;n.receiveShadow=true;(Array.isArray(n.material)?n.material:[n.material]).forEach(m=>m.wireframe=wireframe);}});
 return pivot;
}
async function rebuild(){
 const token=++renderToken;controls.detach();selectionBox.visible=false;
 const next=new THREE.Group();next.name='Room';
 try{
  if(state.shell)next.add(await buildShell());
  const nodes=new Map();for(const o of state.objects){const node=await buildObject(o);nodes.set(o.id,node);next.add(node);}
  if(token!==renderToken){disposeRoot(next);return;}
  for(const child of [...content.children]){content.remove(child);disposeRoot(child);}content.add(next);objectNodes=nodes;shellGroup=next.children.find(n=>n.name==='Structure');
  next.traverse(n=>{if(n.material)(Array.isArray(n.material)?n.material:[n.material]).forEach(m=>m.wireframe=wireframe);});
  updateUI();select(selectedId);
 }catch(e){disposeRoot(next);throw e;}
}
function updateUI(){
 $('project-name').value=state.name;for(const [id,key] of [['room-width','width'],['room-depth','depth'],['room-height','height']])$(id).value=state.room[key];
 $('measured').checked=state.room.source==='user-measured';$('dimension-source').textContent=state.room.source==='user-measured'?'USER MEASURED':'ESTIMATED';$('dimension-source').classList.toggle('measured',state.room.source==='user-measured');
 $('dimensions-label').textContent=`${state.room.width.toFixed(1)} × ${state.room.depth.toFixed(1)} m`;
 $('scene-provenance').textContent=({'manual':'Manual room','guided-photo-projection':'Guided photo layout','worldbuilder':'WorldBuilder AI','imported-glb':'Imported GLB'})[state.provenance]||state.provenance;
 $('object-count').textContent=`${state.objects.length} object${state.objects.length===1?'':'s'}`;$('scene-count').textContent=state.objects.length;
 $('empty-hint').hidden=state.objects.length>0||state.provenance!=='manual';
 $('warnings-count').textContent=state.warnings.length;$('warnings-content').innerHTML=state.warnings.map(x=>`<p>${escapeHtml(x)}</p>`).join('')||'<p>No reconstruction warnings.</p>';
 $('undo-btn').disabled=!history.length;$('redo-btn').disabled=!future.length;
 updateHierarchy();
}
function updateHierarchy(){
 $('hierarchy').innerHTML='';
 if(state.shell){const group=document.createElement('div');group.className='hierarchy-group';group.innerHTML=`<h3>Structure</h3><button class="scene-item" id="select-room">${icon('cube')}<span>Room shell</span><small>PARAMETRIC</small></button>`;$('hierarchy').append(group);group.querySelector('button').onclick=()=>{select(null);toast('Edit the room dimensions in Room settings.');};}
 for(const kind of ['structure','furniture','decorative']){const list=state.objects.filter(o=>o.group===kind);if(!list.length)continue;const group=document.createElement('div');group.className='hierarchy-group';group.innerHTML=`<h3>${escapeHtml(kind)} · ${list.length}</h3>`;
 for(const o of list){const b=document.createElement('button');b.className='scene-item'+(o.id===selectedId?' active':'')+(!o.visible?' hidden-item':'');b.dataset.objectId=o.id;b.innerHTML=`${icon('cube')}<span>${escapeHtml(o.name)}</span><small>${o.kind==='mesh'?'MESH':'ASSET'}</small>`;b.onclick=()=>select(o.id);group.append(b);} $('hierarchy').append(group);}
}
function setTool(mode){tool=mode;controls.setMode(mode);controls.showX=mode!=='rotate';controls.showY=mode!=='translate';controls.showZ=mode!=='rotate';if(mode==='rotate'){controls.showX=false;controls.showY=true;controls.showZ=false;}for(const [id,value] of [['move-tool','translate'],['rotate-tool','rotate'],['scale-tool','scale']])$(id).classList.toggle('active',mode===value);}
function selected(){return state.objects.find(o=>o.id===selectedId);}
function select(id){
 const o=state.objects.find(o=>o.id===id);selectedId=o?.id||null;
 $('no-selection').hidden=!!o;$('object-properties').hidden=!o;$('selection-kind').textContent=o?.kind==='mesh'?'Imported mesh':o?.kind||'';
 controls.detach();selectionBox.visible=false;
 if(o){const node=objectNodes.get(o.id);if(node&&o.visible){controls.attach(node);setTool(tool);selectionBox.box.setFromObject(node);selectionBox.visible=true;}
  $('object-name').value=o.name;['x','y','z'].forEach((a,i)=>$('object-'+a).value=Number(o.position[i].toFixed(3)));['width','height','depth'].forEach((a,i)=>$('object-'+a).value=Number(o.dimensions[i].toFixed(3)));$('object-rotation').value=Number(o.rotation.toFixed(2));$('object-color').value=o.color;$('object-color').disabled=o.kind==='mesh';$('object-evidence').textContent=o.evidence;
 }
 document.querySelectorAll('.scene-item[data-object-id]').forEach(b=>b.classList.toggle('active',b.dataset.objectId===selectedId));
}
function addFurniture(item){
 if(busy)return;const o={id:uuid(),name:item.name,kind:item.kind,group:['door','window'].includes(item.kind)?'structure':['plant','rug','decor','lamp'].includes(item.kind)?'decorative':'furniture',position:[0,item.kind==='window'?1:0,0],rotation:0,dimensions:[...item.dims],color:item.color,asset:null,node:null,mesh_name:null,visible:true,evidence:['door','window'].includes(item.kind)?'Manually placed opening marker; does not cut a hole in a wall':'Procedural library asset; manually placed'};
 selectedId=o.id;recordChange(()=>{constrain(o);state.objects.push(o);});$('status-text').textContent=`Added ${item.name.toLowerCase()}`;
}
function duplicate(){const o=selected();if(!o)return;selectedId=uuid();recordChange(()=>{const copy=clone(o);copy.id=selectedId;copy.name+=' copy';copy.position[0]+=.35;copy.position[2]+=.25;constrain(copy);state.objects.push(copy);});}
function remove(){if(!selectedId)return;recordChange(()=>{state.objects=state.objects.filter(o=>o.id!==selectedId);selectedId=null;});}
async function undo(){if(!history.length)return;future.push(clone(state));state=history.pop();markDirty();await rebuild();}
async function redo(){if(!future.length)return;history.push(clone(state));state=future.pop();markDirty();await rebuild();}
controls.addEventListener('dragging-changed',e=>{orbit.enabled=!e.value;if(e.value){transformStart=clone(state);}else if(transformStart){history.push(transformStart);future=[];transformStart=null;const o=selected();if(o){constrain(o);const n=objectNodes.get(o.id);n.position.fromArray(o.position);n.scale.fromArray(o.dimensions);}markDirty();select(selectedId);updateUI();}});
controls.addEventListener('objectChange',()=>{const o=selected(),n=controls.object;if(!o||!n)return;o.position=n.position.toArray();o.rotation=THREE.MathUtils.radToDeg(n.rotation.y);o.dimensions=n.scale.toArray().map(x=>THREE.MathUtils.clamp(Math.abs(x),.001,100));constrain(o);n.position.fromArray(o.position);n.scale.fromArray(o.dimensions);selectionBox.box.setFromObject(n);});
const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let down=null;
renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY,!!controls.axis];});
renderer.domElement.addEventListener('pointerup',e=>{if(!down||down[2]||controls.dragging||walk||e.button!==0||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4)return;const r=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);const visible=[...objectNodes.values()].filter(n=>n.visible);const hit=ray.intersectObjects(visible,true)[0];let node=hit?.object;while(node&&!node.userData.objectId)node=node.parent;select(node?.userData.objectId||null);});
function resize(){const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;if(camera.isPerspectiveCamera)camera.updateProjectionMatrix();ortho.left=-7*w/h;ortho.right=7*w/h;ortho.top=7;ortho.bottom=-7;ortho.updateProjectionMatrix();}
new ResizeObserver(resize).observe(viewport);
function resetCamera(){setWalk(false);if(topView){camera=ortho;const span=Math.max(state.room.width,state.room.depth)*.8;ortho.zoom=7/Math.max(span,3);ortho.position.set(0,20,0);ortho.updateProjectionMatrix();orbit.target.set(0,0,0);}else{camera=perspectiveCamera;const size=Math.max(state.room.width,state.room.depth);camera.position.set(size*1.15,size*.95,size*1.25);orbit.target.set(0,.4,0);}orbit.object=camera;controls.camera=camera;orbit.enableRotate=!topView;orbit.update();resize();}
const perspectiveCamera=camera;
function changeView(top){topView=top;$('top-btn').classList.toggle('active',top);$('perspective-btn').classList.toggle('active',!top);resetCamera();}
let keys=new Set(),lastTime=performance.now();
function setWalk(value){walk=value;$('walk-btn').classList.toggle('active',walk);$('navigation-help').textContent=walk?'WASD to walk · Hold right mouse to look · Esc to exit':'Drag to orbit · Right-drag to pan · Scroll to zoom';orbit.enabled=!walk;if(walk){topView=false;camera=perspectiveCamera;camera.position.set(0,Math.min(1.65,state.room.height-.15),state.room.depth*.3);orbit.object=camera;controls.camera=camera;orbit.target.set(0,camera.position.y,-state.room.depth/2);camera.lookAt(orbit.target);controls.detach();$('top-btn').classList.remove('active');$('perspective-btn').classList.add('active');}else{keys.clear();orbit.enabled=true;}resize();}
let lookDown=false;
renderer.domElement.addEventListener('contextmenu',e=>e.preventDefault());renderer.domElement.addEventListener('pointerdown',e=>{if(walk&&e.button===2){lookDown=true;renderer.domElement.setPointerCapture(e.pointerId);}});renderer.domElement.addEventListener('pointerup',()=>lookDown=false);
renderer.domElement.addEventListener('pointermove',e=>{if(walk&&lookDown){const q=new THREE.Euler().setFromQuaternion(camera.quaternion,'YXZ');q.y-=e.movementX*.004;q.x=THREE.MathUtils.clamp(q.x-e.movementY*.004,-1.4,1.4);q.z=0;camera.quaternion.setFromEuler(q);}});
function tick(time){requestAnimationFrame(tick);const dt=Math.min((time-lastTime)/1000,.05);lastTime=time;
 if(walk){const dir=new THREE.Vector3();camera.getWorldDirection(dir);dir.y=0;dir.normalize();const side=new THREE.Vector3().crossVectors(dir,new THREE.Vector3(0,1,0));const step=dt*2.2;let motion=new THREE.Vector3();if(keys.has('w'))motion.addScaledVector(dir,step);if(keys.has('s'))motion.addScaledVector(dir,-step);if(keys.has('d'))motion.addScaledVector(side,step);if(keys.has('a'))motion.addScaledVector(side,-step);camera.position.add(motion);if(state.shell){camera.position.x=THREE.MathUtils.clamp(camera.position.x,-state.room.width/2+.15,state.room.width/2-.15);camera.position.z=THREE.MathUtils.clamp(camera.position.z,-state.room.depth/2+.15,state.room.depth/2-.15);}}
 else orbit.update();
 for(const m of wallMeshes){const {axis,sign}=m.userData.wall;m.visible=$('show-walls').checked&&!topView&&(walk||sign*camera.position[axis]<(axis==='x'?state.room.width:state.room.depth)/2);}
 for(const o of state.objects){const node=objectNodes.get(o.id);if(node&&o.group==='structure'&&o.kind==='mesh'){const nm=o.name.toLowerCase();if(nm.includes('ceiling'))node.visible=o.visible&&$('show-ceiling').checked;else if(nm.includes('floor'))node.visible=o.visible&&$('show-floor').checked;else if(nm.includes('wall'))node.visible=o.visible&&$('show-walls').checked;}}
 if(selectedId&&objectNodes.get(selectedId))selectionBox.box.setFromObject(objectNodes.get(selectedId));renderer.render(world,camera);
}
requestAnimationFrame(tick);
function captureCamera(){return {mode:topView?'top':'perspective',position:camera.position.toArray(),target:orbit.target.toArray(),zoom:camera.zoom,visibility:{floor:$('show-floor').checked,walls:$('show-walls').checked,ceiling:$('show-ceiling').checked},snap_grid:$('snap-grid').checked,constrain:$('snap-floor').checked};}
async function loadProject(id){
 if(dirty&&!confirm('Open this project and discard unsaved changes?'))return;
 $('loading').hidden=false;
 try{const result=await api(`/api/projects/${id}`);for(const pending of textureCache.values())pending.then(t=>t.dispose()).catch(()=>{});textureCache.clear();assetCache.clear();state=result.scene;projectId=id;hasOriginal=!!result.has_original;photoProject=null;photoImage=null;selectedId=null;history=[];future=[];dirty=false;localStorage.setItem('stageai-project',id);
 const view=state.camera||{};if(view.visibility){$('show-floor').checked=view.visibility.floor;$('show-walls').checked=view.visibility.walls;$('show-ceiling').checked=view.visibility.ceiling;}$('snap-grid').checked=view.snap_grid||false;$('snap-floor').checked=view.constrain!==false;
 await rebuild();changeView(view.mode==='top');if(view.position?.length===3&&view.position.every(Number.isFinite)&&view.target?.length===3&&view.target.every(Number.isFinite)){camera.position.fromArray(view.position);orbit.target.fromArray(view.target);camera.zoom=Number.isFinite(view.zoom)?THREE.MathUtils.clamp(view.zoom,.1,20):1;camera.updateProjectionMatrix();orbit.update();}
 $('save-state').textContent='Saved locally';$('status-text').textContent='Project loaded';$('projects-dialog').close();
 }finally{$('loading').hidden=true;}
}
async function saveProject(notify=true){
 if(busy)throw new Error('Wait for reconstruction to finish before saving.');
 state.camera=captureCamera();state.name=$('project-name').value.trim()||'Untitled room';
 if(!projectId){const created=await api('/api/projects',{method:'POST'});projectId=created.id;}
 await api(`/api/projects/${projectId}`,jsonOptions('PUT',state));localStorage.setItem('stageai-project',projectId);dirty=false;$('save-state').textContent='Saved locally';$('status-text').textContent='All changes saved';if(notify)toast('Project saved on this PC.');return projectId;
}
function download(blob,name){const link=document.createElement('a');const url=URL.createObjectURL(blob);link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
async function exportGLB(){
 $('export-btn').disabled=true;$('status-text').textContent='Preparing GLB export…';
 try{await saveProject(false);
  // Export a clone with cutaway/inspection visibility disabled. Structure toggles
  // affect inspection only; deleted nodes are absent from the scene graph.
  const out=content.clone(true);out.name=state.name;out.userData={generator:'StageAI',units:'metres',provenance:state.provenance,warnings:state.warnings};out.traverse(n=>{n.visible=true;if(n.material){n.material=Array.isArray(n.material)?n.material.map(m=>m.clone()):n.material.clone();(Array.isArray(n.material)?n.material:[n.material]).forEach(m=>m.wireframe=false);}});
  const result=await new Promise((resolve,reject)=>new GLTFExporter().parse(out,resolve,reject,{binary:true,onlyVisible:false}));
  const form=new FormData();form.append('file',new Blob([result],{type:'model/gltf-binary'}),'room.glb');const blob=await api(`/api/projects/${projectId}/export`,{method:'POST',body:form});download(blob,state.name.replace(/[^a-zA-Z0-9_-]/g,'_')+'.glb');toast('GLB exported. Open it in Blender with File → Import → glTF 2.0.');$('status-text').textContent='GLB validated and exported';
 }finally{$('export-btn').disabled=false;}
}
async function showProjects(){const list=await api('/api/projects');$('projects-list').innerHTML=list.length?'':'<p class="muted">Your saved rooms will appear here.</p>';for(const p of list){const row=document.createElement('div');row.className='project-row';row.innerHTML=`<div><strong>${escapeHtml(p.name)}</strong><small>${p.objects} objects · ${escapeHtml(p.provenance)} · ${new Date(p.modified*1000).toLocaleDateString()}</small></div><button class="button">Open</button>`;row.querySelector('button').onclick=()=>loadProject(p.id).catch(error);$('projects-list').append(row);}$('projects-dialog').showModal();}
async function downloadProject(){await saveProject(false);download(await api(`/api/projects/${projectId}/bundle`),state.name.replace(/[^a-zA-Z0-9_-]/g,'_')+'.stageai');toast('Portable project includes photograph, meshes, textures, and edits.');}
async function newProject(){if(dirty&&!confirm('Create a new room and discard unsaved changes?'))return;state=clone(initial);projectId=null;hasOriginal=false;photoProject=null;photoImage=null;selectedId=null;history=[];future=[];dirty=false;localStorage.removeItem('stageai-project');await rebuild();changeView(false);$('save-state').textContent='New project';$('projects-dialog').close();}

// Photograph preprocessing. Handles are normalized to the rotated/cropped
// image; both the canvas and Pillow apply rotation before crop.
let photoImage=null,photoProject=null,photoRotation=0,corners=[[.25,.58],[.75,.58],[.98,.98],[.02,.98]],dragCorner=-1;
let crop=[0,0,1,1],pollTimer=null;
const photoCanvas=$('photo-canvas');
function drawPhoto(){
 if(!photoImage)return;const rotated=document.createElement('canvas');const ctx=rotated.getContext('2d');const quarter=photoRotation%180!==0;rotated.width=quarter?photoImage.naturalHeight:photoImage.naturalWidth;rotated.height=quarter?photoImage.naturalWidth:photoImage.naturalHeight;ctx.translate(rotated.width/2,rotated.height/2);ctx.rotate(photoRotation*Math.PI/180);ctx.drawImage(photoImage,-photoImage.naturalWidth/2,-photoImage.naturalHeight/2);
 const w=rotated.width*(crop[2]-crop[0]),h=rotated.height*(crop[3]-crop[1]);const ratio=Math.min(900/w,600/h);photoCanvas.width=Math.round(w*ratio);photoCanvas.height=Math.round(h*ratio);const c=photoCanvas.getContext('2d');c.drawImage(rotated,rotated.width*crop[0],rotated.height*crop[1],w,h,0,0,photoCanvas.width,photoCanvas.height);
 c.fillStyle='#b1e7ca33';c.strokeStyle='#b1e7ca';c.lineWidth=2;c.beginPath();corners.forEach((p,i)=>c[i?'lineTo':'moveTo'](p[0]*photoCanvas.width,p[1]*photoCanvas.height));c.closePath();c.fill();c.stroke();corners.forEach((p,i)=>{const x=p[0]*photoCanvas.width,y=p[1]*photoCanvas.height;c.beginPath();c.arc(x,y,14,0,Math.PI*2);c.fillStyle='#c4f0d5';c.fill();c.fillStyle='#204a30';c.font='bold 15px Segoe UI';c.textAlign='center';c.textBaseline='middle';c.fillText(i+1,x,y+1);});
}
photoCanvas.addEventListener('pointerdown',e=>{const r=photoCanvas.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;let min=.09;corners.forEach((p,i)=>{const d=Math.hypot(p[0]-x,p[1]-y);if(d<min){dragCorner=i;min=d;}});photoCanvas.setPointerCapture(e.pointerId);});
photoCanvas.addEventListener('pointermove',e=>{if(dragCorner<0)return;const r=photoCanvas.getBoundingClientRect();corners[dragCorner]=[THREE.MathUtils.clamp((e.clientX-r.left)/r.width,0,1),THREE.MathUtils.clamp((e.clientY-r.top)/r.height,0,1)];drawPhoto();});photoCanvas.addEventListener('pointerup',()=>dragCorner=-1);photoCanvas.addEventListener('pointercancel',()=>dragCorner=-1);
async function openPhoto(){
 $('photo-dialog').showModal();if(busy)return;
 if(hasOriginal&&projectId&&!photoProject){
  $('reconstruct-btn').disabled=true;
  try{photoProject=projectId;photoImage=new Image();photoImage.src=assetUrl('original');await photoImage.decode();
   const saved=state.settings||{};photoRotation=saved.rotation||0;crop=clone(saved.crop||[0,0,1,1]);corners=clone(saved.floor_corners||[[.25,.58],[.75,.58],[.98,.98],[.02,.98]]);
   ['left','top','right','bottom'].forEach((a,i)=>$('crop-'+a).value=crop[i]*100);
   for(const a of ['width','depth','height'])$('photo-'+a).value=state.room[a];$('photo-measured').checked=state.room.source==='user-measured';$('room-type').value=state.room_type;$('dropzone').hidden=true;$('photo-preview').hidden=false;$('photo-size').textContent='Preserved original';$('job-progress').hidden=true;drawPhoto();
  }catch(e){photoProject=null;error(e);}finally{$('reconstruct-btn').disabled=false;}
 }else if(!photoImage){$('dropzone').hidden=false;$('photo-preview').hidden=true;$('job-progress').hidden=true;}
}
async function usePhoto(file){if(!file)return;if(busy)throw new Error('Wait for the current reconstruction.');$('reconstruct-btn').disabled=true;const form=new FormData();form.append('image',file);try{const r=await api('/api/projects/upload',{method:'POST',body:form});photoProject=r.id;photoRotation=0;crop=[0,0,1,1];corners=[[.25,.58],[.75,.58],[.98,.98],[.02,.98]];['left','top','right','bottom'].forEach((a,i)=>$('crop-'+a).value=crop[i]*100);photoImage=new Image();photoImage.src=r.image_url;await photoImage.decode();$('dropzone').hidden=true;$('photo-preview').hidden=false;$('photo-size').textContent=`${r.image_size[0]} × ${r.image_size[1]}`;drawPhoto();$('job-progress').hidden=true;}finally{$('reconstruct-btn').disabled=false;$('photo-file').value='';}}
async function reconstruct(){
 if(!photoProject)throw new Error('Choose a room photograph first.');if(busy)return;
 if(dirty&&!confirm('Create the photo room and discard unsaved changes to the current room?'))return;
 const mode=$('processing-mode').value;
 const settings={mode,rotation:photoRotation,crop,floor_corners:corners,room_type:$('room-type').value,quality:$('quality').value,dimensions:{width:Number($('photo-width').value),depth:Number($('photo-depth').value),height:Number($('photo-height').value),source:$('photo-measured').checked?'user-measured':'estimated'}};
 await api(`/api/projects/${photoProject}/reconstruct`,jsonOptions('POST',settings));busy=true;$('reconstruct-btn').disabled=true;$('job-progress').hidden=false;$('progress-label').textContent='Queued for local processing';$('progress-detail').textContent='';$('progress-fill').style.width='0';$('status-text').textContent='Processing photograph…';
 const current=photoProject;
 const poll=async()=>{try{const j=await api(`/api/projects/${current}/job`);$('progress-label').textContent=j.message;$('progress-fill').style.width=`${j.progress*100}%`;$('status-text').textContent=j.message;
  if(j.status==='failed'){busy=false;$('reconstruct-btn').disabled=false;$('progress-detail').textContent=`${j.error?.code||'failed'}\n${j.error?.fix||''}`;toast(j.error?.message||j.message,true);return;}
  if(j.status==='complete'){busy=false;dirty=false;await loadProject(current);$('photo-dialog').close();$('reconstruct-btn').disabled=false;toast(mode==='guided'?'Guided room ready. Add furniture to start arranging.':'WorldBuilder scene loaded. Review scene notes for reconstruction warnings.');return;}
  pollTimer=setTimeout(poll,800);
 }catch(e){busy=false;$('reconstruct-btn').disabled=false;error(e);}};poll();
}
function updateMode(){const ai=$('processing-mode').value==='worldbuilder';$('quality-label').hidden=!ai;$('mode-info').textContent=ai?'Runs the actual local WorldBuilder pipeline. '+(capabilities?.ai_available?'The inference environment passed preflight. Make sure the local Qwen VLM server is running.':(capabilities?.issues?.map(x=>x.message).join(' ')||'Checking requirements…')):'You mark the floor. We project its photo texture onto an editable rectangular room. Add furniture yourself. This mode does not run AI detection or depth estimation.';$('reconstruct-btn').innerHTML=icon('sparkles')+(ai?'Run WorldBuilder AI':'Create guided room');}

function showInfo(title,html){$('info-title').textContent=title;$('info-body').innerHTML=html;$('info-dialog').showModal();}
async function showCapabilities(){capabilities=await api('/api/capabilities');const c=capabilities;showInfo('Local hardware & AI availability',`<div class="info-row"><strong>${escapeHtml(c.os)} · Python ${escapeHtml(c.python)}</strong>${c.gpus.map(g=>`<p>${escapeHtml(g.name)} · ${(g.total_mb/1024).toFixed(1)} GB total · ${(g.free_mb/1024).toFixed(1)} GB free<br>Driver ${escapeHtml(g.driver)}</p>`).join('')||'<p>No NVIDIA GPU reported.</p>'}</div><div class="info-row"><strong>Guided layout and room editing are available.</strong><p>Full AI pipeline: ${c.ai_available?'environment preflight passed; inference not yet verified':'requirements not met'}.</p></div>${c.issues.map(p=>`<div class="info-row"><strong>${escapeHtml(p.message)}</strong><p>${escapeHtml(p.fix)}</p></div>`).join('')}<p class="muted small">The driver’s CUDA compatibility version does not establish that the CUDA toolkit or PyTorch is installed. See docs/GPU.md.</p>`);}
function renderLibrary(){const query=$('furniture-search').value.toLowerCase();$('furniture-grid').innerHTML='';for(const item of catalog.filter(i=>(i.name+' '+i.category).toLowerCase().includes(query))){const b=document.createElement('button');b.className='furniture-card';b.dataset.kind=item.kind;b.setAttribute('aria-label','Add '+item.name);b.innerHTML=`<img alt="" src="${item.preview||''}"><span>${escapeHtml(item.name)}</span><small>${escapeHtml(item.category)}</small><i class="add">+</i>`;b.onclick=()=>addFurniture(item);$('furniture-grid').append(b);}}

// UI bindings
$('save-btn').onclick=()=>saveProject().catch(error);$('export-btn').onclick=()=>exportGLB().catch(error);$('projects-btn').onclick=()=>showProjects().catch(error);$('new-btn').onclick=()=>newProject().catch(error);$('download-project-btn').onclick=()=>downloadProject().catch(error);
$('import-project-btn').onclick=()=>$('project-file').click();$('project-file').onchange=async e=>{try{if(!e.target.files[0])return;if(dirty&&!confirm('Open the project file and discard unsaved changes?'))return;const f=new FormData();f.append('file',e.target.files[0]);const r=await api('/api/import/project',{method:'POST',body:f});dirty=false;await loadProject(r.id);toast('Portable project opened.');}catch(e){error(e);}finally{$('project-file').value='';}};
$('project-name').onchange=()=>recordChange(()=>state.name=$('project-name').value.trim()||'Untitled room');
for(const id of ['photo-btn','empty-photo'])$(id).onclick=()=>openPhoto().catch(error);
$('photo-file').onchange=e=>usePhoto(e.target.files[0]).catch(error);$('replace-photo').onclick=()=>$('photo-file').click();$('rotate-photo').onclick=()=>{photoRotation=(photoRotation+90)%360;corners=[[.25,.58],[.75,.58],[.98,.98],[.02,.98]];drawPhoto();};
for(const type of ['dragover','dragleave','drop'])$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.toggle('dragover',type==='dragover');if(type==='drop')usePhoto(e.dataTransfer.files[0]).catch(error);});
['left','top','right','bottom'].forEach((a,i)=>$('crop-'+a).onchange=()=>{const candidate=[...crop];candidate[i]=Number($('crop-'+a).value)/100;if(candidate.some(x=>x<0||x>1)||candidate[2]-candidate[0]<.1||candidate[3]-candidate[1]<.1){$('crop-'+a).value=crop[i]*100;toast('Keep at least 10% of the image in each direction.',true);return;}crop=candidate;drawPhoto();});
$('reconstruct-btn').onclick=()=>reconstruct().catch(error);$('processing-mode').onchange=updateMode;
for(const [id,key] of [['room-width','width'],['room-depth','depth'],['room-height','height']])$(id).onchange=()=>{const value=Number($(id).value),min=key==='height'?1.8:1,max=key==='height'?10:50;if(!Number.isFinite(value)||value<min||value>max){$(id).value=state.room[key];toast(`Choose a ${key} between ${min} and ${max} metres.`,true);return;}recordChange(()=>{if(!state.shell){const axis={width:0,height:1,depth:2}[key],factor=value/state.room[key];for(const o of state.objects){o.position[axis]*=factor;o.dimensions[axis]*=factor;}}state.room[key]=value;state.objects.forEach(constrain);});};
$('measured').onchange=()=>recordChange(()=>state.room.source=$('measured').checked?'user-measured':'estimated');
for(const id of ['show-floor','show-walls','show-ceiling'])$(id).onchange=()=>{markDirty();rebuild().catch(error);};
for(const id of ['snap-floor','snap-grid'])$(id).onchange=()=>{markDirty();};
$('object-name').onchange=()=>{if(selected())recordChange(()=>selected().name=$('object-name').value.trim()||'Object');};
for(const [fields,key] of [[['x','y','z'],'position'],[['width','height','depth'],'dimensions']])fields.forEach((field,i)=>$('object-'+field).onchange=()=>{const o=selected(),v=Number($('object-'+field).value);if(!o)return;const valid=Number.isFinite(v)&&(key==='dimensions'?v>=.001&&v<=100:Math.abs(v)<=1000);if(!valid){select(selectedId);toast('Enter a valid size (.001–100 m) or position (±1000 m).',true);return;}recordChange(()=>{o[key][i]=v;constrain(o);});});
$('object-rotation').onchange=()=>{const o=selected(),n=Number($('object-rotation').value);if(o&&Number.isFinite(n)&&Math.abs(n)<=36000)recordChange(()=>{o.rotation=n;constrain(o);});else select(selectedId);};$('object-color').onchange=()=>{if(selected())recordChange(()=>selected().color=$('object-color').value);};
$('duplicate-btn').onclick=duplicate;$('delete-btn').onclick=remove;$('move-tool').onclick=()=>setTool('translate');$('rotate-tool').onclick=()=>setTool('rotate');$('scale-tool').onclick=()=>setTool('scale');$('undo-btn').onclick=()=>undo().catch(error);$('redo-btn').onclick=()=>redo().catch(error);
$('perspective-btn').onclick=()=>changeView(false);$('top-btn').onclick=()=>changeView(true);$('walk-btn').onclick=()=>setWalk(!walk);$('reset-camera').onclick=resetCamera;$('wireframe-btn').onclick=()=>{wireframe=!wireframe;$('wireframe-btn').classList.toggle('active',wireframe);$('wireframe-btn').setAttribute('aria-pressed',wireframe);rebuild().catch(error);};
$('warnings-btn').onclick=()=>$('warnings-content').hidden=!$('warnings-content').hidden;
for(const tab of ['library','scene'])$(tab+'-tab').onclick=()=>{for(const t of ['library','scene']){$(t+'-panel').hidden=t!==tab;$(t+'-tab').classList.toggle('active',t===tab);$(t+'-tab').setAttribute('aria-selected',String(t===tab));}};
$('furniture-search').oninput=renderLibrary;$('capabilities-btn').onclick=()=>showCapabilities().catch(error);
$('help-btn').onclick=()=>showInfo('Make yourself at home.',`<p>Upload a room photograph for a guided layout, or import a GLB from WorldBuilder. Guided mode uses your floor corners and dimensions. It does not automatically recover furniture.</p><ul><li>Click furniture to select it. Use G to move, R to rotate, S to scale. Drag the coloured handles or enter exact properties.</li><li>Delete removes a selected object. Ctrl+D duplicates. Ctrl+Z undoes; Ctrl+Y redoes.</li><li>Home resets the camera. Top view helps arrange furniture. Walk uses WASD and right mouse drag; Escape exits.</li><li>Walls automatically cut away in orbit view. The ceiling starts hidden. Visibility switches only affect inspection.</li><li>Save writes to this PC. Download a .stageai project to preserve the original photo, textures, meshes, camera, and edits.</li><li>Export GLB preserves separate objects and materials in metres. In Blender use File → Import → glTF 2.0.</li></ul><p class="muted small">Opening markers do not cut wall holes. Furniture-to-furniture collision and hidden-surface measurement are not implemented. See README.md for the complete limitations.</p>`);
$('import-glb-btn').onclick=()=>$('import-dialog').showModal();$('import-confirm').onclick=async()=>{const file=$('import-glb-file').files[0];if(!file){$('import-error').textContent='Choose a GLB file first.';return;}if(dirty&&!confirm('Import the scene and discard unsaved changes?'))return;$('import-confirm').disabled=true;$('import-error').textContent='Validating meshes and materials…';try{const f=new FormData();f.append('file',file);const r=await api('/api/import/glb?scale='+encodeURIComponent($('import-scale').value),{method:'POST',body:f});dirty=false;await loadProject(r.id);$('import-dialog').close();toast('Scene imported with individually editable meshes.');}catch(e){$('import-error').textContent=e.message;}finally{$('import-confirm').disabled=false;}};
document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)||document.querySelector('dialog[open]'))return;const k=e.key.toLowerCase();if(walk){keys.add(k);if(k==='escape'){setWalk(false);resetCamera();}return;}if((e.ctrlKey||e.metaKey)&&k==='s'){e.preventDefault();saveProject().catch(error);}else if((e.ctrlKey||e.metaKey)&&k==='z'){e.preventDefault();(e.shiftKey?redo():undo()).catch(error);}else if((e.ctrlKey||e.metaKey)&&k==='y'){e.preventDefault();redo().catch(error);}else if((e.ctrlKey||e.metaKey)&&k==='d'){e.preventDefault();duplicate();}else if(k==='delete'||k==='backspace'){e.preventDefault();remove();}else if(k==='g')setTool('translate');else if(k==='r')setTool('rotate');else if(k==='s')setTool('scale');else if(k==='home')resetCamera();else if(k==='escape')select(null);});document.addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));window.addEventListener('blur',()=>keys.clear());window.addEventListener('beforeunload',e=>{if(dirty||busy){e.preventDefault();e.returnValue='';}});
// Small diagnostic surface also used by the browser acceptance suite.
window.stageai={getState:()=>clone(state),getSelected:()=>selectedId,projectId:()=>projectId,select,addFurniture:kind=>addFurniture(catalog.find(i=>i.kind===kind)),ready:false,renderer,world,camera:()=>camera};
async function init(){
 const thumbRenderer=new THREE.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});thumbRenderer.setPixelRatio(1);thumbRenderer.outputColorSpace=THREE.SRGBColorSpace;thumbRenderer.toneMapping=THREE.ACESFilmicToneMapping;
 for(const item of catalog)item.preview=previewFurniture(thumbRenderer,item);thumbRenderer.dispose();renderLibrary();
 capabilities=await api('/api/capabilities');$('gpu-summary').textContent=capabilities.gpus[0]?`${(capabilities.gpus[0].total_mb/1024).toFixed(0)} GB GPU`:'CPU ready';updateMode();
 const saved=localStorage.getItem('stageai-project');if(saved){try{await loadProject(saved);}catch(e){localStorage.removeItem('stageai-project');await rebuild();resetCamera();toast('Previous project could not be loaded. Choose it from Projects.',true);}}else{await rebuild();resetCamera();}
 window.stageai.ready=true;
}
init().catch(e=>{error(e);$('loading').hidden=false;$('loading-label').textContent='The studio could not initialize';$('loading-detail').textContent=e.message;});
