"""Build a current-Mite body from one of our bots, in layers, each a patch on the copy:
  1. draft: Mite's picks. On the ladder maps the pin's exact (map, side) table, elsewhere its pick model
     (fitgen_r7.py, sampled with the draft salt); --draft model uses the model on every map.
  2. run time: the draft salt and member seed come from the runner (env.experiment_config), as the rt-* bodies'
     do, so fgate can play it unmetered with a seed a game.
  3. constants: --set NAME=VALUE (params.h inline constexpr) and --mul NAME=FACTOR.
  3b. noise (--noise SD, default 0.2; 0 for none): params.h's tunable constants (tunify.py) are redrawn every 100
     rounds as value x exp(SD N(0,1)), seeded by the member seed, the map and the team, as the dvn bodies do.
  4. rules: --patch FILE (a unified diff against the body's src/, applied with patch -p1 in src/) or --py 'SCRIPT [ARGS]'
     (run as SCRIPT BODY_DIR), in order.
    py mkbody.py NAME [--base variants/c520-ps] [--draft table|model] [--ref r7] [--set K=V]... [--mul K=F]...
                      [--patch F]... [--py S]... [-f]"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path
R = Path('/home/ubuntu/cambc-autumn'); T = R / 'research/ideas-2026-11-08/spar-tools'; FG = R / 'research/ideas-2026-11-09/freshgate-tools'
M = Path.home() / 'tmp-offload/mitefit'
enum = lambda n: n.lower().replace(' & ', '_and_').replace(' ', '_')
RT_H = '''#pragma once
#include <cstdint>
// The runner supplies per-game values before any draft call (key 0 member seed, key 1 draft salt).
extern "C" __attribute__((import_module("env"), import_name("experiment_config")))
std::uint64_t experiment_config(std::uint32_t key);
'''

def table(bot, ref):
    H = json.load(open(T / 'hashes.json')); rows = {}
    for l in open(R / 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
        g = json.loads(l)
        if g.get('opp_name') == 'Mite' and g.get('refset') == ref and g.get('status') == 'finished' and g.get('opp_picks'):
            rows[(g['map'].replace('_', '-'), 'b' if g['side'] == 'a' else 'a')] = g['opp_picks']  # keyed by the side Mite plays
    out = []
    for key, h in sorted(H.items()):
        m, side = key.split(':')
        m = m.replace('_', '-')
        if (m, side) in rows:
            p = rows[(m, side)]
            out.append(f"    {{{h}ull, {len(p)}, {{{', '.join('C::' + enum(x) for x in p)}}}}}, // {m} {side}")
    (bot / 'src/draft/spar_draft.h').write_text(
        f'#pragma once\n// mitefit/mkbody.py: Mite {ref}\'s picks per ladder map and the side it plays.\n#include <cstdint>\n'
        'namespace spar {\nusing C = cambc::champion_draft;\nstruct Entry { std::uint64_t hash; int n; C picks[5]; };\n'
        'inline constexpr Entry table[] = {\n' + '\n'.join(out) + '\n};\n}\n')
    return len(out)

def constant(ph, name, val=None, mul=None):
    m = re.search(rf'^(inline )?constexpr (float|int|double) {name} = ([-0-9.e]+)f?;', ph, re.M)
    assert m, f'{name} not in params.h'
    v = float(m[3]) * mul if mul is not None else float(val)
    lit = str(round(v)) if m[2] == 'int' else (repr(v) + ('f' if m[2] == 'float' else ''))
    return ph[:m.start(3)] + lit + ';' + ph[m.end(0):], (m[3], lit)

NOISE_H = r'''#pragma once
// mitefit body noise (mkbody.py): every 100 rounds the tuned constants are redrawn as default x exp(SD N(0,1)), seeded
// by (member seed, team, map), so teammates agree and games replay.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include "tune.h"
#include "experiment_config.h"
namespace dvp {
inline constexpr float sd = SDVAL;
inline constexpr unsigned epoch_rounds = 100;
inline constexpr bool capped[] = {CAPS};
inline constexpr float floor_[] = {FLOORS};  // hit_given_reach stays above recall_risk (safety.cc's dropped assert)
inline std::uint64_t mixw(std::uint64_t h, std::uint64_t w) { h = (h ^ w) * 0x9E3779B97F4A7C15ull; return h ^ (h >> 29); }
inline void apply(unsigned round) {
    static float f0[sizeof(diana_tune.f) / 4]; static int i0[sizeof(diana_tune.i) / 4];
    static std::uint64_t map_h = 0; static unsigned last = ~0u;
    if (!map_h) {
        for (unsigned k = 0; k < sizeof(f0) / 4; ++k) f0[k] = diana_tune.f[k];
        for (unsigned k = 0; k < sizeof(i0) / 4; ++k) i0[k] = diana_tune.i[k];
        std::uint64_t h = mixw(experiment_config(0), static_cast<std::uint64_t>(cambc::detail::sdk_my_team()));
        h = mixw(h, static_cast<std::uint64_t>(cambc::map::width()) << 32 | static_cast<std::uint32_t>(cambc::map::height()));
        const auto& w = cambc::map::walls(); const auto words = cambc::detail::layout().board_bytes / 8;
        for (std::uint32_t k = 0; k < words; ++k) h = mixw(h, w.ptr()[k]);
        map_h = h | 1;
    }
    const unsigned e = round / epoch_rounds;
    if (e == last) return;
    last = e;
    std::uint64_t s = mixw(map_h, e + 1);
    auto gauss = [&] {
        s = mixw(s, 0x2545F4914F6CDD1Dull); const double u1 = ((s >> 11) + 1.0) / 9007199254740993.0;
        s = mixw(s, 0x2545F4914F6CDD1Dull); const double u2 = (s >> 11) / 9007199254740992.0;
        return static_cast<float>(std::sqrt(-2.0 * std::log(u1)) * std::cos(6.283185307179586 * u2));
    };
    for (unsigned k = 0; k < sizeof(f0) / 4; ++k) {
        const float v = f0[k] * std::exp(sd * gauss());
        diana_tune.f[k] = std::max(floor_[k], capped[k] && v > 0.95f ? 0.95f : v);
    }
    for (unsigned k = 0; k < sizeof(i0) / 4; ++k) diana_tune.i[k] = static_cast<int>(std::lround(i0[k] * std::exp(sd * gauss())));
}
}
'''

KNOBS = ('fight_weight fight_camp_prior life_value gem_value tribute_value recall_value chip_value gold_price_scale mid_gold '
         'hurt_health_fraction hurt_retreat_ratio home_retreat_ratio camp_risk hit_given_reach track_horizon threat_radius '
         'pack_ally_radius hit_steps slack_steps').split()

def noise(bot, sd):
    # The SPSA labs' 19 economy and fight knobs, made tunable as ~/tmp-offload/localq/mktune.sh does.
    src = bot / 'src'
    ph = (src / 'params.h').read_text().replace('\ninline float gold_price_scale = ', '\ninline constexpr float gold_price_scale = ')
    (src / 'params.h').write_text(ph)
    sh = (src / 'model/safety.h').read_text()
    (src / 'model/safety.h').write_text(sh.replace('inline constexpr float hit_given_reach = params::hit_given_reach;', 'inline const float& hit_given_reach = params::hit_given_reach;'))
    sc = (src / 'model/safety.cc').read_text()
    (src / 'model/safety.cc').write_text(sc.replace('static_assert(unknown_camp_weight >= recall_risk && hit_given_reach >= recall_risk);', 'static_assert(unknown_camp_weight >= recall_risk);'))
    subprocess.run([sys.executable, str(R / 'research/diana-2026-11-03/tunify.py'), str(bot)] + KNOBS, check=True, capture_output=True)
    ph = (src / 'params.h').read_text()
    (src / 'params.h').write_text(ph.replace('inline const float& gold_price_scale = diana_tune', 'inline float& gold_price_scale = diana_tune'))
    tj = json.load(open(bot / 'src/tune.json'))
    caps = ', '.join('true' if ('fraction' in n or 'share' in n) else 'false' for n, _ in tj['floats']) or 'false'
    floors = ', '.join('0.21f' if n == 'hit_given_reach' else '0.0f' for n, _ in tj['floats']) or '0.0f'
    (bot / 'src/dvp_noise.h').write_text(NOISE_H.replace('SDVAL', f'{sd}f').replace('CAPS', caps).replace('FLOORS', floors))
    m = bot / 'src/main.cc'; s = m.read_text()
    s = s.replace('#include "bot.h"\n', '#include "bot.h"\n#include "dvp_noise.h"\n', 1)
    old = '        run("map conditioning", [&] { aph::condition_on_map(world->map()); });\n'
    assert s.count(old) == 1
    m.write_text(s.replace(old, old + '        run("dvp noise", [&] { dvp::apply(aph::round_now()); });\n', 1))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('--base', default='variants/c520-ps')
    ap.add_argument('--draft', default='table', choices=['table', 'model']); ap.add_argument('--ref', default='r7')
    ap.add_argument('--set', action='append', default=[]); ap.add_argument('--mul', action='append', default=[])
    ap.add_argument('--patch', action='append', default=[]); ap.add_argument('--py', action='append', default=[])
    ap.add_argument('-f', action='store_true'); ap.add_argument('--noise', type=float, default=0.2)
    ap.add_argument('--static', type=int, help='bake member K (seed 1310000+K, salt K) in: no run-time import, plays metered without a config (tune.py)')
    a = ap.parse_args(); name = f'variants/{a.name}'; bot = R / 'bots' / name
    subprocess.run([str(R / 'copybot')] + (['-f'] if a.f else []) + [a.base, name], check=True, cwd=R, capture_output=True)
    subprocess.run([sys.executable, str(T / 'patch_spar.py'), str(bot)], check=True, capture_output=True)
    n = table(bot, a.ref)
    fm = M / f'fm/fm_draft_M.h'; assert fm.exists(), 'run fitgen_r7.py first'
    tmp = FG / 'fm_draft_M.h'; orig = tmp.read_text()
    try:  # patch_fm.py reads its header from its own dir: lend it ours for the call
        tmp.write_text(fm.read_text()); subprocess.run([sys.executable, str(FG / 'patch_fm.py'), str(bot), 'M', '0'], check=True, capture_output=True)
    finally: tmp.write_text(orig)
    d = bot / 'src/draft/draft.cc'; s = d.read_text()
    if a.draft == 'table':
        s = s.replace('        return fm_forced();\n', '''        const auto h = test_compositions::map_hash();
        for (const auto& e : spar::table)
            if (e.n && e.hash == h && e.n == static_cast<int>(cambc::draft::team_size()))
                return new std::vector<cambc::champion_draft>(e.picks, e.picks + e.n);
        return fm_forced();
''', 1)
    # run time: the salt from the runner
    (bot / 'src/experiment_config.h').write_text(RT_H if a.static is None else
        f'#pragma once\n#include <cstdint>\n// A static member (mkbody.py --static): seed and salt baked in.\n'
        f'inline std::uint64_t experiment_config(std::uint32_t key) {{ return key ? {a.static}u : {1310000 + a.static}u; }}\n')
    f = bot / 'src/draft/fm_draft.h'; h = f.read_text()
    h, k = re.subn(r'inline constexpr std::uint64_t salt = \d+ull;', 'inline std::uint64_t salt() { return experiment_config(1); }', h); assert k == 1
    f.write_text(h.replace('#include <cstdint>', '#include <cstdint>\n#include "../experiment_config.h"', 1))
    assert s.count('fm::salt *') == 1; d.write_text(s.replace('fm::salt *', 'fm::salt() *'))
    # constants
    p = bot / 'src/params.h'; ph = p.read_text(); log = []
    for kv in a.set: k, v = kv.split('='); ph, c = constant(ph, k, val=v); log.append((k, *c))
    for kv in a.mul: k, v = kv.split('='); ph, c = constant(ph, k, mul=float(v)); log.append((k, *c))
    p.write_text(ph)
    if a.noise > 0: noise(bot, a.noise)
    for x in a.patch: subprocess.run(['patch', '-p1', '-i', str(Path(x).resolve())], cwd=bot / 'src', check=True)
    # A --py value may carry the script's arguments after its path: 'rule_vesper.py 0 --build greed-s,greed-h'.
    for x in a.py: q = x.split(); subprocess.run([sys.executable, q[0], str(bot)] + q[1:], check=True)
    (bot / 'MITEBODY.json').write_text(json.dumps({'base': a.base, 'draft': a.draft, 'ref': a.ref, 'table': n, 'constants': log,
                                                   'patches': a.patch, 'py': a.py, 'noise': a.noise, 'static': a.static}, indent=1))
    print(name, n, 'table entries', log)

if __name__ == '__main__': main()
