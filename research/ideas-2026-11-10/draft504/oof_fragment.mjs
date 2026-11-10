// Inserted only into a temporary sibling of the sealed model.mjs during the queued phase.
function draft17OOF(o) {
  const table = mapTable(o.lab), rows = gameRows(o.lab, table);
  const fixed = readJson(o['fixed-model']);
  if (!fixed || !fixed.lam || fixed.features.join() !== FEAT.map(f => f[0]).join()) throw new Error('Invalid fixed OOF hyperparameters');
  if (rows.some(r => r.prior)) throw new Error('Draft17 does not pool historical games');
  const lam = { ...OPP_LAM, ...fixed.lam }, alpha = fixed.alpha ?? 0;
  fs.mkdirSync(o.out, { recursive: true });
  const fd = fs.openSync(path.join(o.out, 'rows.jsonl'), 'w');
  const provenance = { lam, alpha, fixed_model: o['fixed-model'], normalization: 'common training pool, no outcome labels', folds: [] };
  startPool(rows, +(o.threads ?? 1), true);
  try {
    for (let k = 0; k < FOLDS; k++) {
      // No full-data fitted warm start or outcome-selected hyperparameter enters a fold fit.
      const fit = fitAll(poolView(k, 0), lam, alpha);
      const trainKeys = new Set(rows.filter(r => r.fold !== k).map(r => r.key));
      const test = rows.filter(r => r.fold === k);
      if (!test.length || test.some(r => trainKeys.has(r.key))) throw new Error('Invalid out-of-map split');
      for (const r of test) fs.writeSync(fd, JSON.stringify({key:r.key, fold:k, picks:r.picks,
        A:r.A, B:r.B, z:Array.from(r.z.slice(0,25)), eta:dot(fit.picks[r.picks].theta,r),
        oursA:!r.g.botA || r.g.botA==='self', oursB:!r.g.botB || r.g.botB==='self', y:r.win})+'\n');
      provenance.folds.push({fold:k,train_maps:trainKeys.size,test_maps:new Set(test.map(r=>r.key)).size,rows:test.length});
    }
    fs.writeFileSync(path.join(o.out,'pool.json'),JSON.stringify(table.maps.map(m=>({key:m.key,picks:m.picks,z:Array.from(m.z.slice(0,25))}))));
    fs.writeFileSync(path.join(o.out,'provenance.json'),JSON.stringify(provenance,null,2)+'\n');
  } finally { fs.closeSync(fd); stopPool(); }
}
