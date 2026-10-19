'use strict';
const $=id=>document.getElementById(id);
let token='',role=null,facility=null,geo=null,state=null,viewer=null,useFallback=false,pin=null,pinMode='report',pendingDirection=null,dynamic=[],viewBounds=null,tilesEnabled=false;
const incidentEdges=new Map(),renderedLists={};
function listChanged(key,value){const signature=JSON.stringify(value);if(renderedLists[key]===signature)return false;renderedLists[key]=signature;return true;}
const say=text=>{$('notice').textContent=text;};
async function api(path,body){
  const response=await fetch('/api/live/'+path,{method:body?'POST':'GET',headers:{...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined});
  const data=await response.json();
  if(!response.ok){const e=new Error(data.error||'Request failed');e.detail=data.detail;throw e;}
  return data;
}
function pointInput(){return [Number($('longitude').value),Number($('latitude').value)];}
function setPin(point){pin=point;$('longitude').value=point[0].toFixed(7);$('latitude').value=point[1].toFixed(7);$('confirm').checked=false;draw();}
async function directed(action){
  try{await action();pendingDirection=null;$('direction-box').hidden=true;await refresh();}
  catch(e){if(e.message==='AMBIGUOUS_DIRECTION_SELECT_EDGE'){
    pendingDirection=action;const select=$('direction-choice');select.replaceChildren();
    for(const c of e.detail){const o=new Option(`${c.edge} · ${c.distance_m.toFixed(1)} m · along directed road`,c.edge);select.add(o);}
    $('direction-box').hidden=false;say('Direction is ambiguous. Confirm the intended directed road below.');
  }else say(e.message+(typeof e.detail==='string'?' — '+e.detail:''));}
}
async function place(point,edge){
  if(role!=='operator')return say('Sign in as an operator to place a test ambulance.');
  const row=await api('position',{source:'USER_SELECTED',coordinates:point,edge});say('USER_SELECTED test ambulance snapped '+row.position.distance_m.toFixed(1)+' m from pin.');
}
function selectPoint(point){setPin(point);if(pinMode==='ambulance')directed(edge=>place(point,edge));else say('Test incident pin selected. Confirm the coordinates before submitting.');}
function svgElement(tag,attrs){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));return e;}
function mercator(p){return [(p[0]+180)/360,(1-Math.asinh(Math.tan(p[1]*Math.PI/180))/Math.PI)/2];}
function projectionBounds(){const b=viewBounds||geo.bounds;return [mercator([b[0],b[3]]),mercator([b[2],b[1]])];}
function svgHeight(){const [a,b]=projectionBounds();return 1000*(b[1]-a[1])/(b[0]-a[0]);}
function xy(p){const [a,b]=projectionBounds(),m=mercator(p);return [(m[0]-a[0])/(b[0]-a[0])*1000,(m[1]-a[1])/(b[0]-a[0])*1000];}
function svgTiles(svg){
  if(!tilesEnabled)return;
  const [a,b]=projectionBounds(),z=(viewBounds||geo.bounds)[2]-(viewBounds||geo.bounds)[0]>.1?12:14,n=2**z;
  let count=0;
  for(let x=Math.floor(a[0]*n);x<=Math.floor(b[0]*n);x++)for(let y=Math.floor(a[1]*n);y<=Math.floor(b[1]*n);y++){
    if(++count>64)return;
    const width=1000/n/(b[0]-a[0]);
    const tile=svgElement('image',{x:(x/n-a[0])/(b[0]-a[0])*1000,y:(y/n-a[1])/(b[0]-a[0])*1000,width,height:width,href:`https://tile.openstreetmap.org/${z}/${x}/${y}.png`,preserveAspectRatio:'none'});
    tile.addEventListener('error',()=>say('Optional OSM imagery unavailable. Local pilot roads remain available.'));
    svg.append(tile);
  }
}
function svgLine(parent,points,attrs={}){parent.append(svgElement('polyline',{points:points.map(p=>xy(p).join(',')).join(' '),...attrs}));}
function marker(parent,p,label,kind){const [x,y]=xy(p);parent.append(svgElement('circle',{cx:x,cy:y,r:6,class:kind}));const text=svgElement('text',{x:x+9,y:y-8});text.textContent=label;parent.append(text);}
function fallback(){
  useFallback=true;$('map').hidden=true;$('fallback').removeAttribute('hidden');$('flat').textContent='2D fallback active';
  if(viewer){viewer.destroy();viewer=null;}draw();
}
// Small display offsets keep ellipsoid chords above the globe; not measured elevations.
function mapLine(points,height=2){return Cesium.Cartesian3.fromDegreesArrayHeights(points.flatMap(p=>[p[0],p[1],height]));}
function initializeMap(){
  if(new URLSearchParams(location.search).has('fallback')||!window.Cesium){say('Local 2D fallback selected or Cesium unavailable.');return fallback();}
  const probe=document.createElement('canvas');
  let context=null;try{context=probe.getContext('webgl2')||probe.getContext('webgl');}catch(e){}
  if(!context){say('3D unavailable: WebGL context initialization failed. Local 2D roads remain usable.');return fallback();}
  context.getExtension('WEBGL_lose_context')?.loseContext();
  try{
    Cesium.Ion.defaultAccessToken='';
    viewer=new Cesium.Viewer('map',{baseLayer:false,terrainProvider:new Cesium.EllipsoidTerrainProvider(),animation:false,timeline:false,baseLayerPicker:false,geocoder:false,homeButton:false,sceneModePicker:false,navigationHelpButton:false,fullscreenButton:false,selectionIndicator:false,infoBox:false,requestRenderMode:true});
    viewer.scene.globe.baseColor=Cesium.Color.fromCssColorString('#112333');
    for(const [id,road] of Object.entries(geo.roads))viewer.entities.add({id:'road-'+id,polyline:{positions:mapLine(road.coordinates),width:2,material:Cesium.Color.fromCssColorString('#365464')}});
    viewer.screenSpaceEventHandler.setInputAction(click=>{const ray=viewer.camera.getPickRay(click.position);const picked=ray&&viewer.scene.globe.pick(ray,viewer.scene);if(!picked)return;const p=Cesium.Cartographic.fromCartesian(picked);selectPoint([Cesium.Math.toDegrees(p.longitude),Cesium.Math.toDegrees(p.latitude)]);},Cesium.ScreenSpaceEventType.LEFT_CLICK);
    viewer.camera.setView({destination:Cesium.Rectangle.fromDegrees(...geo.bounds)});
    viewer.scene.renderError.addEventListener(()=>{say('3D unavailable; using local 2D road geometry.');fallback();});
  }catch(e){say('3D initialization unavailable: '+e.message+' · using local 2D roads.');fallback();}
}
function entityMarker(p,label,color){dynamic.push(viewer.entities.add({position:Cesium.Cartesian3.fromDegrees(...p),point:{pixelSize:10,color:Cesium.Color.fromCssColorString(color),outlineColor:Cesium.Color.BLACK,outlineWidth:2},label:{text:label,font:'11px sans-serif',pixelOffset:new Cesium.Cartesian2(0,-18),showBackground:true,distanceDisplayCondition:new Cesium.DistanceDisplayCondition(0,100000)}}));}
function draw(){
  if(!geo)return;
  const incidents=(state?.incidents||[]).filter(r=>!['REJECTED','RESOLVED'].includes(r.status)),hospitals=state?.hospitals||[],r=state?.recommendation,amb=state?.ambulance;
  const traffic=(state?.traffic?.observations||[]).filter(row=>row.observation_kind!=='INCIDENT'||row.incident_type==='ROAD_CLOSURE'&&row.eligible_for_routing);
  if(useFallback){
    if(!listChanged('svgMap',{viewBounds,tilesEnabled,pin,incidents,hospitals:hospitals.map(h=>[h.id,h.coordinates]),route:r&&!['UNAVAILABLE','CANCELLED'].includes(r.status)?r.geometry:null,amb,traffic:traffic.map(row=>[row.road_geometry,row.incident_type,row.eligible_for_routing,row.freshness_status])}))return;
    const svg=$('fallback');svg.setAttribute('viewBox','0 0 1000 '+svgHeight());svg.setAttribute('preserveAspectRatio','xMidYMid meet');svg.replaceChildren();svgTiles(svg);
    const pilot=[geo.bounds.slice(0,2),[geo.bounds[2],geo.bounds[1]],geo.bounds.slice(2),[geo.bounds[0],geo.bounds[3]],geo.bounds.slice(0,2)];
    svgLine(svg,pilot,{fill:'none',stroke:'#e7b668','stroke-width':2,'stroke-dasharray':'8 5'});
    for(const road of Object.values(geo.roads))svgLine(svg,road.coordinates,{class:'road'});
    for(const row of traffic){if(row.road_geometry?.length>1)svgLine(svg,row.road_geometry,{fill:'none',stroke:row.incident_type==='ROAD_CLOSURE'&&row.eligible_for_routing?'#ffcf70':'#b28bf0','stroke-width':4,'stroke-dasharray':row.freshness_status==='FRESH'?'':'6 4'});}
    if(r&&!['UNAVAILABLE','CANCELLED'].includes(r.status))for(const edge of r.geometry)svgLine(svg,edge.coordinates,{class:'route'});
    hospitals.forEach(h=>marker(svg,h.coordinates,h.name,'hospital'));incidents.forEach(i=>marker(svg,i.coordinates,'TEST '+i.status,'incident'));
    if(amb)marker(svg,amb.position.coordinates,'USER_SELECTED','ambulance');if(pin)marker(svg,pin,'Selected pin','incident');
  }else if(viewer){
    dynamic.forEach(e=>viewer.entities.remove(e));dynamic=[];
    if(r&&!['UNAVAILABLE','CANCELLED'].includes(r.status))for(const edge of r.geometry)dynamic.push(viewer.entities.add({polyline:{positions:mapLine(edge.coordinates,4),width:6,material:Cesium.Color.fromCssColorString('#39e4cd')}}));
    for(const row of traffic)if(row.road_geometry?.length>1)dynamic.push(viewer.entities.add({polyline:{positions:mapLine(row.road_geometry,8),width:5,material:Cesium.Color.fromCssColorString(row.incident_type==='ROAD_CLOSURE'&&row.eligible_for_routing?'#ffcf70':'#b28bf0')}}));
    hospitals.forEach(h=>entityMarker(h.coordinates,h.name,'#79dfad'));incidents.forEach(i=>entityMarker(i.coordinates,'TEST INCIDENT','#ff8a7b'));
    if(amb)entityMarker(amb.position.coordinates,'USER_SELECTED','#ffd570');if(pin)entityMarker(pin,'Selected pin','#ff8a7b');viewer.scene.requestRender();
  }
}
function item(parent,title,lines){const div=document.createElement('div');div.className='item';const b=document.createElement('b');b.textContent=title;div.append(b);for(const line of lines){const p=document.createElement('p');p.textContent=line;div.append(p);}parent.append(div);return div;}
function render(){
  const s=state; $('role').textContent=role?role.toUpperCase()+(facility?' · '+facility:''):'PUBLIC · no operator permissions';
  $('operator-panel').hidden=role!=='operator';$('hospital-form').hidden=role!=='hospital';$('traffic-test-panel').hidden=role!=='operator'||!s.traffic.offline_test_enabled;
  $('facility').textContent=facility||'';
  $('traffic-source').textContent=s.traffic.source;
  $('traffic-status').textContent='No actual traffic-provider connection. '+s.provider_access+' · active test closures: '+(s.traffic.active_closures?.length||0);
  $('coverage').textContent='Routing bounds: '+geo.bounds.join(', ')+' · display does not imply routing coverage.';
  if(listChanged('traffic',s.traffic)){
  $('traffic-rows').replaceChildren();
  for(const row of s.traffic.observations||[])item($('traffic-rows'),`${row.provider_segment_id} · ${row.source_type}`,[`${row.freshness_status} · ${row.matching_status} · ${row.incident_type||'FLOW'}`,`Source time: ${row.observation_timestamp||'UNKNOWN'} · retrieved: ${row.retrieved_at}`]);
  if(s.traffic.quarantine_count)item($('traffic-rows'),'UNKNOWN · FUTURE CLOCK QUARANTINED',[String(s.traffic.quarantine_count)+' invalid record(s); last valid current observation preserved.']);
  }
  if(listChanged('hospitals',s.hospitals)){
  $('hospitals').replaceChildren();for(const h of s.hospitals){const div=item($('hospitals'),h.name,[`${h.availability} · ${h.freshness}`,h.status?`Accepting: ${h.status.accepting??'UNKNOWN'} · ICU: ${h.status.icu??'UNKNOWN'} · beds: ${h.status.beds??'UNKNOWN'}`:'Capacity and services UNKNOWN',h.road_access]);const a=document.createElement('a');a.href=h.source;a.target='_blank';a.rel='noreferrer';a.textContent='OSM source · not field verified';div.append(a);}
  }
  if(listChanged('incidents',s.incidents)){
  $('queue').replaceChildren();const prior=$('incident-choice').value;$('incident-choice').replaceChildren();
  for(const i of s.incidents){const div=item($('queue'),i.type+' · '+i.status,[i.description,`PUBLIC_TEST_REPORT · ${i.created_at}`]);if(i.status==='PENDING_VERIFICATION')for(const [label,status] of [['Verify for testing','VERIFIED_FOR_TESTING'],['Reject','REJECTED']]){const b=document.createElement('button');b.textContent=label;b.onclick=()=>act(()=>api('verify',{id:i.id,status}));div.append(b);}if(i.status==='VERIFIED_FOR_TESTING')$('incident-choice').add(new Option(i.id+' · '+i.type,i.id));const del=document.createElement('button');del.textContent='Delete report';del.onclick=()=>act(()=>api('delete',{id:i.id}));div.append(del);}
  if([...$('incident-choice').options].some(o=>o.value===prior))$('incident-choice').value=prior;
  }
  $('position').textContent=s.ambulance?`USER_SELECTED · ${s.ambulance.position.edge} · snap ${s.ambulance.position.distance_m.toFixed(1)} m · ${s.ambulance.position.confidence}`:'USER_SELECTED position required.';
  $('recommendation').replaceChildren();const r=s.recommendation;
  if(r){item($('recommendation'),r.status,[r.reason,`${(r.eta_seconds/60).toFixed(1)} min · ${r.eta_label}`,`${r.estimated_edges} estimated edges / ${r.observed_edges} offline-observed edges`,r.assumptions||'',r.execution||'']);}
  $('history').textContent=JSON.stringify({history:s.history,agents:r?.agents},null,2);
  for(const b of document.querySelectorAll('[data-state]'))b.disabled=!r||!({PENDING_OPERATOR_REVIEW:['APPROVED','CANCELLED'],APPROVED:['ACKNOWLEDGED','CANCELLED'],ACKNOWLEDGED:['ARRIVAL_REPORTED','CANCELLED']}[r.status]||[]).includes(b.dataset.state);
  if(listChanged('testEdges',r?.route||[])){
  const previous=$('test-edge').value;$('test-edge').replaceChildren();for(const eid of r?.route||[])$('test-edge').add(new Option(eid,eid));if([...$('test-edge').options].some(o=>o.value===previous))$('test-edge').value=previous;
  }
  draw();
}
async function refresh(){const requestToken=token;try{const next=await api('state');if(requestToken!==token)return;state=next;render();}catch(e){if(requestToken===token)say(e.message);}}
function clearPrivateState(){role=null;facility=null;pendingDirection=null;incidentEdges.clear();$('direction-box').hidden=true;if(state){state={...state,incidents:[],ambulance:null,recommendation:null,history:[]};render();}}
async function act(action){try{await action();await refresh();}catch(e){say(e.message);}}
$('report-form').onsubmit=e=>{e.preventDefault();act(async()=>{const r=await api('incidents',{test:true,confirmed:$('confirm').checked,coordinates:pointInput(),type:$('incident-type').value,description:$('description').value});say('TEST report '+r.id+' submitted: '+r.status+'. No emergency service contacted.');$('confirm').checked=false;$('description').value='';});};
$('login-form').onsubmit=e=>{e.preventDefault();act(async()=>{const nextToken=$('token').value;$('token').value='';token='';clearPrivateState();token=nextToken;try{const s=await api('session');role=s.role;facility=s.facility;say('Authenticated '+role+'.');}catch(err){token='';clearPrivateState();throw err;}});};
$('logout').onclick=()=>{token='';clearPrivateState();refresh();say('Signed out. Token cleared from tab memory.');};
$('report-pin').onclick=()=>{pinMode='report';say('Click the map to select a test incident location.');$('report').scrollIntoView({block:'nearest'});};
$('ambulance-pin').onclick=()=>{pinMode='ambulance';say('Click a pilot road for the USER_SELECTED test ambulance. Operator sign-in required.');};
$('position-from-pin').onclick=()=>directed(edge=>place(pointInput(),edge));
$('direction-confirm').onclick=()=>{if(pendingDirection){const action=pendingDirection,edge=$('direction-choice').value;directed(()=>action(edge));}};
$('recommend').onclick=()=>{const id=$('incident-choice').value;directed(async edge=>{if(edge)incidentEdges.set(id,edge);const r=await api('recommend',{leg:$('leg').value,incident_id:id,incident_edge:incidentEdges.get(id),incident_arrival_confirmed:$('at-incident').checked,require_icu:$('require-icu').checked,require_trauma:$('require-trauma').checked});say(r.status+' · '+r.eta_label);});};
for(const b of document.querySelectorAll('[data-state]'))b.onclick=()=>act(()=>api('transition',{status:b.dataset.state,recommendation_id:state?.recommendation?.id}));
$('location').onclick=()=>{if(!navigator.geolocation)return say('Geolocation unavailable. Place a pin manually.');navigator.geolocation.getCurrentPosition(p=>{pinMode='report';setPin([p.coords.longitude,p.coords.latitude]);say('Device location selected once, accuracy ±'+Math.round(p.coords.accuracy)+' m. Not submitted until you confirm.');},()=>say('Location unavailable or denied. Place a pin manually.'),{enableHighAccuracy:true,timeout:10000,maximumAge:0});};
$('hospital-form').onsubmit=e=>{e.preventDefault();act(async()=>{const value=id=>$(id).value===''?null:$(id).value==='true';await api('hospital',{hospital_id:facility,accepting:value('accepting'),trauma:value('trauma'),icu:value('icu'),beds:$('beds').value===''?null:Number($('beds').value),notes:$('hospital-notes').value});say('Saved STAFF_REPORTED availability; expires after 15 minutes.');});};
$('traffic-test').onclick=()=>act(async()=>{await api('traffic-test',{edge:$('test-edge').value,condition:$('test-condition').value});say('Applied SYNTHETIC_TEST condition. No provider request.');});
$('fallback').onclick=e=>{
  const svg=e.currentTarget,p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;
  const local=p.matrixTransform(svg.getScreenCTM().inverse()),[a,b]=projectionBounds();
  if(local.x<0||local.x>1000||local.y<0||local.y>svgHeight())return;
  const x=a[0]+local.x/1000*(b[0]-a[0]),y=a[1]+local.y/1000*(b[0]-a[0]);
  selectPoint([x*360-180,Math.atan(Math.sinh(Math.PI*(1-2*y)))*180/Math.PI]);
};
$('flat').onclick=fallback;
$('pilot').onclick=()=>{if(viewer)viewer.camera.flyTo({destination:Cesium.Rectangle.fromDegrees(...geo.bounds),duration:1});else{viewBounds=[...geo.bounds];draw();say('Bounded routing pilot view. Outside the dashed boundary is display only.');}};
$('city').onclick=()=>{if(viewer)viewer.camera.flyTo({destination:Cesium.Rectangle.fromDegrees(80.02,12.75,80.35,13.25),duration:1});else{viewBounds=[80.02,12.75,80.35,13.25];draw();say('Chennai-wide DISPLAY ONLY. Enable optional OSM basemap for city roads. Only the dashed pilot is routable.');}};
$('tiles').onclick=()=>{
  tilesEnabled=!tilesEnabled;
  if(viewer){if(!tilesEnabled)viewer.imageryLayers.removeAll();else viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',maximumLevel:19,credit:'© OpenStreetMap contributors'}));}
  draw();say(tilesEnabled?'Optional OSM tiles enabled. Basemap roads outside the pilot are not routable.':'Online basemap disabled; local pilot geometry remains.');
};
(async()=>{try{geo=await api('geography');initializeMap();await refresh();setInterval(refresh,5000);}catch(e){say('Map unavailable: '+e.message);}})();
