'use strict';
const $ = id => document.getElementById(id);
const show = (id, value) => { $(id).textContent = value ?? 'UNAVAILABLE'; };
const pretty = value => JSON.stringify(value ?? 'UNAVAILABLE', null, 2);
const num = (value, places = 1) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(places) : '—';
let viewer, geo, latest, replayAt = 0, playing = false, replay = false, busy = false, viewerFailure = '';
let follow = false, fallbackMode = false, imageryOn = false, lastWall = performance.now();
const vehicles = new Map(), roads = new Map(), signals = new Map();
let routeEntity, previousRoute = '', homePosition;
const C = window.Cesium;
let selectedTrafficRoad = '';
const externalEntities = new Map();

function notice(text) { show('notice', text); }
function home() {
  follow = false;
  $('follow').classList.remove('active');
  if (viewer) {
    viewer.camera.lookAt(C.Cartesian3.fromDegrees(80.153,12.843,0),
      new C.HeadingPitchRange(0,C.Math.toRadians(-70),6500));
    viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
    viewer.scene.requestRender();
  }
}
function position(lon,lat,height=2) { return C.Cartesian3.fromDegrees(lon,lat,height); }
function line(points, height=1) { return C.Cartesian3.fromDegreesArrayHeights(points.flatMap(p=>[p[0],p[1],height])); }
function safeDescription(text) { return String(text).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }

function initializeCesium() {
  if (!C) throw new Error('Local Cesium bundle unavailable');
  C.Ion.defaultAccessToken = '';
  viewer = new C.Viewer('map', {baseLayer:false,baseLayerPicker:false,geocoder:false,
    terrainProvider:new C.EllipsoidTerrainProvider(),animation:false,timeline:false,
    homeButton:false,navigationHelpButton:false,sceneModePicker:false,fullscreenButton:false,
    selectionIndicator:false,infoBox:false,requestRenderMode:true,maximumRenderTimeChange:Infinity});
  viewer.scene.globe.baseColor = C.Color.fromCssColorString('#172638');
  viewer.scene.backgroundColor = C.Color.fromCssColorString('#0b111a');
  viewer.scene.globe.enableLighting = false;
  viewer.targetFrameRate = 30;
  viewer.selectedEntityChanged.addEventListener(entity=>{
    if(entity?.id?.startsWith('road:')) {selectedTrafficRoad=entity.id.slice(5);if(latest)renderTrafficPanel(latest);}
    if(entity)notice(entity.name+' · '+(entity.description?.getValue(viewer.clock.currentTime) || 'OSM geometry'));
  });
  viewer.scene.renderError.addEventListener((_scene,error)=>{
    viewerFailure=error.message;
    notice('3D rendering failed: '+error.message);
    activateFallback(true);
  });
  viewer.cesiumWidget.creditDisplay.addStaticCredit(new C.Credit('© OpenStreetMap contributors · ODbL 1.0',true));
  for (const [id,road] of Object.entries(geo.roads)) {
    roads.set(id,viewer.entities.add({id:'road:'+id,name:road.name || id,
      description:safeDescription('OSM / SUMO edge '+id+' · '+road.classification),
      polyline:{positions:line(road.coordinates),width:road.classification.includes('primary')?4:2,
        material:C.Color.fromCssColorString('#405269')}}));
  }
  for (const building of geo.buildings) {
    viewer.entities.add({id:'building:'+building.id,name:building.name || 'OSM building',
      description:safeDescription(building.height_source+' · '+building.height+' m'),
      polygon:{hierarchy:C.Cartesian3.fromDegreesArray(building.coordinates.flat()),height:0,
        extrudedHeight:building.height,material:C.Color.fromCssColorString('#47586d').withAlpha(0.65),
        outline:false}});
  }
  viewer.entities.add({id:'vit',position:position(80.154,12.8408,60),
    label:{text:'VIT CHENNAI',font:'bold 13px sans-serif',fillColor:C.Color.LIGHTCYAN,
      showBackground:true,backgroundColor:C.Color.fromCssColorString('#102131'),disableDepthTestDistance:Infinity}});
  routeEntity=viewer.entities.add({id:'accepted-route',polyline:{positions:[],width:7,
    material:new C.PolylineGlowMaterialProperty({glowPower:0.18,color:C.Color.fromCssColorString('#56e0dc')})}});
  home();
  show('geography-status',`${Object.keys(geo.roads).length} road edges · OSM buildings · WGS84 alignment · Drag to explore`);
}

function activateFallback(on) {
  fallbackMode=on;
  $('fallback').toggleAttribute('hidden',!on);
  $('map').hidden=on;
  $('flat').textContent=on?'Switch to 3D':'2D / 3D';
  if (on) {
    show('geography-status','2D geographical fallback · Actual OSM / SUMO geometry');
    if (latest) renderFallback(latest);
  } else if (viewer) { viewer.resize(); viewer.scene.requestRender(); }
}
function marker(id,lon,lat,label,color) {
  let entity=viewer.entities.getById(id);
  if (!entity) entity=viewer.entities.add({id,position:position(lon,lat,8),
    point:{pixelSize:14,color:C.Color.fromCssColorString(color),outlineWidth:2,outlineColor:C.Color.WHITE,disableDepthTestDistance:Infinity},
    label:{text:label,font:'11px sans-serif',pixelOffset:new C.Cartesian2(0,-23),showBackground:true,
      backgroundColor:C.Color.fromCssColorString('#102131'),disableDepthTestDistance:Infinity}});
  return entity;
}

function renderMap(state) {
  const frame=state.chennai;
  if (!frame || !viewer || fallbackMode) { if (fallbackMode) renderFallback(state); return; }
  const present=new Set();
  for (const v of frame.vehicles) {
    present.add(v.id);
    let entity=vehicles.get(v.id);
    const ambulance=v.category==='ambulance';
    if (!entity) {
      entity=viewer.entities.add({id:'vehicle:'+v.id,name:v.id,
        box:{dimensions:new C.Cartesian3(ambulance?6:3,ambulance?13:7,ambulance?5:2.7),
          material:C.Color.fromCssColorString(ambulance?'#ff6475':'#8db7ea'),outline:ambulance,outlineColor:C.Color.WHITE},
        point:{pixelSize:ambulance?13:4,color:C.Color.fromCssColorString(ambulance?'#ff6475':'#8db7ea'),disableDepthTestDistance:Infinity},
        label:ambulance?{text:'✚ AMBULANCE',font:'bold 12px sans-serif',pixelOffset:new C.Cartesian2(0,-30),
          showBackground:true,backgroundColor:C.Color.fromCssColorString('#632838'),disableDepthTestDistance:Infinity}:undefined});
      vehicles.set(v.id,entity);
    }
    const target=position(v.longitude,v.latitude,ambulance?3:2);
    // Render the received measurement directly. No extrapolated vehicle simulation.
    entity.position=target;
    entity.orientation=C.Transforms.headingPitchRollQuaternion(target,new C.HeadingPitchRoll(C.Math.toRadians(v.heading),0,0));
    entity.description=safeDescription(`${v.source} · ${v.simulation_time}s · ${v.road} · ${num(v.speed)} m/s. Display glyphs enlarged for visibility.`);
    if (ambulance && follow) viewer.camera.lookAt(target,new C.HeadingPitchRange(0,C.Math.toRadians(-55),650));
  }
  for (const [id,entity] of vehicles) if (!present.has(id)) {viewer.entities.remove(entity);vehicles.delete(id);}
  if (!follow) viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
  for (const [id,entity] of roads) {
    const traffic=frame.roads[id];
    entity.polyline.material=C.Color.fromCssColorString(traffic?.blocked?'#fa4f66':traffic?.congestion==='HIGH'?'#f6a75a':traffic?.congestion==='MEDIUM'?'#bda36a':'#405269');
  }
  const route=state.plan?.route || [];
  if (JSON.stringify(route)!==previousRoute) {
    routeEntity.polyline.positions=line(route.flatMap(id=>geo.roads[id]?.coordinates || []),4);
    previousRoute=JSON.stringify(route);
  }
  for (const hospital of frame.hospitals) {
    const entity=marker(hospital.id,hospital.longitude,hospital.latitude,'H · '+hospital.name,'#61d6b5');
    entity.description=safeDescription(`${hospital.location_source}\n${hospital.availability_source}\n${hospital.road_access}\nAccess offset ${hospital.road_access_distance_m} m · Services ${hospital.emergency_services}`);
  }
  marker('incident',frame.incident.longitude,frame.incident.latitude,'SIMULATED INCIDENT','#f6a75a');
  for (const signal of frame.signals) {
    const color=signal.state.includes('G')?'#68e3b3':signal.state.includes('y')?'#ffce73':'#ff6475';
    const entity=marker('signal:'+signal.signal_id,signal.longitude,signal.latitude,'TLS · '+signal.phase,color);
    entity.point.color=C.Color.fromCssColorString(color);
    entity.description=safeDescription(`SUMO phase ${signal.phase} · link states ${signal.state}. Each character represents a controlled link. Real signal unverified.`);
    signals.set(signal.signal_id,entity);
  }
  for (const obs of frame.gps || []) {
    const entity=marker('gps:'+obs.vehicle_id,obs.longitude,obs.latitude,'GPS REPLAY · '+obs.vehicle_id,'#d48cfa');
    entity.description=safeDescription(`${obs.source} · ${obs.timestamp} · accuracy ${obs.accuracy_m} m. Synthetic recorded feed; not a live tracked vehicle.`);
  }
  for(const entity of [...viewer.entities.values]) if(entity.id.startsWith('gps:') && !(frame.gps || []).some(obs=>'gps:'+obs.vehicle_id===entity.id))viewer.entities.remove(entity);
  renderTrafficOverlay(frame);
  viewer.scene.requestRender();
}

function renderFallback(state) {
  if (!geo) return;
  const svg=$('fallback'), ns='http://www.w3.org/2000/svg';
  svg.replaceChildren();svg.setAttribute('viewBox','0 0 1000 800');
  const [west,south,east,north]=geo.bounds;
  const xy=(lon,lat)=>[60+(lon-west)/(east-west)*880,730-(lat-south)/(north-south)*650];
  function path(points,color,width) {const el=document.createElementNS(ns,'polyline');el.setAttribute('points',points.map(p=>xy(...p).join(',')).join(' '));el.setAttribute('fill','none');el.setAttribute('stroke',color);el.setAttribute('stroke-width',width);svg.append(el);}
  for (const [id,road] of Object.entries(geo.roads)) path(road.coordinates,state.chennai?.roads[id]?.congestion==='HIGH'?'#f6a75a':'#435875',1.5);
  for (const id of state.plan?.route || []) if (geo.roads[id]) path(geo.roads[id].coordinates,'#56e0dc',4);
  function dot(lon,lat,r,color,label) {const [x,y]=xy(lon,lat);const el=document.createElementNS(ns,'circle');for(const [k,v] of Object.entries({cx:x,cy:y,r,fill:color}))el.setAttribute(k,v);svg.append(el);if(label){const t=document.createElementNS(ns,'text');t.setAttribute('x',x+8);t.setAttribute('y',y-8);t.setAttribute('fill',color);t.setAttribute('font-size','12');t.textContent=label;svg.append(t);}}
  for(const v of state.chennai?.vehicles || []) dot(v.longitude,v.latitude,v.category==='ambulance'?7:2,v.category==='ambulance'?'#ff6475':'#8db7ea',v.category==='ambulance'?'AMBULANCE':null);
  for(const h of state.chennai?.hospitals || [])dot(h.longitude,h.latitude,6,'#61d6b5','H · '+h.name);
  for(const s of state.chennai?.signals || [])dot(s.longitude,s.latitude,5,s.state.includes('G')?'#68e3b3':s.state.includes('y')?'#ffce73':'#ff6475');
  for(const obs of state.chennai?.external?.observations || []) {
    if(obs.road_geometry.length<2)continue;
    path(obs.road_geometry,obs.freshness_status==='FRESH'?'#d48cfa':'#9ca6b4',3);
    if(obs.incident_type)dot(...obs.road_geometry[0],6,'#ffd166',obs.source_type+' · '+obs.incident_type);
  }
  dot(80.154,12.8408,4,'#b9edf0','VIT CHENNAI');
  dot(80.170,12.829,5,'#f6a75a','INCIDENT');
}

function renderTrafficOverlay(frame) {
  const present=new Set();
  for(const obs of frame.external?.observations || []) {
    if(obs.road_geometry.length<2)continue;
    const id='external-flow:'+obs.provider+':'+obs.provider_segment_id;
    present.add(id);
    let entity=externalEntities.get(id);
    if(!entity){entity=viewer.entities.add({id,name:obs.source_type+' · '+obs.provider_segment_id,polyline:{positions:[],width:5}});externalEntities.set(id,entity);}
    entity.polyline.positions=line(obs.road_geometry,12);
    entity.polyline.material=new C.PolylineDashMaterialProperty({color:C.Color.fromCssColorString(obs.freshness_status==='FRESH'?'#d48cfa':'#9ca6b4'),dashLength:18});
    entity.description=safeDescription(`${obs.source_type} · ${obs.freshness_status} · ${obs.matching_status} · ${obs.match_reason} · ${num(obs.current_speed)} m/s · Advisory only`);
    if(obs.incident_type){
      const incidentId='external-incident:'+id;present.add(incidentId);
      const [lon,lat]=obs.road_geometry[Math.floor(obs.road_geometry.length/2)];
      const markerEntity=marker(incidentId,lon,lat,obs.source_type+' · '+obs.incident_type,'#ffd166');
      markerEntity.position=position(lon,lat,15);
      markerEntity.description=safeDescription(`${obs.incident_description || obs.incident_type} · ${obs.freshness_status} · ${obs.matching_status}`);
      externalEntities.set(incidentId,markerEntity);
    }
  }
  for(const [id,entity] of externalEntities)if(!present.has(id)){viewer.entities.remove(entity);externalEntities.delete(id);}
}

function renderTrafficPanel(state) {
  const external=state.chennai?.external || {}, observations=external.observations || [];
  show('traffic-status',`${external.provider || 'Unavailable'} · ${external.display_status || external.status || 'UNAVAILABLE'} · ${external.match_status || 'NO VERIFIED ROAD MATCHES'} · ${external.source || 'UNAVAILABLE'}`);
  show('traffic-counts',`${external.observation_count || observations.length} observations · ${external.matched_roads || 0} matched roads · ${external.unmatched_records || 0} unmatched · ${external.stale_records || 0} STALE / EXPIRED · ${external.unknown_time_records || 0} UNKNOWN time`);
  const ages=observations.map(o=>o.age_seconds).filter(v=>typeof v==='number');
  show('traffic-time',`Last successful fetch: ${external.last_update || 'UNAVAILABLE'} · Source age: ${ages.length?num(Math.max(...ages))+' s':'UNKNOWN'} · Coverage bounds: ${pretty(external.coverage_area)} · HERE / TomTom coverage unverified unless authorized and measured`);
  show('traffic-errors',`Providers: ${Object.entries(external.provider_statuses || {}).map(([p,s])=>p+': '+s.replaceAll('_',' ')).join(' · ')} · API / data errors: ${(external.errors || []).join(', ') || 'none reported'} · Failed polls: ${external.failed_fetches || 0}`);
  const ids=[...new Set(observations.flatMap(o=>o.matched_sumo_edges || []))];
  if(selectedTrafficRoad && !ids.includes(selectedTrafficRoad))ids.unshift(selectedTrafficRoad);
  if(!selectedTrafficRoad)selectedTrafficRoad=ids[0] || '';
  $('traffic-road').replaceChildren(...(ids.length?ids:['']).map(id=>{const option=document.createElement('option');option.value=id;option.textContent=id || 'NO VERIFIED ROAD MATCHES';option.selected=id===selectedTrafficRoad;return option;}));
  const rows=[['SUMO edge ID',selectedTrafficRoad || 'UNAVAILABLE'],['SUMO_SIMULATED speed',num(state.chennai?.roads[selectedTrafficRoad]?.speed)+' m/s']];
  const selected=observations.filter(o=>o.matching_status==='MATCHED' && o.matched_sumo_edges.includes(selectedTrafficRoad));
  for(const o of selected)rows.push(['Provider segment',o.provider_segment_id],['Data source',o.source_type],['External speed',num(o.current_speed)+' m/s'],['Free-flow speed',num(o.free_flow_speed)+' m/s'],['Reported congestion',num(o.congestion,2)],['Source timestamp',o.observation_timestamp || 'UNKNOWN'],['Quality',o.freshness_status+' · '+o.matching_status],['Match reason',o.match_reason]);
  if(!selected.length)rows.push(['External traffic','UNAVAILABLE — NO VERIFIED ROAD MATCHES']);
  table('traffic-comparison',['Measurement','Value'],rows);
}

function table(target, headers, rows) {
  const el=document.createElement('table'),head=document.createElement('tr');
  for (const title of headers) {const th=document.createElement('th');th.textContent=title;head.append(th);}
  el.append(head);
  for(const row of rows) {const tr=document.createElement('tr');for(const value of row){const td=document.createElement('td');td.textContent=value??'UNAVAILABLE';tr.append(td);}el.append(tr);}
  $(target).replaceChildren(el);
}
function renderPanel(state) {
  renderTrafficPanel(state);
  const frame=state.chennai, plan=state.plan, ambulance=frame?.vehicles.find(v=>v.id===frame.ambulance_id);
  const hospital=frame?.hospitals.find(h=>h.id===state.hospital);
  show('status',state.terminal?.outcome || (frame?'RUNNING':'WAITING FOR TELEMETRY'));
  show('mode',state.playback+' · '+(state.provenance.profile || 'UNKNOWN PROFILE')+' · READ ONLY');
  show('time',num(frame?.simulation_time ?? state.time,0)+' s');
  show('count',frame?.vehicles.length);show('replans',state.plans.length);
  show('queues',frame?Object.values(frame.roads).reduce((a,r)=>a+r.queue,0):null);
  show('emergency-state',state.terminal?.outcome || (plan?'DISPATCHED':'WAITING'));
  show('ambulance-id',frame?.ambulance_id || 'Waiting for ambulance dispatch');
  const kv=[['Speed',ambulance?num(ambulance.speed*3.6)+' km/h':'UNAVAILABLE'],
    ['Location',ambulance?`${num(ambulance.latitude,5)}, ${num(ambulance.longitude,5)}`:'UNAVAILABLE'],
    ['Current road',ambulance?.road],['Hospital',hospital?.name || state.hospital],
    ['Plan ETA',plan?num(plan.eta)+' s · estimate at acceptance':'UNAVAILABLE'],
    ['Response time',state.terminal?.metrics.travel_time != null?num(state.terminal.metrics.travel_time)+' simulation s':'UNAVAILABLE'],
    ['Arrival',state.terminal?.metrics.arrival_time != null?num(state.terminal.metrics.arrival_time)+' simulation s':'UNAVAILABLE'],
    ['Observation',frame?num(frame.simulation_time,0)+' s · SUMO_SIMULATED':'UNAVAILABLE']];
  $('ambulance').replaceChildren(...kv.flatMap(pair=>pair.map(text=>{const span=document.createElement('span');span.textContent=text??'UNAVAILABLE';return span;})));
  $('plan-history').replaceChildren(...state.plans.map(p=>{const el=document.createElement('span');el.textContent=`P${p.plan.revision} · ${p.time}s`;return el;}));
  show('decision',state.decision.decision || state.decision.outcome || 'UNKNOWN');
  show('reason',state.decision.reason || 'No planning decision observed');
  table('scores',['Candidate','Score','Validity'],Object.entries(state.decision.candidate_scores || {}).map(([id,s])=>[id,typeof s.final_score==='number'?num(s.final_score):s.final_score,s.usable?'VALID':s.reason]));
  show('agents',pretty({traffic:state.initial_agents.traffic_assessment,ambulance:state.initial_agents.ambulance_result,
    hospital:state.initial_agents.hospital_result,recommendations:plan?.recommendations}));
  show('execution',pretty({plan,execution:state.execution,validation:state.decision.validation_result}));
  $('signals').replaceChildren(...(frame?.signals || []).map(s=>{const div=document.createElement('div');div.textContent=`${s.signal_id} · phase ${s.phase} · ${s.state} · t=${s.simulation_time}s`;return div;}));
  table('roads',['Edge','m/s','Queue','State'],Object.entries(frame?.roads || {}).sort((a,b)=>b[1].queue-a[1].queue).map(([id,r])=>[id,num(r.speed),r.queue,r.blocked?'BLOCKED':r.congestion]));
  show('source',`${state.playback==='REPLAY'?'REPLAY of ':''}SUMO SIMULATED DATA · External: ${frame?.external?.source || 'UNAVAILABLE'}`);
  show('external',pretty({traffic:frame?.external || 'UNAVAILABLE',gps:frame?.gps?.length?frame.gps:'UNAVAILABLE — no GPS feed configured'}));
  const age=frame?.observed_at_utc?(Date.now()-Date.parse(frame.observed_at_utc))/1000:null;
  show('freshness',state.playback==='REPLAY'?`Recorded at ${frame?.observed_at_utc || 'UNAVAILABLE'}`:`Observation age ${num(age)} s · ${frame?.health.traci || 'UNKNOWN'}`);
  const timeline=[...state.timeline];
  // Scenario and initial-dispatch events are supplied separately by the API.
  timeline.push(...(state.pilot_events || []));timeline.sort((a,b)=>a.time-b.time);
  $('timeline').replaceChildren(...timeline.map(e=>{const div=document.createElement('div');div.className='event';const b=document.createElement('b'),span=document.createElement('span');b.textContent=`${e.time}s · ${e.action.replaceAll('_',' ')}`;span.textContent=e.result || e.plan_id || 'Observed runtime event';div.append(b,span);return div;}));
  const timelineEl=$('timeline');timelineEl.scrollLeft=timelineEl.scrollWidth;
  show('outcome',state.terminal?`${state.terminal.outcome} · ${state.terminal.reason}`:'Execution verified before plan acceptance');
  if (state.read_error || state.telemetry_error) notice(state.read_error || state.telemetry_error);
  else if (state.playback!=='REPLAY' && age>5) notice('Telemetry is stale. Last received values remain visible.');
  else notice(fallbackMode?'2D fallback active. '+viewerFailure:'Simulation-only response · Enlarged vehicle glyphs');
}

async function update() {
  if(busy)return;
  busy=true;
  try {
    const response=await fetch('/api/state'+(replay?'?at='+replayAt:''));
    if(!response.ok)throw new Error('Telemetry HTTP '+response.status);
    latest=await response.json();
    const firstReplay=!replay && latest.playback==='REPLAY';
    replay=latest.playback==='REPLAY';
    $('replay-controls').hidden=!replay;
    if(replay){$('seek').max=latest.telemetry_max_time; if(firstReplay){replayAt=1;playing=true;} $('seek').value=replayAt;}
    renderPanel(latest);renderMap(latest);
  } catch(error) {notice('Data unavailable: '+error.message);show('status','DISCONNECTED');}
  finally{busy=false;}
}
$('traffic-road').onchange=()=>{selectedTrafficRoad=$('traffic-road').value;if(latest)renderTrafficPanel(latest);};
$('home').onclick=home;
$('follow').onclick=()=>{follow=!follow;$('follow').classList.toggle('active',follow);if(latest)renderMap(latest);};
$('flat').onclick=()=>{if(!viewer){notice('WebGL unavailable; 2D fallback remains active.');return;}activateFallback(!fallbackMode);};
$('imagery').onclick=()=>{
  if(!viewer)return;
  imageryOn=!imageryOn;
  if(imageryOn){const provider=new C.OpenStreetMapImageryProvider({url:'https://tile.openstreetmap.org/',maximumLevel:19});provider.errorEvent.addEventListener(()=>notice('OSM tiles unavailable; local road geometry remains visible.'));viewer.imageryLayers.addImageryProvider(provider);}
  else viewer.imageryLayers.removeAll();
  $('imagery').classList.toggle('active',imageryOn);viewer.scene.requestRender();
};
$('play').onclick=()=>{if(replayAt>=Number($('seek').max))replayAt=1;playing=!playing;$('play').textContent=playing?'Pause replay':'Play replay';};
$('seek').oninput=()=>{replayAt=Number($('seek').value);playing=false;$('play').textContent='Play replay';update();};
async function start() {
  try {const response=await fetch('/api/geography');if(!response.ok)throw new Error('Map unavailable');geo=await response.json();
    try{initializeCesium();}catch(error){viewerFailure=error.message;notice(error.message);activateFallback(true);}
    await update();setInterval(()=>{const now=performance.now();if(replay&&playing){replayAt=Math.min(Number($('seek').max),replayAt+(now-lastWall)/1000*Number($('rate').value));if(replayAt>=Number($('seek').max))playing=false;}lastWall=now;update();},500);
  }catch(error){notice('Map initialization failed: '+error.message);}
}
start();
