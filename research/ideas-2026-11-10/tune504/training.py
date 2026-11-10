"""Scheduled tune8 init/run with immutable config and complete-gradient checks."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/localq/rounds/tune8')
RUN = 'oc504-tune8'
spec = importlib.util.spec_from_file_location('tune8_engine', R / 'tools/tune/tune.py')
tune = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tune)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('phase', choices=['init', 'train'])
    args = a.parse_args()
    cfg = json.loads((D / 'config.json').read_text())
    run = tune.RUNS / RUN
    if args.phase == 'init':
        assert not run.exists(), 'Do not overwrite a partially initialised run; review required'
        def pooled_build(bot):
            subprocess.run([sys.executable, R / 'tools/pooled.py', '1', '--', 'cambc', 'build', str(bot), '--release'], cwd=R, check=True)
        tune.build_release = pooled_build
        tune.cmd_init(SimpleNamespace(run=RUN, bot=cfg['bot'], opps=','.join('variants/' + n.removeprefix('variants-') for n in cfg['opps']),
                      pool=','.join(cfg['pool']), maps=cfg['maps_per_iter'], pairs=cfg['pairs'], seed=cfg['seed'], params=None, force=False))
        (run / 'config.json').write_text(json.dumps(cfg, indent=2) + '\n')
        defaults = tune.patch.Base(run / 'base').defaults()
        x = {n: (defaults[n] - lo) / (hi - lo) for n, (lo, hi, _) in cfg['params'].items()}
        (run / 'state.json').write_text(json.dumps({'k': 0, 'x': x}, indent=2) + '\n')
        files = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for directory in [run/'base/src',run/'opps'] for p in directory.rglob('*') if p.is_file() and '.cambc' not in p.parts}
        (D/'training-inputs.json').write_text(json.dumps(files,indent=2)+'\n')
        return
    expected = json.loads((run / 'config.json').read_text())
    assert expected == cfg
    state = json.loads((run / 'state.json').read_text())
    assert state['k'] == 0 and not (run / 'history.jsonl').exists(), 'No automatic restart/extra iterations'
    files = json.loads((D/'training-inputs.json').read_text())
    maps = {x['path']:x['sha256'] for x in json.loads((D/'maps.json').read_text())['selected']}
    summarize = tune.summarize
    def checked_summary(path):
        st = summarize(path)
        if st is not None:
            assert st['outcome'] in ('teamA','teamB') and isinstance(st['rounds'],int) and st['rounds'] >= 0, ('Invalid game metadata',path)
        return st
    tune.summarize = checked_summary
    start = tune.Batch.start
    finish = tune.Batch.finish
    def checked_start(self):
        assert json.loads((run / 'config.json').read_text()) == cfg
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in files.items()), 'Training input drift'
        assert all(str(m) in maps and hashlib.sha256(m.read_bytes()).hexdigest() == maps[str(m)] for m,_,_ in self.games), 'Training map drift'
        assert self.cfg == cfg and self.n == 1152 and len(self.games) == 144 and len(self.cands) == 8
        assert len({str(m) for m, _, _ in self.games}) == 24
        return start(self)
    def checked_finish(self):
        assert self.proc.returncode == 0, ('run-batch error', self.tag)
        # Preserve failed evidence; successful batches are deleted only after all candidates have every cell.
        os.environ['TUNE_KEEP'] = '1'
        held = tune.cpu_slots.acquire(32, least=1)
        executor = tune.ThreadPoolExecutor
        tune.ThreadPoolExecutor = lambda workers=1, *a, **kw: executor(min(workers, len(held)), *a, **kw)
        try:
            res = finish(self)
            with (D/'parsing-slots.jsonl').open('a') as f:
                f.write(json.dumps({'iteration':self.tag,'workers':len(held)})+'\n')
        finally:
            tune.ThreadPoolExecutor = executor
            tune.cpu_slots.release(held)
        assert set(res) == {f'{s}{i}' for s in 'pm' for i in range(4)}
        for name, rows in res.items():
            assert len(rows) == 144 and {r[2] for r in rows} == set(range(144)), (self.tag, name, 'missing scores')
            assert all(math.isfinite(r[0]) and r[1] in (-1, 0, 1) for r in rows)
        assert json.loads((run / 'config.json').read_text()) == cfg
        shutil.rmtree(self.work)
        return res
    tune.Batch.start, tune.Batch.finish = checked_start, checked_finish
    tune.cmd_run(SimpleNamespace(run=RUN, hours=None, iters=600))
    assert json.loads((run / 'state.json').read_text())['k'] == 600
    h = [json.loads(x) for x in (run / 'history.jsonl').read_text().splitlines()]
    assert [x['k'] for x in h] == list(range(1, 601)) and all(x['games'] == 1152 for x in h)


if __name__ == '__main__':
    main()
