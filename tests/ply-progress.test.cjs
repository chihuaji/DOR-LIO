const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
  for (const encoding of ['gzip', 'identity']) {
    const context = {window: {ReadableStream}, Uint8Array, TextDecoder, fetch: async () => ({
      ok: true, headers: new Headers({'Content-Length': '2', 'Content-Encoding': encoding}),
      body: new ReadableStream({start(c) {c.enqueue(new Uint8Array(encoding === 'gzip' ? 8 : 2)); c.close();}})
    })};
    vm.runInNewContext(fs.readFileSync('js/ply-loader.js', 'utf8'), context);
    const progress = [];
    const bytes = await context.window.DORPLY.fetchPLY('map.ply', (done, total) => progress.push({done, total}));
    assert.equal(progress[0].total, encoding === 'gzip' ? 0 : 2);
    assert.equal(bytes.length, encoding === 'gzip' ? 8 : 2);
  }
  console.log('PASS compressed PLY progress uses decoded bytes without an invalid percentage');
})().catch(e => {console.error(e); process.exitCode = 1;});
