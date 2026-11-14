"""Diverse-panel bodies (diverse-panel.md): copies of oc-tune3 (= oc-base25 tunified) with other tunings, styles or
per-game noise.   py bodies.py [NAME...]   -> bots/variants/dvp-NAME (own draft; makespar.sh adds live drafts)."""
import json, re, subprocess, sys
from pathlib import Path
R = Path('/home/ubuntu/cambc-autumn'); SRC = 'variants/oc-tune3'
TJ = json.load(open(R / 'bots' / SRC / 'src/tune.json'))
TUNED = [n for n, _ in TJ['floats']] + [n for n, _ in TJ['ints']]
DFL = dict(TJ['floats'] + TJ['ints'])

def oc6(scale):
    """oc6's SPSA iterate: default + scale x (final - default), in its [0,1] range space."""
    c = json.load(open(R / 'replays/tune/oc6/config.json'))['params']
    xf = json.loads(open(R / 'replays/tune/oc6/history.jsonl').readlines()[-1])['x']
    out = {}
    for n, (lo, hi, kind) in c.items():
        xd = (DFL[n] - lo) / (hi - lo); x = min(1, max(0, xd + scale * (xf[n] - xd)))
        out[n] = ('=', lo + (hi - lo) * x)
    return out

STYLES = {  # multipliers on oc-base25's values
    'agg': dict(life_value=.6, hurt_health_fraction=.75, hurt_retreat_ratio=1.5, home_retreat_ratio=1.4, chip_value=1.4,
                tribute_value=1.3, camp_risk=.7, brake_bag=.7, bag_ratio=1.4),
    'pas': dict(life_value=1.6, hurt_health_fraction=1.3, hurt_retreat_ratio=.7, home_retreat_ratio=.75, chip_value=.7,
                camp_risk=1.3, home_power=1.3, finish_camp_health_fraction=.8, bag_ratio=.75),
    'greed': dict(efficiency_power=1.6, pair_hold_share=.7, mid_gold=1.3, min_bank=1.6, life_value=1.2, gem_value=.8,
                  camp_risk=.8),
}

def body(name):
    if name == 'oc6': return oc6(1.0)
    if name == 'anti6': return oc6(-1.5)
    return {k: ('*', v) for k, v in STYLES[name].items()}

def flit(x):
    t = f'{x:.8g}'
    return t + ('' if '.' in t or 'e' in t else '.0') + 'f'

def write(dst, changes):
    subprocess.run([str(R / 'copybot'), '-f', SRC, dst], check=True, capture_output=True)
    d = R / 'bots' / dst / 'src'; th = (d / 'tune.h').read_text(); ph = (d / 'params.h').read_text()
    fl = [v for _, v in TJ['floats']]; it = [v for _, v in TJ['ints']]
    for n, (op, v) in changes.items():
        if n in DFL:
            new = v if op == '=' else DFL[n] * v
            if n in dict(TJ['ints']): it[[k for k, _ in TJ['ints']].index(n)] = max(0, round(new))
            else: fl[[k for k, _ in TJ['floats']].index(n)] = min(new, 0.95) if 'fraction' in n or 'share' in n else new
            continue
        m = re.search(rf'^inline constexpr (float|int) {n} = ([0-9.]+)f?;', ph, re.M); assert m, n
        new = float(m[2]) * v if op == '*' else v
        lit = str(max(0, round(new))) if m[1] == 'int' else flit(new)
        ph = ph[:m.start(2)] + lit + ph[m.end(0) - 1:] if m[1] == 'int' else ph[:m.start(2)] + lit + ';' + ph[m.end(0):]
    th = re.sub(r'\{"DIANA-TUNE-BLK1", \{[^}]*\}, \{[^}]*\}\}',
                '{"DIANA-TUNE-BLK1", {' + ', '.join(flit(x) for x in fl) + '}, {' + ', '.join(map(str, it)) + '}}', th)
    (d / 'tune.h').write_text(th); (d / 'params.h').write_text(ph)

NOISE_H = r'''#pragma once
// Diverse-panel noise body (research/notes/ideas-2026-11-08/diverse-panel.md): every EPOCH rounds the tuned knobs are
// redrawn as default x exp(SD N(0,1)), seeded by (map, team, epoch, member seed), so teammates agree and games replay.
#include <cmath>
#include <cstdint>
#include "tune.h"
namespace dvp {
inline constexpr std::uint64_t member_seed = SEEDu;
inline constexpr float sd = SDf;
inline constexpr unsigned epoch_rounds = EPOCH;
inline std::uint64_t mixw(std::uint64_t h, std::uint64_t w) { h = (h ^ w) * 0x9E3779B97F4A7C15ull; return h ^ (h >> 29); }
inline void apply(unsigned round) {
    static float f0[sizeof(diana_tune.f) / 4]; static int i0[sizeof(diana_tune.i) / 4];
    static std::uint64_t map_h = 0; static unsigned last = ~0u;
    if (!map_h) {
        for (unsigned k = 0; k < sizeof(f0) / 4; ++k) f0[k] = diana_tune.f[k];
        for (unsigned k = 0; k < sizeof(i0) / 4; ++k) i0[k] = diana_tune.i[k];
        std::uint64_t h = mixw(member_seed, static_cast<std::uint64_t>(cambc::detail::sdk_my_team()));
        h = mixw(h, static_cast<std::uint64_t>(cambc::map::width()) << 32 | static_cast<std::uint32_t>(cambc::map::height()));
        const auto& w = cambc::map::walls(); const auto words = cambc::detail::layout().board_bytes / 8;
        for (std::uint32_t k = 0; k < words; ++k) h = mixw(h, w.ptr()[k]);
        map_h = h | 1;
    }
    const unsigned e = round / epoch_rounds;
    if (e == last) return;
    last = e;
    std::uint64_t s = mixw(map_h, e + 1);
    auto gauss = [&] {  // Box-Muller from two 53-bit uniforms
        s = mixw(s, 0x2545F4914F6CDD1Dull); const double u1 = ((s >> 11) + 1.0) / 9007199254740993.0;
        s = mixw(s, 0x2545F4914F6CDD1Dull); const double u2 = (s >> 11) / 9007199254740992.0;
        return static_cast<float>(std::sqrt(-2.0 * std::log(u1)) * std::cos(6.283185307179586 * u2));
    };
    for (unsigned k = 0; k < sizeof(f0) / 4; ++k) {
        const float g = gauss();
        if (k == SKIP1 || k == SKIP2) continue;  // map-conditioned per map (condition_on_map)
        float v = f0[k] * std::exp(sd * g);
        diana_tune.f[k] = (FRACMASK >> k & 1) && v > 0.95f ? 0.95f : v;
    }
    for (unsigned k = 0; k < sizeof(i0) / 4; ++k) {
        const float v = i0[k] * std::exp(sd * gauss());
        diana_tune.i[k] = static_cast<int>(std::lround(v));
    }
}
}
'''

def noise(dst, seed, sd=0.2, epoch=100):
    write(dst, {})
    d = R / 'bots' / dst / 'src'; names = [n for n, _ in TJ['floats']]
    skip = [names.index('recall_health_fraction'), names.index('gold_price_scale')]
    frac = sum(1 << k for k, n in enumerate(names) if 'fraction' in n or 'share' in n)
    h = (NOISE_H.replace('SEEDu', f'{seed}u').replace('SDf', f'{sd}f').replace('EPOCH', str(epoch))
         .replace('SKIP1', str(skip[0])).replace('SKIP2', str(skip[1])).replace('FRACMASK', f'{frac}u'))
    (d / 'dvp_noise.h').write_text(h)
    m = (d / 'main.cc').read_text()
    m = m.replace('#include "util.h"\n', '#include "util.h"\n#include "dvp_noise.h"\n', 1)
    old = '        run("map conditioning", [&] { aph::condition_on_map(world->map()); });\n'
    assert old in m
    m = m.replace(old, old + '        run("dvp noise", [&] { dvp::apply(aph::round_now()); });\n', 1)
    (d / 'main.cc').write_text(m)

if __name__ == '__main__':
    for n in sys.argv[1:]:
        if n.startswith('n'):  # nS[:SD[:EPOCH]] e.g. n1310001:0.2:100
            seed, *rest = n[1:].split(':'); sd = float(rest[0]) if rest else 0.2; ep = int(rest[1]) if len(rest) > 1 else 100
            noise(f'variants/dvp-n{int(seed) - 1310000}', int(seed), sd, ep); print('noise', seed, sd, ep)
        else:
            write(f'variants/dvp-{n}', body(n)); print('body', n)
