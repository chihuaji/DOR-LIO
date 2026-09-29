/* One shared display camera; independent source-time and screen-space wipe. */
(function () {
 'use strict';
 const host=document.getElementById('mtp01-viewer');if(!host)return;
 const path=window.MTP01_PATH,seek=document.getElementById('mtp01-time'),label=document.getElementById('mtp01-clock'),play=document.getElementById('mtp01-play');
 let viewer,playing=false,time=170,last=0;
 seek.max=path.duration;seek.value=time;
 function showTime(){label.textContent=time.toFixed(1)+' / '+path.duration.toFixed(1)+' s';seek.value=time;seek.setAttribute('aria-valuetext',time.toFixed(1)+' seconds along trajectory');}
 function pose(){
  let lo=0,hi=path.times.length-1;while(lo+1<hi){const m=(lo+hi)>>1;if(path.times[m]<=time)lo=m;else hi=m;}
  const a=lo,b=hi,u=Math.max(0,Math.min(1,(time-path.times[a])/(path.times[b]-path.times[a])));
  const p=path.cameraPositions[a].map((v,i)=>v+(path.cameraPositions[b][i]-v)*u),yaw=path.yaw[a]+(path.yaw[b]-path.yaw[a])*u;
  viewer._camera.position.set(p[0],p[1],p[2]+path.cameraHeightOffset);
  viewer._camera.lookAt(p[0]+Math.cos(yaw)*10,p[1]+Math.sin(yaw)*10,p[2]+path.cameraHeightOffset-Math.tan(13*Math.PI/180)*10);
  const n=Math.min(path.positions.length,Math.ceil(a)+120);viewer.route.geometry.setDrawRange(a,n-a);
 }
 function setPlay(v){playing=v;play.textContent=v?'Pause':'Play tour';play.setAttribute('aria-pressed',String(v));last=0;}
 seek.addEventListener('input',()=>{time=Number(seek.value);setPlay(false);showTime();if(viewer)pose();});
 play.addEventListener('click',()=>{if(time>=path.duration)time=0;setPlay(!playing);});
 document.getElementById('mtp01-reset').addEventListener('click',()=>{time=170;setPlay(false);showTime();if(viewer){viewer._setSplit(.5);pose();}});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)setPlay(false);});
 async function start(){
  try {
   viewer=new CompareViewer(host,{leftLabel:'BTSA',rightLabel:'DOR-LIO (Ours)',pointSize:2.3,preserveView:true});window.mtp01Viewer=viewer;
   host.querySelector('.cmp-hint').textContent='Drag the divider to compare · Scrub time below to travel';
   viewer.setLegend('Red: DOR-derived labels on BTSA · White: trajectory');
   const geo=new THREE.BufferGeometry().setFromPoints(path.positions.map(p=>new THREE.Vector3(...p)));
   viewer.route=new THREE.Line(geo,new THREE.LineBasicMaterial({color:0xffffff,depthTest:false,transparent:true,opacity:.8}));viewer.route.renderOrder=10;viewer._scene.add(viewer.route);
   viewer._camera.fov=65;viewer._camera.near=.35;viewer._camera.far=90;viewer._camera.updateProjectionMatrix();
   viewer._controls.update=()=>{const now=performance.now();if(playing&&last){time=Math.min(path.duration,time+(now-last)/1000*Number(document.getElementById('mtp01-speed').value));showTime();if(time>=path.duration)setPlay(false);}last=now;pose();};
   await viewer.loadPair('data/mtp01/mtp01_btsa.ply','data/mtp01/mtp01_dor.ply');
   if(viewer._raw&&viewer._clean){host.dataset.ready='true';play.disabled=false;pose();}
  }catch(e){host.textContent='Interactive map could not load. Please use the recorded comparison below.';console.error(e);}
 }
 showTime();
 const observer=new IntersectionObserver(entries=>{for(const e of entries){if(e.isIntersecting&&!viewer){start();}if(!e.isIntersecting){setPlay(false);last=0;}}},{rootMargin:'0px'});observer.observe(host);
})();
