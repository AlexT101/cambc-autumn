"""Build a Fish r8 body (mitefit/mkbody.py's layers, Fish's draft):
  1. draft: Fish r8's exact picks per (ranked map, side) where the map's hash is known (spar-tools hashes.json plus
     ~/tmp-offload/fishr8/hashes05.json), elsewhere its pick model (fitgen.py's fm_draft_F.h, most likely comp).
  2. run time: member seed and draft salt from the runner (fgate --fish-body, calib.sh).
  3. constants --set/--mul, 3b. noise (--noise SD, default 0.2), 4. rules --patch/--py, as mitefit/mkbody.py.
    py mkbody.py NAME [--base variants/c520-ps] [--set K=V]... [--mul K=F]... [--patch F]... [--py 'S [ARGS]']... [-f]"""
import argparse, json, os, re, shlex, subprocess, sys
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
import mkbody as mk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta import CH
R = mk.R; T = mk.T; FG = mk.FG; H = Path.home() / 'tmp-offload/fishr8'
FULL = {'Vesper': 'Vesper Vale', 'C&I': 'Cassi & Issac', 'HoR': 'Heart of Ruin'}

def table(bot):
    hashes = json.load(open(T / 'hashes.json'))
    if (H / 'hashes05.json').exists(): hashes.update(json.load(open(H / 'hashes05.json')))
    rows = {}
    for v in json.load(open(H / 'ours.json')).values():
        if v['refset'] == 'r8':
            rows[(v['map'].replace('_', '-'), 'b' if v['side'] == 'a' else 'a')] = [FULL.get(CH[i], CH[i]) for i in v['opp_picks']]
    out = []
    for key, h in sorted(hashes.items()):
        m, side = key.split(':'); m = m.replace('_', '-')
        if (m, side) in rows:
            p = rows[(m, side)]
            out.append(f"    {{{h}ull, {len(p)}, {{{', '.join('C::' + mk.enum(x) for x in p)}}}}}, // {m} {side}")
    (bot / 'src/draft/spar_draft.h').write_text(
        '#pragma once\n// fishr8/mkbody.py: Fish r8\'s picks per ranked map and the side it plays.\n#include <cstdint>\n'
        'namespace spar {\nusing C = cambc::champion_draft;\nstruct Entry { std::uint64_t hash; int n; C picks[5]; };\n'
        'inline constexpr Entry table[] = {\n' + '\n'.join(out) + '\n};\n}\n')
    return len(out)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('--base', default='variants/c520-ps')
    ap.add_argument('--set', action='append', default=[]); ap.add_argument('--mul', action='append', default=[])
    ap.add_argument('--patch', action='append', default=[]); ap.add_argument('--py', action='append', default=[])
    ap.add_argument('-f', action='store_true'); ap.add_argument('--noise', type=float, default=0.2)
    a = ap.parse_args(); name = f'variants/{a.name}'; bot = R / 'bots' / name
    subprocess.run([str(R / 'copybot')] + (['-f'] if a.f else []) + [a.base, name], check=True, cwd=R, capture_output=True)
    subprocess.run([sys.executable, str(T / 'patch_spar.py'), str(bot)], check=True, capture_output=True)
    n = table(bot)
    fm = H / 'fm/fm_draft_F.h'; assert fm.exists(), 'run fitgen.py first'
    tmp = FG / 'fm_draft_F.h'; orig = tmp.read_text()
    try:
        tmp.write_text(fm.read_text()); subprocess.run([sys.executable, str(FG / 'patch_fm.py'), str(bot), 'F', '0'], check=True, capture_output=True)
    finally: tmp.write_text(orig)
    d = bot / 'src/draft/draft.cc'; s = d.read_text()
    s = s.replace('        return fm_forced();\n', '''        const auto h = test_compositions::map_hash();
        debug_block({ std::printf("SPARHASH %llu\\n", static_cast<unsigned long long>(h)); });
        for (const auto& e : spar::table)
            if (e.n && e.hash == h && e.n == static_cast<int>(cambc::draft::team_size()))
                return new std::vector<cambc::champion_draft>(e.picks, e.picks + e.n);
        return fm_forced();
''', 1)
    (bot / 'src/experiment_config.h').write_text(mk.RT_H)
    f = bot / 'src/draft/fm_draft.h'; h = f.read_text()
    h, k = re.subn(r'inline constexpr std::uint64_t salt = \d+ull;', 'inline std::uint64_t salt() { return experiment_config(1); }', h); assert k == 1
    f.write_text(h.replace('#include <cstdint>', '#include <cstdint>\n#include "../experiment_config.h"', 1))
    assert s.count('fm::salt *') == 1; d.write_text(s.replace('fm::salt *', 'fm::salt() *'))
    p = bot / 'src/params.h'; ph = p.read_text(); log = []
    for kv in a.set: k, v = kv.split('='); ph, c = mk.constant(ph, k, val=v); log.append((k, *c))
    for kv in a.mul: k, v = kv.split('='); ph, c = mk.constant(ph, k, mul=float(v)); log.append((k, *c))
    p.write_text(ph)
    if a.noise > 0: mk.noise(bot, a.noise)
    for x in a.patch: subprocess.run(['patch', '-p1', '-i', str(Path(x).resolve())], cwd=bot / 'src', check=True)
    for x in a.py: subprocess.run([sys.executable] + shlex.split(x) [:1] + [str(bot)] + shlex.split(x)[1:], check=True)
    (bot / 'FISHBODY.json').write_text(json.dumps({'base': a.base, 'ref': 'r8', 'table': n, 'constants': log,
                                                   'patches': a.patch, 'py': a.py, 'noise': a.noise}, indent=1))
    print(name, n, 'table entries', log)

if __name__ == '__main__': main()
