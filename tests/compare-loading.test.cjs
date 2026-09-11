const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const pending = [];
const context = {window: {}, console, AbortController,
  DORPLY: {fetchPLY: (url, progress, options) => new Promise(resolve => pending.push({url, resolve, options})), parsePLY: x => x},
  THREE: {BufferGeometry: class {setAttribute() {} computeBoundingBox(){this.boundingBox={getCenter:()=>({clone(){return this}}),getSize:()=>({length:()=>2})}} dispose(){}},
    BufferAttribute: class {}, PointsMaterial: class {dispose(){}}, Points: class {constructor(g,m){this.geometry=g;this.material=m}}, Vector3: class {}}
};
vm.runInNewContext(fs.readFileSync('js/compare-viewer.js','utf8'),context);
const viewer=Object.create(context.window.CompareViewer.prototype);
Object.assign(viewer,{opts:{pointSize:1},_loading:{style:{}},_loadingText:{},_loadingBar:{style:{}},_scene:{add(){},remove(){}},_controls:{fit(){}},_home:null,_raw:null,_clean:null});
const geo={positions:new Float32Array([0,0,0]),colors:new Float32Array([1,1,1])};
(async()=>{
  const first=viewer.loadPair('old-left','old-right');
  const second=viewer.loadPair('new-left','new-right');
  assert.ok(pending[0].options?.signal.aborted,'Changing pages must abort the previous download');
  for (const p of pending.filter(p=>p.url.startsWith('new')))p.resolve(geo);
  await second;const current=viewer._raw;
  for (const p of pending.filter(p=>p.url.startsWith('old')))p.resolve(geo);
  await first;
  assert.equal(viewer._raw,current,'Late old-page results must not replace the current pair');
  assert.equal(viewer._loading.style.display,'none');
  console.log('PASS: pagination cancels downloads and ignores stale map results');
})().catch(e=>{console.error(e);process.exitCode=1});
