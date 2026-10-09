import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
const $=id=>document.getElementById(id);
let renderer,scene,camera,controls,latest,geometryKey='',follow=false,playing=false,busy=false,previousTime=null;
const vehicles=new Map(),lights=new Map();let city=new THREE.Group(),routeGroup=new THREE.Group();
const material=(color,extra={})=>new THREE.MeshStandardMaterial({color,roughness:.8,...extra});
const materials={road:material(0x27343c),curb:material(0x62777d),white:material(0xf5f3e8),glass:material(0x173d53),red:material(0xed4850),car:material(0x5597cf),green:material(0x31cfa0,{emissive:0x176c50}),dark:material(0x172830)};
function box(w,h,d,mat,x=0,y=0,z=0){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;return m;}
function label(text,color='#b9eadf'){const c=document.createElement('canvas');c.width=512;c.height=96;const x=c.getContext('2d');x.fillStyle='#0e2430';x.fillRect(0,0,512,96);x.font='bold 34px sans-serif';x.textAlign='center';x.fillStyle=color;x.fillText(text,256,60);const texture=new THREE.CanvasTexture(c);const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}));sprite.scale.set(36,7,1);return sprite;}
function strip(a,b,width,mat,height=.08,parent=city){const dx=b[0]-a[0],dz=-(b[1]-a[1]),len=Math.hypot(dx,dz);if(!len)return;const m=box(width,.12,len,mat,(a[0]+b[0])/2,height,-(a[1]+b[1])/2);m.rotation.y=Math.atan2(dx,dz);parent.add(m);}
function segments(shape,mat,width,parent=city,height=.12){const p=shape.split(' ').map(s=>s.split(',').map(Number));for(let i=1;i<p.length;i++)strip(p[i-1],p[i],width,mat,height,parent);}
function dispose(group){group.traverse(o=>{o.geometry?.dispose();if(o.isSprite){o.material.map?.dispose();o.material.dispose();}});group.clear();}
function build(config,d){dispose(city);lights.clear();const [x0,y0,x1,y1]=config.bounds;
 city.add(box(x1-x0+110,1,y1-y0+110,material(0x25463e),(x0+x1)/2,-.7,-(y0+y1)/2));
 for(const signal of d.signals){const crossing=new THREE.Mesh(new THREE.CylinderGeometry(7.5,7.5,.14,24),materials.road);crossing.position.set(signal.position[0],.06,-signal.position[1]);crossing.receiveShadow=true;city.add(crossing);}
 for(const road of config.roads){segments(road,materials.curb,5,city,0);segments(road,materials.road,3.4);}
 // Buildings occupy open blocks only; their appearance does not claim real GIS data.
 for(let x=x0+30;x<x1;x+=100)for(let y=y0+28;y<y1;y+=100){
  for(let k=0;k<3;k++){const h=10+((x+y+k*11)%23),bx=x+k*17,by=y+(k%2)*23;const b=box(13,h,16,material([0x778a92,0x617984,0x93a5a9][k]),bx,h/2,-by);city.add(b);city.add(box(14,.8,17,materials.dark,bx,h+.4,-by));
   for(let level=4;level<h;level+=5)city.add(box(13.2,1,16.2,materials.glass,bx,level,-by));}
 }
 for(let x=x0+72;x<x1;x+=100)for(let y=y0+64;y<y1;y+=100){for(let k=0;k<3;k++){city.add(box(.7,4,.7,material(0x715944),x+k*6,2,-y));const tree=new THREE.Mesh(new THREE.SphereGeometry(3.5,8,6),material(0x388064));tree.position.set(x+k*6,6,-y);tree.castShadow=true;city.add(tree);}}
 const [hx,hy]=d.hospital_position;
 const hospital=new THREE.Group();hospital.position.set(hx+23,0,-hy-21);hospital.add(box(28,21,24,materials.white,0,10.5));hospital.add(box(29,1,25,materials.green,0,21));hospital.add(box(22,3,24.2,materials.glass,0,13));hospital.add(box(4,10,.5,materials.red,0,13,12.4));hospital.add(box(10,4,.5,materials.red,0,13,12.5));city.add(hospital);
 const hlabel=label('✚ H1 · SIMULATED');hlabel.position.set(hx+23,32,-hy-21);city.add(hlabel);
 const marker=new THREE.Mesh(new THREE.CylinderGeometry(8,8,.3,32),material(0x31cfa0,{transparent:true,opacity:.5}));marker.position.set(hx,.4,-hy);city.add(marker);
 for(const s of d.signals){const g=new THREE.Group();g.position.set(s.position[0]+5,0,-s.position[1]+5);g.add(box(.7,8,.7,materials.dark,0,4));g.add(box(7,3,1,materials.dark,0,9));const bulbs=[];
  [...s.state].forEach((_,i)=>{const bulb=new THREE.Mesh(new THREE.SphereGeometry(.45,8,8),new THREE.MeshBasicMaterial());bulb.position.set((i-(s.state.length-1)/2)*.65,9,1);g.add(bulb);bulbs.push(bulb);});city.add(g);lights.set(s.id,bulbs);
  const name=label(s.id);name.scale.set(9,2,1);name.position.set(s.position[0],13,-s.position[1]);city.add(name);
 }
 overview(config);
}
function car(ambulance,blocker=false){const g=new THREE.Group();g.add(box(ambulance?2.7:2,ambulance?2:1.1,ambulance?6:4.6,ambulance?materials.white:blocker?materials.red:materials.car,0,ambulance?1.4:.9));g.add(box(1.8,.8,2,materials.glass,0,ambulance?2:1.7,-.7));
 for(const x of [-1.1,1.1])for(const z of [-1.5,1.5]){const wheel=new THREE.Mesh(new THREE.CylinderGeometry(.5,.5,.35,12),materials.dark);wheel.rotation.z=Math.PI/2;wheel.position.set(x,.55,z);g.add(wheel);}
 if(ambulance){g.add(box(2.8,.4,5.8,materials.red,0,1.1));g.add(box(2,.35,.6,materials.red,0,2.65));g.add(box(.1,.3,1.4,materials.red,1.4,1.9,1));g.add(box(.1,.9,.4,materials.red,1.41,1.9,1));const badge=label('AMBULANCE','#ffb0b4');badge.position.y=8;badge.scale.set(24,4.5,1);g.add(badge);}
 if(blocker){const badge=label('INCIDENT VEHICLE','#ffcf9f');badge.position.y=7;badge.scale.set(22,4,1);g.add(badge);}
 return g;
}
function overview(config){if(!config)return;follow=false;$('follow').classList.remove('active');const [x0,y0,x1,y1]=config.bounds,cx=(x0+x1)/2,cy=-(y0+y1)/2;controls.target.set(cx,0,cy);camera.position.set(cx+310,340,cy+350);controls.update();}
function show(s){latest=s;const d=s.demo,c=s.demo_config;$('source').textContent=s.mode.startsWith('REPLAY')?'REPLAY · SUMO evidence':s.terminal?'COMPLETED · SUMO run':'LIVE · SUMO observations';$('time').textContent=`${s.time??'—'} s`;
 $('notice').textContent=s.read_error||(!c?'This recording has no demo vehicle/signal observations. Launch citybrain.demo.':!d?'Waiting for the first observation.':(!s.terminal&&s.source_age_seconds>5&&!s.mode.startsWith('REPLAY')?'Observations paused or stale. Vehicles remain at their last observed positions.':''));if(!c||!d)return;
 const key=JSON.stringify([c.bounds,c.roads]);if(key!==geometryKey){geometryKey=key;build(c,d);}
 $('revision').textContent=s.plan?`P${s.plan.revision}`:'Awaiting dispatch';const ambulance=d.vehicles.find(v=>v.type==='ambulance');$('speed').textContent=ambulance?`${ambulance.speed.toFixed(1)} m/s`:s.terminal?'Arrived / absent':'Not yet present';$('count').textContent=d.vehicles.length;$('outcome').textContent=s.terminal?.outcome||'Observing';$('decision').textContent=s.decision?.reason||'Waiting for dispatch';
 $('plans').replaceChildren(...s.plans.map(p=>{const li=document.createElement('li');li.textContent=`P${p.plan.revision} accepted · ${p.time} s`;return li;}));
 $('replayControls').hidden=!s.mode.startsWith('REPLAY');$('seek').max=s.max_time;
 for(const signal of d.signals){(lights.get(signal.id)||[]).forEach((b,i)=>b.material.color.set({r:0xff4242,y:0xffcc32,g:0x36f69f,o:0x555555}[signal.state[i]?.toLowerCase()]??0x555555));}
 if(previousTime!==d.observed_time){const ids=new Set(d.vehicles.map(v=>v.id));for(const [id,item]of vehicles)if(!ids.has(id)){scene.remove(item.mesh);dispose(item.mesh);vehicles.delete(id);}
  for(const v of d.vehicles){let item=vehicles.get(v.id);const target=new THREE.Vector3(v.position[0],0,-v.position[1]);if(!item){const mesh=car(v.type==='ambulance',v.type==='accidentVehicle');scene.add(mesh);mesh.position.copy(target);item={mesh};vehicles.set(v.id,item);}
   item.from=item.mesh.position.clone();item.to=target;item.start=performance.now();item.duration=d.observed_time-previousTime===1?Math.max(500,(s.mode.startsWith('REPLAY')?1.8:c.seconds_per_step)*1000):0;
   // Heading is actual SUMO angle when recorded; old evidence uses displacement only.
   if(Number.isFinite(v.angle))item.mesh.rotation.y=-v.angle*Math.PI/180;
   else if(item.from.distanceTo(target)>.01)item.mesh.rotation.y=Math.atan2(-(target.x-item.from.x),-(target.z-item.from.z));
   item.ambulance=v.type==='ambulance';
  }previousTime=d.observed_time;
 }
 dispose(routeGroup);if(c.road_edges&&s.plan)for(const edge of s.plan.route)for(const shape of c.road_edges[edge]||[])segments(shape,materials.green,1,routeGroup,.3);
}
function cameraMode(mode){document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.id===mode));if(mode==='overview')overview(latest?.demo_config);if(mode==='follow')follow=true;if(mode==='hospital'&&latest?.demo){follow=false;const [x,y]=latest.demo.hospital_position;controls.target.set(x+15,8,-y-10);camera.position.set(x+100,90,-y+100);controls.update();}if(mode==='top'&&latest?.demo_config){follow=false;const [x0,y0,x1,y1]=latest.demo_config.bounds;controls.target.set((x0+x1)/2,0,-(y0+y1)/2);camera.position.set((x0+x1)/2,480,-(y0+y1)/2+.1);controls.update();}}
async function poll(){if(busy)return;busy=true;try{const response=await fetch(`/api/state?at=${$('seek').value}`,{cache:'no-store'});if(!response.ok)throw Error(`HTTP ${response.status}`);show(await response.json());}catch(e){$('notice').textContent=`Viewer unavailable: ${e.message}. Simulation runs independently.`;}finally{busy=false;}}
try{
 renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(innerWidth,innerHeight);renderer.setClearColor(0x10232e);renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;$('world').append(renderer.domElement);
 scene=new THREE.Scene();scene.fog=new THREE.Fog(0x10232e,650,1400);camera=new THREE.PerspectiveCamera(43,innerWidth/innerHeight,.1,1800);controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.maxPolarAngle=Math.PI/2-.03;controls.minDistance=25;controls.maxDistance=1000;
 scene.add(city,routeGroup,new THREE.HemisphereLight(0xe6f5ff,0x365947,2.7));const sun=new THREE.DirectionalLight(0xfff0d3,3);sun.position.set(100,350,200);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-450,right:450,top:450,bottom:-450,far:900});scene.add(sun);
 $('details').addEventListener('click',()=>{const panel=document.querySelector('aside');panel.hidden=!panel.hidden;$('details').textContent=panel.hidden?'Show details':'Hide details';});
 for(const id of ['overview','follow','top','hospital'])$(id).addEventListener('click',()=>cameraMode(id));$('seek').addEventListener('input',()=>{playing=false;$('play').textContent='Play replay';poll();});$('play').addEventListener('click',()=>{playing=!playing;$('play').textContent=playing?'Pause replay':'Play replay';});
 addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
 renderer.setAnimationLoop(()=>{const now=performance.now();for(const item of vehicles.values()){const t=item.duration?Math.min(1,(now-item.start)/item.duration):1;item.mesh.position.lerpVectors(item.from,item.to,t);}
 if(follow){const item=[...vehicles.values()].find(v=>v.ambulance);if(item){controls.target.lerp(item.mesh.position,.08);const target=item.mesh.position.clone().add(new THREE.Vector3(45,55,65));camera.position.lerp(target,.035);}}
 controls.update();renderer.render(scene,camera);});
 setInterval(poll,500);setInterval(()=>{if(playing){$('seek').value=Math.min(Number($('seek').max),Number($('seek').value)+1);if($('seek').value===$('seek').max){playing=false;$('play').textContent='Play replay';}poll();}},1800);poll();
}catch(e){$('notice').textContent=`3D unavailable (${e.message}). The 2D dashboard remains available.`;}
