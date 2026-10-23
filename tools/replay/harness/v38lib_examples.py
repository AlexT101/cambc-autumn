"""Worked examples for tools/replay/harness/v38lib.py on the traced games, written as Markdown.

    py tools/replay/harness/v38lib.py examples [--keys K1,K2] [--out tools/replay/harness/EXAMPLES.md] [--world ladder]
                                       [--detail N]

Sections: data and join checks, (a) deaths with the 5 preceding turns, (b) prediction vs actual damage,
(c) target switching and oscillation, (d) rejected kills in the strike search, (e) gem losses,
(f) ward and bush blindness. Only trusted rounds are used (the trace explains the game there).

One pass over the games, one game in memory at a time (a 2000-round game takes about 220 MB loaded), so it
scales to all 390; a section keeps only compact rows and the few rendered detail blocks it shows.
"""
import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v38lib as L  # noqa: E402

ROUTINE = {("recall", "recall_start"), ("cancel_channel", "recall_keep"), ("set_priority", "priority")}


def fmt_pos(p):
    return "-" if not p or p == (-1, -1) else f"{p[0]},{p[1]}"


def fmt_fight(f):
    if f is None:
        return ""
    if isinstance(f, str):
        return f
    return f"{f.lost}:{f.tku}:{f.tkt}:{'?' if f.falls is None else f.falls}:{f.allies}:{f.enemies}"


def actions(turn):
    out = []
    for a in turn.ta:
        if (a.a, a.s) in ROUTINE:
            continue
        x = a.x
        name = a.a.replace("_with_result", "")
        if name == "move_to":
            s = f"mv {x[0]},{x[1]}"
        elif name == "attack":
            s = f"atk {'e' if x[0] == 1 else 'g' if x[0] == 2 else 'lock'}{x[1]}"
        elif name == "cast":
            s = f"s{x[0]} " + (f"e{x[2]}" if x[1] == 1 else f"g{x[2]}" if x[1] == 2 else f"@{x[3]},{x[4]}")
        elif name == "place_ward":
            s = f"ward {x[0]},{x[1]}"
        elif name == "submit_gems":
            s = "tribute"
        else:
            s = name
        if a.ok == 0:
            s += "(fail)"
        out.append(f"{s}[{a.s}]")
    return " ".join(out)


def home_why(turn):
    h = turn.te_kind("home")
    return ",".join(sorted({str(x.why) for x in h})) if h else ""


def died_between(g, c, r):
    """Our champion c dies after its turn in round r and before its turn in r+1."""
    t0, t1 = g.turn_index(r, c), g.turn_index(r + 1, c)
    for d in g._deaths_all:
        if d.v == c and (r, t0) < (d.r, d.t) < (r + 1, t1 if t1 is not None else 1 << 20):
            return d
    return None


def died_within(g, c, r, rounds):
    for d in g._deaths_all:
        if d.v == c and (d.r > r or d.r == r and d.t > (g.turn_index(r, c) or 0)) and d.r <= r + rounds:
            return d
    return None


def load(key, world):
    g = L.load_game(key, world)
    if not g.traced or not g.has_extract:
        print(f"skip {key}: traced={g.traced} extract={g.has_extract}", file=sys.stderr)
        return None
    g._deaths_all = g.deaths("all")
    return g


class Keep:
    """The n largest items by key (for detail blocks rendered while their game is loaded)."""

    def __init__(self, n):
        self.n, self.items = n, []

    def offer(self, key, make):
        if len(self.items) < self.n or key > self.items[-1][0]:
            self.items.append((key, make()))
            self.items.sort(key=lambda x: x[0], reverse=True)
            del self.items[self.n:]


# ---------------------------------------------------------------- data and joins

class Data:
    def __init__(self):
        self.rows, self.tot = [], Counter()

    def add(self, g):
        ok, bad, _ = g.check_turn_order()
        tt = vis_ok = vis_n = pos_ok = pos_n = dmg_eq = dmg_n = 0
        for t in g.turns(trusted_only=True):
            if not t.tt:
                continue
            tt += 1
            sees = set((g.state(t.r, t.c) or {}).get("sees") or [])
            if t.tt.a:
                for b in t.tb:
                    if b.al:
                        vis_n += 1
                        vis_ok += bool(b.v) == (b.h in sees)
                pos_n += 1
                pos_ok += g.positions_at(t.r, t.t).get(t.c) == t.tt.p
            nx = g._by_rc.get((t.r + 1, t.c), {}).get("TT")
            if nx and g.trusted(t.r + 1):
                dmg_n += 1
                dmg_eq += abs(t.actual - nx[-1].dmg) < 0.6
        deaths = [d for d in g._deaths_all if d.ours]
        self.rows.append(f"| {g.key} | {g.map_name} | {g.our_side} | {g.opponent} | {g.rounds_played} | {g.ladder_trusted_through} | {tt} | "
                         f"{len(deaths)} ({sum(d.trusted for d in deaths)}) | {ok}/{ok + bad} | {vis_ok}/{vis_n} | {pos_ok}/{pos_n} | {dmg_eq}/{dmg_n} |")
        for k, v in (("tt", tt), ("ok", ok), ("bad", bad), ("vis_ok", vis_ok), ("vis_n", vis_n), ("pos_ok", pos_ok), ("pos_n", pos_n),
                     ("dmg_eq", dmg_eq), ("dmg_n", dmg_n), ("deaths", len(deaths)), ("tdeaths", sum(d.trusted for d in deaths))):
            self.tot[k] += v

    def render(self, md):
        tot = self.tot
        md.append("## Data and join checks\n")
        md.append("| key | map | side | opponent | rounds | trusted through | TT turns (trusted) | our deaths (trusted) | turn order vs events | TB `v` vs extract `sees` | TT `p` vs extract | TT `dmg` vs extract damage |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        md.extend(self.rows)
        md.append(f"| **all** | | | | | | {tot['tt']} | {tot['deaths']} ({tot['tdeaths']}) | {tot['ok']}/{tot['ok'] + tot['bad']} | "
                  f"{tot['vis_ok']}/{tot['vis_n']} | {tot['pos_ok']}/{tot['pos_n']} | {tot['dmg_eq']}/{tot['dmg_n']} |\n")
        md.append("- *Turn order vs events*: `Game.turn_order` (team A first in odd rounds, alternating, priority set in a round applying from the next) "
                  "against the turn index `t` of every champion action in the extract.")
        md.append("- *TB `v` vs `sees`*: the trace's belief `v` (visible now) for each living enemy against the extract's `sees` (enemies the engine "
                  "showed that champion at its turn start).")
        md.append("- *TT `p` vs extract*: the trace's turn-start position against `positions_at(r, t)` rebuilt from the extract (alive turns).")
        md.append("- *TT `dmg` vs extract damage*: next turn's `dmg` (health lost) against the extract's damage events between the two turns "
                  "(health plus shield lost). They differ only when a shield absorbed damage or the champion was healed.\n")


# ---------------------------------------------------------------- (a) deaths

def death_block(g, d, before=5):
    md = []
    killer = d.by if isinstance(d.by, int) else None
    md.append(f"#### {g.key} r{d.r}: our {d.victim} (id {d.v}) killed by {d.killer}{f' (id {killer})' if killer is not None else ''}, "
              f"bag {d.gems} gems, assists {d.assists}{', linked' if d.linked is not None else ''}{'' if d.trusted else ' (UNTRUSTED round)'}\n")
    md.append("| r | t | d | p > q | hp | sh | g | dmg | actual after | ls / le | fs / fe | ts | home | actions | killer belief (TB) | killer truth |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in g.window(d.r, d.v, before=before):
        tt = t.tt
        if not tt:
            md.append(f"| {t.r} | {t.t} | (no TT) | | | | | | {t.actual} | | | | | | | |")
            continue
        b = t.belief(killer) if killer is not None else None
        bs = ""
        if b is not None:
            bs = (f"v={b.v} p={fmt_pos(b.p)} src={b.src} pr={b.pr} hp={b.hp[0] if isinstance(b.hp, tuple) else b.hp}"
                  f"{' bu' if b.bu else ''}{f' np={b.np}' if b.np else ''}") if b.al else f"dead rsp={b.rsp}"
        truth = ""
        if killer is not None and tt.a:
            kp = g.positions_at(t.r, t.t).get(killer)
            if kp:
                truth = f"{fmt_pos(kp)} d={L.cheb(kp, tt.p)}{' bush' if kp in g.map['bush_set'] else ''}"
        sh = f"{tt.sh[0]},{tt.sh[1]}" if tt.sh else ""
        md.append(f"| {t.r} | {t.t} | {tt.d} | {fmt_pos(tt.p)} > {fmt_pos(tt.q)} | {tt.hp}>{tt.hq} | {sh} | {tt.g} | {tt.dmg} | {t.actual} | "
                  f"{'' if tt.ls is None else tt.ls} / {'' if tt.le is None else tt.le} | {fmt_fight(tt.fs)} / {fmt_fight(tt.fe)} | {tt.ts or ''} | "
                  f"{home_why(t)} | {actions(t)} | {bs} | {truth} |")
    md.append("")
    return md


def last_turn(g, d):
    win = [t for t in g.window(d.r, d.v, before=5) if t.tt and t.tt.a]
    return win, (win[-1] if win else None)


class Deaths:
    HAND = ("f974cb55-1", 41)

    def __init__(self, detail):
        self.rows, self.linked, self.detail = [], 0, Keep(detail)
        self.hand = None

    def add(self, g):
        for d in g.deaths("us"):
            if not d.trusted:
                continue
            win, last = last_turn(g, d)
            killer = d.by if isinstance(d.by, int) else None
            taken = sum((t.actual or 0) for t in win)
            seen = ""
            if last and killer is not None:
                b = last.belief(killer)
                seen = "yes" if b and b.v else "no"
            tt = last.tt if last else None
            lt = f"{'' if tt.ls is None else tt.ls} / {'' if tt.le is None else tt.le}" if tt else ""
            self.rows.append(f"| {g.key} | {d.r} | {d.victim} | {d.killer} | {d.gems} | {tt.d if tt else ''} | {tt.hq if tt else ''} | "
                             f"{taken:.0f} | {last.actual if last else ''} | {lt} | {(fmt_fight(tt.fs) + ' / ' + fmt_fight(tt.fe)) if tt else ''} | {seen} |")
            self.linked += d.linked is not None
            self.detail.offer((d.gems, g.key, d.r, d.v), lambda: death_block(g, d))
            if (g.key, d.r) == self.HAND:
                self.hand = death_block(g, d)

    def render(self, md):
        md.append("## (a) Our deaths and the 5 turns before\n")
        md.append("One row per death of our champions in trusted rounds (`Game.deaths('us')`); the last turn before it is "
                  "the victim's last living turn (TT `a=1`) at or before the death round. `hp` is its health at that turn's end, "
                  "`killing blow window` the damage it then took before its next turn (the death included), `ls / le` the lethal "
                  "bound at the start / end tile and `fs / fe` the fight sim (`lost:tku:tkt:falls:allies:enemies`) of that turn; "
                  "blank means not evaluated (absent), `?` asked but not evaluated.\n")
        md.append("| key | r | victim | killer | bag | last d | hp | dmg taken in the 5 turns | killing blow window | ls / le | fs / fe | killer seen at last turn |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        md.extend(self.rows)
        md.append(f"\n{len(self.rows)} deaths in trusted rounds; {self.linked} of them linked Cassi/Issac bodies.\n")
        md.append(f"### Detail: the {self.detail.n} largest bags, plus the hand-checked death\n")
        for _, block in self.detail.items:
            md.extend(block)
        if self.hand and self.hand not in [b for _, b in self.detail.items]:
            md.extend(self.hand)


# ---------------------------------------------------------------- (b) calibration

EDGES = [(-1, -1, "-1 (bound < hp)"), (0, 0, "0"), (0.01, 100, "1-100"), (100.01, 300, "101-300"), (300.01, 600, "301-600"), (600.01, 1e9, ">600")]


def bucket(v, edges=EDGES):
    for lo, hi, name in edges:
        if lo <= v <= hi:
            return name
    return "other"


class Calibration:
    PICKS = (("lethal at the end tile (`le`, or `ls` when the champion did not move)", lambda t: t.predicted["lethal"]),
             ("lethal at the start tile (`ls`) whether or not the champion moved", lambda t: t.tt.ls))

    def __init__(self):
        self.tables = [(defaultdict(list), []) for _ in self.PICKS]
        self.cells, self.n_q = defaultdict(list), 0
        self.ts = defaultdict(list)

    def add(self, g):
        for t in g.turns(trusted_only=True):
            if not t.tt or not t.tt.a or not t.tt.ok:
                continue
            a = t.actual
            if a is None:
                continue
            died = died_between(g, t.c, t.r) is not None
            hq = t.tt.mh if g.on_spawn(t.tt.q) else t.tt.hq
            for (title, pick), (rows, misses) in zip(self.PICKS, self.tables):
                v = pick(t)
                if v is None:
                    continue
                rows[bucket(v)].append((v, a, died, hq))
                if v == -1 and a >= hq:
                    misses.append(f"{g.key} r{t.r} c{t.c} ({t.tt.t}): hp {hq}, actual {a}{', died' if died else ''}, d={t.tt.d}, p={fmt_pos(t.tt.p)} q={fmt_pos(t.tt.q)}")
            f = t.predicted["fight"]
            if f == "none":
                key = ("none", "-")
            elif isinstance(f, L.Fight):
                key = (f.lost, "?" if f.falls is None else f.falls)
            else:
                self.n_q += 1
                key = None
            if key:
                self.cells[key].append((a, died, died_within(g, t.c, t.r, 3) is not None))
            if t.tt.p == t.tt.q and t.tt.d not in ("H",):
                self.ts[t.tt.ts or 0].append(a)

    def render(self, md):
        md.append("## (b) Predicted vs actual damage\n")
        md.append("Per trusted, completed (`ok` not 0) turn of a living champion: the prediction made at the end of its turn against the damage it took "
                  "(health plus shield) before its next turn, from the extract. `lethal` is the worst case (every credible threat at "
                  "full damage plus camps); -1 means the cheap bound proved it below our health.\n")
        for (title, _), (rows, misses) in zip(self.PICKS, self.tables):
            md.append(f"**{title}**\n")
            md.append("| predicted | turns | mean predicted | mean actual | P(actual > 0) | P(actual > predicted) | P(died before next turn) | max actual |")
            md.append("|---|---|---|---|---|---|---|---|")
            for _, _, name in EDGES:
                x = rows.get(name)
                if not x:
                    md.append(f"| {name} | 0 | | | | | | |")
                    continue
                n = len(x)
                over = sum(1 for v, a, _, hq in x if (a > v if v >= 0 else a >= hq))
                md.append(f"| {name} | {n} | {sum(v for v, *_ in x) / n:.0f} | {sum(a for _, a, *_ in x) / n:.1f} | {sum(a > 0 for _, a, *_ in x) / n:.3f} | "
                          f"{over / n:.3f} | {sum(d for *_, d, _ in x) / n:.4f} | {max(a for _, a, *_ in x):.0f} |")
            md.append("")
            if misses:
                md.append(f"Turns where the bound said non-lethal (-1) but the damage reached the champion's health ({len(misses)}):\n")
                md.extend(f"- {m}" for m in misses[:12])
                md.append("")
        md.append("For `-1` the 'actual > predicted' column counts actual damage at least the champion's end health (the bound said it "
                  "could not be lethal); on our own spawn that health is the maximum, as the turn-end heal follows the TT.\n")
        md.append("**Fight sim at the end tile (`fe`, or `fs` when the champion did not move) vs outcome**\n")
        md.append("| lost | falls | turns | P(actual > 0) | mean actual | P(died before next turn) | P(died within 3 rounds) |")
        md.append("|---|---|---|---|---|---|---|")
        for key in sorted(self.cells, key=str):
            x = self.cells[key]
            n = len(x)
            md.append(f"| {key[0]} | {key[1]} | {n} | {sum(a > 0 for a, *_ in x) / n:.3f} | {sum(a for a, *_ in x) / n:.1f} | "
                      f"{sum(d for _, d, _ in x) / n:.4f} | {sum(w for *_, w in x) / n:.4f} |")
        md.append(f"\n{self.n_q} alive trusted turns had no usable fight value (`?`, absent, or moved with `fe` not evaluated).\n")
        md.append("**`ts` (threatened at the start tile) vs damage, turns that did not move**\n")
        md.append("| ts | turns | P(actual > 0) | mean actual |")
        md.append("|---|---|---|---|")
        for k in sorted(self.ts):
            x = self.ts[k]
            md.append(f"| {k} | {len(x)} | {sum(a > 0 for a in x) / len(x):.3f} | {sum(x) / len(x):.1f} |")
        md.append("")


# ---------------------------------------------------------------- (c) oscillation

def primary_target(turn):
    for a in turn.ta:
        if a.a == "attack" and a.x and a.x[0] == 1:
            return a.x[1]
        if a.a == "cast_with_result" and len(a.x) >= 3 and a.x[1] == 1:
            return a.x[2]
    return None


class Oscillation:
    def __init__(self):
        self.c = Counter()
        self.ex = defaultdict(list)

    def example(self, kind, text):
        if len(self.ex[kind]) < 8:
            self.ex[kind].append(text)

    def add(self, g):
        dead_at = defaultdict(list)
        for d in g._deaths_all:
            dead_at[d.v].append(d.r)
        for c in g.ours:
            seq = [t for t in g.turns(c, trusted_only=True) if t.tt and t.tt.a]
            tg = [(t.r, primary_target(t)) for t in seq]
            for i in range(1, len(tg)):
                (r0, a), (r1, b) = tg[i - 1], tg[i]
                if a is not None and b is not None and r1 == r0 + 1:
                    self.c["att"] += 1
                    if a != b:
                        self.c["sw"] += 1
                        self.c["sw_alive"] += not any(r0 <= x <= r1 for x in dead_at[a])
                if i >= 2:
                    rp, z = tg[i - 2]
                    if z is not None and a is not None and b is not None and r1 == r0 + 1 == rp + 2 and z == b and a != b:
                        self.c["osc"] += 1
                        self.example("osc", f"{g.key} c{c} r{rp}-{r1}: e{z} > e{a} > e{b}")
            run = 1
            for i in range(2, len(seq)):
                t0, t1, t2 = seq[i - 2], seq[i - 1], seq[i]
                if (t2.r == t1.r + 1 == t0.r + 2 and t0.tt.q == t2.tt.q and t1.tt.q != t2.tt.q and t1.tt.q == t1.tt.p == t0.tt.q
                        or t2.r == t1.r + 1 == t0.r + 2 and t2.tt.q == t1.tt.p and t1.tt.q == t0.tt.p and t1.tt.q != t1.tt.p and t2.tt.q != t2.tt.p):
                    run += 1
                    if run == 3:
                        self.c["ping"] += 1
                        self.example("ping", f"{g.key} c{c} r{t0.r}-{t2.r}: {fmt_pos(t0.tt.p)} > {fmt_pos(t0.tt.q)} > {fmt_pos(t1.tt.q)} > "
                                             f"{fmt_pos(t2.tt.q)} (d {t0.tt.d}{t1.tt.d}{t2.tt.d})")
                else:
                    run = 1
            fb = []
            for t in seq:
                f = t.te_kind("farm")
                fb.append((t.r, f[-1].best if f else None))
            for i in range(3, len(fb)):
                w = fb[i - 3:i + 1]
                if all(x[1] is not None and x[1] >= 0 for x in w) and w[3][0] - w[0][0] == 3 and w[0][1] == w[2][1] and w[1][1] == w[3][1] and w[0][1] != w[1][1]:
                    self.c["farm"] += 1
                    self.example("farm", f"{g.key} c{c} r{w[0][0]}-{w[3][0]}: groups {'/'.join(str(x[1]) for x in w)}")

    def render(self, md):
        c = self.c
        md.append("## (c) Target switching and oscillation\n")
        md.append("Per champion over consecutive trusted rounds: the primary enemy-champion target (first attack or unit cast at a champion, "
                  "from TA), the end tile (TT `q`) and the farm choice (TE farm `best`).\n")
        md.append(f"- Consecutive-round pairs where both turns hit an enemy champion: {c['att']}; the target changed in {c['sw']} "
                  f"({c['sw_alive']} while the previous target was still alive); A > B > A in three consecutive rounds: {c['osc']}.")
        md.extend(f"  - {e}" for e in self.ex["osc"])
        md.append(f"- Tile ping-pong (the end tile alternating between two tiles over 3+ consecutive turns, moving each turn): {c['ping']} runs.")
        md.extend(f"  - {e}" for e in self.ex["ping"])
        md.append(f"- Farm choice A/B/A/B over 4 consecutive turns: {c['farm']} windows.")
        md.extend(f"  - {e}" for e in self.ex["farm"])
        md.append("\nA switch is not necessarily wrong (a kill on the other target, a target leaving range); these are candidates to inspect "
                  "with `g.window(r, c)`.\n")


# ---------------------------------------------------------------- (d) kills and stuns

class Kills:
    def __init__(self):
        self.stats = Counter()
        self.rej = {"kill": [], "stun": []}

    def add(self, g):
        idx = {h: i for i, h in g.enemy_index().items()}
        for t in g.turns(trusted_only=True):
            if not t.tt or not t.tt.a or not t.ts:
                continue
            ev = t.events
            for ts in t.ts:
                for what, entries, mask in (("kill", ts.kill or {}, ts.kl or 0), ("stun", ts.stun or {}, (ts.rm or 0) & ~(ts.kl or 0))):
                    for h, (val, tile) in entries.items():
                        i = idx.get(h)
                        if i is not None and mask >> i & 1:
                            if what == "kill":
                                done = any(e["k"] == "death" and e.get("v") == h for e in ev)
                                self.stats[("kill", "chosen", "killed that turn" if done else "not killed that turn")] += 1
                            else:
                                done = any(h in (e.get("stun") or ()) for e in ev)
                                self.stats[("stun", "chosen", "stunned that turn" if done else "not stunned that turn")] += 1
                            continue
                        later = [d for d in g._deaths_all if d.v == h and (d.r == t.r and d.t > t.t or t.r < d.r <= t.r + 3)]
                        self.stats[(what, "rejected", "enemy died within 3 rounds" if later else "enemy survived 3 rounds")] += 1
                        self.rej[what].append((g.key, t.r, t.c, t.tt.t, h, val, ts.tot, ts.raw, tile, ts.ch, bool(later),
                                               any(isinstance(d.by, int) and g.champions[d.by]["ours"] for d in later), t.tt.hq, t.actual))

    def render(self, md):
        md.append("## (d) Kills and stuns the strike search found but did not take\n")
        md.append("Each TS line lists, per enemy handle, the best plan that kills it (`kill=`) and the best that removes it by a stun "
                  "without killing it (`stun=`): that plan's value before expected damage, and its end tile. The chosen plan's "
                  "`kl` mask (enemy indices) holds what it kills and `rm` what it kills or stuns. An enemy in `kill` but not in "
                  "`kl` is a kill that was considered and rejected; an enemy in `stun` but not in `rm` a rejected stun. The plan "
                  "assumes its hits land, so a listed kill is not a proof the kill was guaranteed.\n")
        md.append("| list | plan | outcome | entries |")
        md.append("|---|---|---|---|")
        for k in sorted(self.stats):
            md.append(f"| {k[0]} | {k[1]} | {k[2]} | {self.stats[k]} |")
        md.append("\n'that turn' is checked against the extract: a `death` of that enemy, or its id in a `stun` list, among the "
                  "champion's own turn events.\n")
        for what in ("kill", "stun"):
            rows = sorted(self.rej[what], key=lambda x: -(x[5] - x[6]))
            md.append(f"Rejected {what}s ({len(rows)}), by plan value minus chosen `tot` (top 20):\n")
            if not rows:
                continue
            md.append("| key | r | c | type | enemy | plan value | chosen tot | chosen raw | its tile | chosen tile | enemy died within 3 | by us | our hp | dmg after |")
            md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
            for k, r, c, ty, h, val, tot, raw, tile, ch, died, by_us, hp, act in rows[:20]:
                md.append(f"| {k} | {r} | {c} | {ty} | {h} | {val} | {tot} | {raw} | {fmt_pos(tile)} | {fmt_pos(ch)} | {'yes' if died else ''} | "
                          f"{'yes' if by_us else ''} | {hp} | {act} |")
            md.append("")
        md.append("The plan value is before expected damage and `tot` after it, so a large gap is the damage the search expected to "
                  "take at that tile; level-2 traces (TQ/TF) show the threat values behind it.\n")


# ---------------------------------------------------------------- (e) gems

class Gems:
    def __init__(self):
        self.rows, self.camp_kills = [], 0

    def add(self, g):
        for d in g.deaths("us"):
            if not d.trusted:
                continue
            self.camp_kills += bool(d.camp)
            if d.gems <= 0:
                continue
            _, last = last_turn(g, d)
            tt = last.tt if last else None
            dist = min((L.cheb(tt.q, tuple(a)) for a in g.map["altars"]), default=None) if tt else None
            carry = last.te_kind("carry") if last else []
            cs = f"safe={carry[-1].safe} close={carry[-1].close}" if carry else ""
            line = (f"| {g.key} | {d.r} | {d.victim} | {d.killer} | {d.gems} | {tt.d if tt else ''} | {tt.bk or '' if tt else ''} | "
                    f"{':'.join(map(str, tt.chq or tt.ch or ())) if tt else ''} | {dist if dist is not None else ''} | {cs} | {home_why(last) if last else ''} |")
            self.rows.append((d.gems, bool(d.camp), line))

    def render(self, md):
        rows = sorted(self.rows, key=lambda x: -x[0])
        camp = [x for x in rows if x[1]]
        md.append("## (e) Gem losses\n")
        md.append("Our deaths in trusted rounds with a bag (extract `death.gems`), and camp kills (gems lost to nobody).\n")
        md.append(f"- Deaths with gems: {len(rows)}, {sum(x[0] for x in rows)} gems; to champions {len(rows) - len(camp)} "
                  f"({sum(x[0] for x in rows if not x[1])} gems handed to the killer), to camps {len(camp)} ({sum(x[0] for x in camp)} gems destroyed).")
        md.append(f"- All camp kills of ours in trusted rounds: {self.camp_kills}.\n")
        md.append("Columns from the victim's last living turn: `d`, `bk` (banking), channel at its end, Chebyshev distance from its end "
                  "tile to the nearest altar, the TE carry line and TE home reasons.\n")
        md.append("| key | r | victim | killer | gems | last turn d | bk | channel | dist to nearest altar | carry TE | home why |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|")
        md.extend(x[2] for x in rows)
        md.append("")


# ---------------------------------------------------------------- (f) blindness

def blind_example(g, d, last, kp):
    md = [f"### Example: {g.key} r{d.r}, our {d.victim} (id {d.v}) killed by {d.killer} (id {d.by})\n",
          f"At its last turn (r{last.r}) our champion stood at {fmt_pos(last.tt.p)}; the killer was really at {fmt_pos(kp)} "
          f"(distance {L.cheb(kp, last.tt.p)}, a bush tile). The trace's beliefs about the killer over the window:\n", "```"]
    for t in g.window(d.r, d.v, before=5):
        if t.tt:
            md.append(t.tt.line)
        b = t.belief(d.by)
        if b:
            md.append(b.line)
        if t.tt and t.tt.a:
            tp = g.positions_at(t.r, t.t).get(d.by)
            md.append(f"# truth r{t.r} t{t.t}: killer at {fmt_pos(tp)}{' (bush)' if tp in g.map['bush_set'] else ''}, "
                      f"distance {L.cheb(tp, t.tt.p) if tp else '-'}")
        md.extend(a.line for a in t.ta if a.ok == 0)
    md.append("```\n")
    md.append("`ok=0` TA lines are hidden blockers: an action onto a tile holding an unseen unit.\n")
    return md


class Blind:
    def __init__(self):
        self.cls, self.base, self.hb = Counter(), Counter(), Counter()
        self.win_bush = self.to_champs = 0
        self.example = Keep(1)

    def add(self, g):
        bushes = g.map["bush_set"]
        for d in g.deaths("us"):
            if not d.trusted:
                continue
            _, last = last_turn(g, d)
            if isinstance(d.by, int):
                self.to_champs += 1
                for t in g.window(d.r, d.v, before=5):
                    b = t.belief(d.by)
                    kp = g.positions_at(t.r, t.t).get(d.by) if t.tt and t.tt.a else None
                    if b and kp and not b.v and L.cheb(kp, t.tt.p) <= 8 and kp in bushes:
                        self.win_bush += 1
                        break
            if not isinstance(d.by, int) or not last or not last.tt:
                self.cls["camp or no turn"] += 1
                continue
            b = last.belief(d.by)
            kp = g.positions_at(last.r, last.t).get(d.by)
            if b is None or kp is None:
                self.cls["killer dead or unknown at that turn"] += 1
                continue
            if b.v:
                k = "seen"
            elif L.cheb(kp, last.tt.p) > 8:
                k = "unseen, out of range"
            elif kp in bushes:
                k = "unseen, within 8, killer in a bush"
                self.example.offer((d.gems, g.key, d.r), lambda: blind_example(g, d, last, kp))
            else:
                k = "unseen, within 8, not on a bush tile (walls or bushes in between)"
            self.cls[k] += 1
        for t in g.turns(trusted_only=True):
            for a in t.ta:
                if a.ok == 0 and a.rc == 0:
                    self.hb[a.a] += 1
            if not t.tt or not t.tt.a:
                continue
            pos = g.positions_at(t.r, t.t)
            for b in t.tb:
                kp = pos.get(b.h)
                if kp is None or L.cheb(kp, t.tt.p) > 8:
                    continue
                self.base[("bush" if kp in bushes else "open", "seen" if b.v else "unseen", "we in bush" if t.tt.bu else "")] += 1

    def render(self, md):
        md.append("## (f) Ward and bush blindness\n")
        md.append("For each trusted death by an enemy champion: was the killer visible (TB `v`) at the victim's last turn before the death, "
                  "and where was it really (`positions_at` at that turn's start)? `within 8` is the 17x17 sight square; unseen inside "
                  "it means occlusion (bush or wall shadow), not range.\n")
        md.append("| killer at the victim's last turn | deaths |")
        md.append("|---|---|")
        for k, v in self.cls.most_common():
            md.append(f"| {k} | {v} |")
        md.append(f"\nDeaths whose killer was unseen on a bush tile within 8 at any of the victim's 5 turns before: {self.win_bush} of "
                  f"{self.to_champs} deaths to champions.\n")
        md.append("Base rate over every trusted living turn: living enemies within 8 of our champion, by whether the enemy stood on a bush "
                  "tile, whether it was seen (TB `v`), and whether our champion stood in a bush (TT `bu`):\n")
        md.append("| enemy tile | seen | our champion | turn-enemy pairs |")
        md.append("|---|---|---|---|")
        for k in sorted(self.base):
            md.append(f"| {k[0]} | {k[1]} | {k[2] or 'not in a bush'} | {self.base[k]} |")
        md.append("")
        for _, block in self.example.items:
            md.extend(block)
        md.append(f"Hidden-blocker failures (TA `ok=0 rc=0`) in trusted turns: {dict(self.hb)}.\n")


# ---------------------------------------------------------------- hand check

class HandCheck:
    KEY, ROUND = "f974cb55-1", 41

    def __init__(self):
        self.md = []

    def add(self, g):
        if g.key != self.KEY:
            return
        d = next((x for x in g.deaths("us") if x.r == self.ROUND), None)
        if d is None:
            return
        md = self.md
        md.append(f"## Hand check: {self.KEY} r{self.ROUND}\n")
        md.append("The raw trace lines and extract events behind one death, so the parsed numbers above can be checked against the "
                  "data. For each turn of the victim: its TT line, then every damage event the extract has between that turn and "
                  "the next (round, turn index, attacker, amount), their sum (`Turn.actual`), and the next TT's `dmg`.\n")
        md.append("```")
        for t in g.window(d.r, d.v, before=5):
            if not t.tt:
                continue
            md.append(t.tt.line)
            t1 = g.turn_index(t.r + 1, t.c)
            evs = g.damage_events(t.c, (t.r, t.t), (t.r + 1, t1 if t1 is not None else 1 << 20))
            nx = g.turn(t.r + 1, t.c).tt
            md.append(f"#   events after it: {[(r, tt, src, amt) for r, tt, src, amt, _ in evs]} sum {t.actual}; "
                      f"next TT dmg={nx.dmg if nx else '-'}{' (shield sh=' + str(t.tt.sh) + ' absorbed the rest)' if t.tt.sh and nx and t.actual != nx.dmg else ''}")
        md.append(f"#   death event: {d.event}")
        md.append("```\n")

    def render(self, md):
        md.extend(self.md)



NOTES = """## What the data does and does not support

Numbers quoted here are from the 16-game run of 2026-10-23 (agent A's final recorder, agent B's final tracer); the
tables above are regenerated, these notes are not.

- **Sample.** 16 traced games: 6 picked for out-of-fuel rollovers plus every 39th manifest key. They are not a random
  sample of the 390, and games of one ladder group share bots and maps, so rates here are descriptive only.
  Re-run this file after the full trace batch.
- **Trust.** Only rounds through `ladder_trusted_through` are used. Three games diverge from the ladder (1c870553-3
  after r45, b0a77e05-2 after r199, eb003a5a-1 after r683; all three among the recorder's 21 divergences), so 38 of
  the 185 deaths of ours in these games are left out. `--world rerun` uses the traced run's own replay instead,
  which the trace always matches, but after the divergence the opponent puppet replays the ladder blindly.
- **Joins are exact.** The data table: turn order from the rules reproduces every action's turn index; TB `v`
  equals the engine's `sees` for every belief; TT `p` equals the extract's position on every turn but 8, each the
  turn after one that ran out of fuel (the stale turn's actions land at the start of the next, see README.md).
- **`dmg` vs damage.** TT `dmg` is health lost since the end of the previous turn: shields hide damage (Heart of
  Ruin), and on our own spawn the turn-end heal happens after `hq` is read, so `dmg` under-reports there.
  `Turn.actual` (extract damage events, health plus shield) is the comparable quantity.
- **Predictions are sparse.** `fe` (fight at the end tile) is almost always `?`; `fs` and `ls` describe the start
  tile. The calibration tables therefore use the end tile only when the champion did not move. Lethal values above
  0 are rare (a few hundred turns), so their rates are noisy.
- **`lethal` is a worst case over credible threats.** 10-16% of turns with a predicted worst case of 0 or 1-100
  took more than predicted; which threats it leaves out (unseen enemies, enemies judged unable to reach) is not
  in the trace, so these are leads, not proven bugs. The `-1` misses are listed for inspection.
- **Kills and stuns** (section d) are now separate in the trace (`kl`, `kill=`, `stun=`). Every chosen kill (111)
  killed that turn and every chosen stun (297) stunned; only 3 kills and 32 stuns were considered and rejected.
- **Oscillation detectors are heuristics**: a switch or ping-pong can be correct (kiting, a target leaving range).
- **Blindness** is judged at turn start against true positions; it says the killer was hidden, not that seeing it
  would have changed the decision.
- **Hand check.** The f974cb55-1 r41 death was checked by hand against the raw lines of the final trace on
  2026-10-23: the damage events read from `events.jsonl.gz` (55+55+45+45+70+70 = 340 after r37, 150 of it into
  Heart of Ruin's shield, so TT r38 `dmg=190`; then 100; then 270; then the 30-damage killing blow by Marcella,
  id 9, at r41 t1), the TB line of r40 for id 9 (`v=1 p=24,19 hp=1063/1200`, true position 24,19), and the
  blocked move to 25,19 at r40 (TA `ok=0`, extract `blocked`), where the enemy Vesper (id 8) stood unseen in a
  bush, all match the tables above.
"""




def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--world", default="ladder")
    ap.add_argument("--detail", type=int, default=6, help="deaths shown with their full 5-turn window")
    args = ap.parse_args(argv)
    t0 = time.time()
    keys = [k for k in args.keys.split(",") if k] or L.traced_keys()
    sections = [Data(), Deaths(args.detail), Calibration(), Oscillation(), Kills(), Gems(), Blind(), HandCheck()]
    n = 0
    for k in keys:
        g = load(k, args.world)
        if g is None:
            continue
        n += 1
        for s in sections:
            s.add(g)
        del g
        print(f"[{n}] {k} ({time.time() - t0:.0f} s)", file=sys.stderr, flush=True)
    md = [f"# v38 replay harness: worked examples\n",
          f"Generated by `py tools/replay/harness/v38lib.py examples` on {n} traced games ({args.world} world), trusted rounds only. "
          "See [README.md](README.md) for the data and its caveats.\n"]
    for s in sections:
        s.render(md)
    if not args.keys:
        md.append(NOTES)
    md.append(f"_Run time {time.time() - t0:.0f} s._\n")
    text = "\n".join(md) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(text)} bytes) in {time.time() - t0:.0f} s")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
