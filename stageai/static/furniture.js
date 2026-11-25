import * as THREE from 'three';

export const catalog = [
 {kind:'sofa',name:'Sofa',dims:[2.3,.86,.94],color:'#8fae9c',category:'Seating'},
 {kind:'chair',name:'Lounge chair',dims:[.75,.92,.78],color:'#c2aa89',category:'Seating'},
 {kind:'table',name:'Coffee table',dims:[1.2,.43,.65],color:'#ae8862',category:'Tables'},
 {kind:'bed',name:'Double bed',dims:[1.65,.85,2.15],color:'#aebeb0',category:'Bedroom'},
 {kind:'desk',name:'Writing desk',dims:[1.4,.75,.68],color:'#b39472',category:'Workspace'},
 {kind:'wardrobe',name:'Wardrobe',dims:[1.6,2.1,.6],color:'#9eaa96',category:'Storage'},
 {kind:'cabinet',name:'Sideboard',dims:[1.5,.82,.45],color:'#b28b62',category:'Storage'},
 {kind:'shelf',name:'Bookshelf',dims:[.9,1.8,.35],color:'#b19a77',category:'Storage'},
 {kind:'lamp',name:'Floor lamp',dims:[.45,1.65,.45],color:'#e2cfaa',category:'Lighting'},
 {kind:'rug',name:'Area rug',dims:[2.4,.02,1.7],color:'#8f9e92',category:'Textiles'},
 {kind:'plant',name:'Potted plant',dims:[.6,1.15,.6],color:'#6e9272',category:'Decor'},
 {kind:'decor',name:'Ceramic vase',dims:[.24,.42,.24],color:'#d2b89b',category:'Decor'},
 {kind:'door',name:'Door marker',dims:[.9,2.1,.07],color:'#a58e70',category:'Openings'},
 {kind:'window',name:'Window marker',dims:[1.3,1.1,.08],color:'#b6cbd0',category:'Openings'},
];

// All models share a bottom-centre origin. Dimensions are authoritative metres.
// Unit geometry is normalized once, so edits do not depend on regenerated AI.
export function createFurniture(kind,color) {
 const root=new THREE.Group();
 const main=new THREE.MeshStandardMaterial({color,roughness:.82});
 const wood=new THREE.MeshStandardMaterial({color:'#7b624c',roughness:.8});
 const dark=new THREE.MeshStandardMaterial({color:'#39463d',roughness:.7});
 const pale=new THREE.MeshStandardMaterial({color:'#e8e5d9',roughness:.95});
 function box(x,y,z,w,h,d,mat=main){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;root.add(m);return m;}
 function cyl(x,y,z,r,h,mat=main,rt=r){const m=new THREE.Mesh(new THREE.CylinderGeometry(rt,r,h,24),mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;root.add(m);return m;}
 function legs(y,h,w=.07){for(const x of [-.39,.39])for(const z of [-.36,.36])box(x,y,z,w,h,w,wood);}
 if(kind==='sofa'){
  box(0,.22,0,.95,.25,.86);box(0,.7,-.36,.94,.6,.16);box(-.44,.48,0,.12,.5,.9);box(.44,.48,0,.12,.5,.9);
  for(let x of [-.25,0,.25]){box(x,.4,.02,.24,.17,.64);box(x,.69,-.24,.23,.44,.1);}
  legs(.07,.14,.045);
 }else if(kind==='chair'){
  box(0,.45,.03,.87,.17,.85);box(0,.78,-.35,.88,.44,.14);box(-.44,.56,0,.1,.27,.82);box(.44,.56,0,.1,.27,.82);legs(.2,.4,.06);
 }else if(kind==='table'||kind==='desk'){
  box(0,.92,0,1,.12,1);legs(.44,.88,.06);if(kind==='desk')box(.29,.74,0,.35,.23,.86);
 }else if(kind==='bed'){
  legs(.08,.16,.08);box(0,.24,.03,1,.27,.91,wood);box(0,.48,.03,.96,.23,.9,pale);box(0,.42,-.46,1,.85,.08);box(0,.63,.16,.97,.04,.6);
  for(let x of [-.24,.24])box(x,.64,-.28,.4,.1,.22,pale);
 }else if(kind==='wardrobe'||kind==='cabinet'){
  legs(.04,.08,.045);box(0,.54,0,1,.91,1);for(let x of [-.25,.25])box(x,.54,.508,.485,.86,.015);for(let x of [-.035,.035])box(x,.54,.53,.018,.12,.02,dark);
 }else if(kind==='shelf'){
  box(-.47,.5,0,.06,1,1);box(.47,.5,0,.06,1,1);box(0,.5,-.47,.92,1,.06);
  for(let y of [.03,.27,.51,.75,.97])box(0,y,0,.94,.045,1);
  for(let i=0;i<4;i++){const m=new THREE.MeshStandardMaterial({color:['#8c9b7d','#b5a281','#566b5e','#b5b8a5'][i]});box(-.3+i*.13,.39,.04,.09,.18,.55,m);}
 }else if(kind==='lamp'){
  cyl(0,.025,0,.35,.05,dark);cyl(0,.5,0,.025,.93,dark);cyl(0,.88,0,.5,.24,main,.3);
 }else if(kind==='rug'){
  box(0,.5,0,1,1,1);const stripe=new THREE.MeshStandardMaterial({color:'#c4c8b6',roughness:1});for(let x of [-.44,.44])box(x,1.01,0,.018,.01,.94,stripe);
 }else if(kind==='plant'){
  cyl(0,.16,0,.27,.32,new THREE.MeshStandardMaterial({color:'#baa78b'}),.34);cyl(0,.56,0,.025,.68,wood);
  for(let i=0;i<9;i++){const a=i*2.4;const geo=new THREE.SphereGeometry(.17,12,8);geo.scale(.6,1.5,.28);const leaf=new THREE.Mesh(geo,main);leaf.position.set(Math.cos(a)*.21,.4+i*.064,Math.sin(a)*.21);leaf.rotation.set(.3,a,.7);leaf.castShadow=true;root.add(leaf);}
 }else if(kind==='decor'){
  cyl(0,.26,0,.42,.52,main,.32);cyl(0,.66,0,.18,.3);cyl(0,.85,0,.2,.1);
 }else if(kind==='door'){
  box(0,.5,0,1,1,1);cyl(.35,.48,.6,.025,.03,dark).rotation.x=Math.PI/2;
 }else if(kind==='window'){
  box(0,.5,0,1,1,.5,new THREE.MeshStandardMaterial({color:'#9cbaca',transparent:true,opacity:.5,roughness:.2}));
  for(const x of [-.47,0,.47])box(x,.5,.1,.04,1,1,pale);for(const y of [.02,.5,.98])box(0,y,.1,1,.04,1,pale);
 }else box(0,.5,0,1,1,1);
 const bounds=new THREE.Box3().setFromObject(root),size=bounds.getSize(new THREE.Vector3());
 const origin=new THREE.Vector3((bounds.min.x+bounds.max.x)/2,bounds.min.y,(bounds.min.z+bounds.max.z)/2);
 for(const child of root.children)child.position.sub(origin);
 root.scale.set(1/size.x,1/size.y,1/size.z);
 root.userData.procedural=true;
 return root;
}

export function previewFurniture(renderer,item){
 const scene=new THREE.Scene();scene.add(new THREE.AmbientLight(0xffffff,2));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,5,2);scene.add(light);
 const model=createFurniture(item.kind,item.color);model.scale.multiply(new THREE.Vector3(...item.dims));scene.add(model);
 const size=Math.max(...item.dims),cam=new THREE.PerspectiveCamera(35,1.4,.01,100);
 cam.position.set(size*1.45,size*1.15,size*1.65);cam.lookAt(0,item.dims[1]*.45,0);
 renderer.setSize(196,140);renderer.setClearColor(0x000000,0);renderer.render(scene,cam);
 const data=renderer.domElement.toDataURL('image/png');
 scene.traverse(n=>{n.geometry?.dispose();if(n.material){const mats=Array.isArray(n.material)?n.material:[n.material];mats.forEach(m=>m.dispose());}});
 return data;
}
