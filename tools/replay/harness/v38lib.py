"""Loader for the v38 top-20 replay harness: the joined view per game, round and champion turn.

    import sys; sys.path.insert(0, "tools/replay/harness"); import v38lib as L
    g = L.load_game("f974cb55-1")             # world="ladder" (default) or "rerun"
    for d in g.deaths("us"):
        for t in g.window(d.r, d.v, before=5):
            print(t.r, t.tt and t.tt.d, t.predicted, t.actual)

    py tools/replay/harness/v38lib.py summary [--all]  # data available per (traced) game
    py tools/replay/harness/v38lib.py extract-check [K1,K2]   # ladder vs re-run extract of the traced games
    py tools/replay/harness/v38lib.py examples [--keys K1,K2] [--out FILE]

Sources, per game key `<group8>-<position>` (replays/v38-top20/):
  manifest.json                         the ladder game (map, side, opponent, result)
  runs/batch/<key>/validation.json      release and recorder re-runs vs the ladder (agent A)
  runs/batch/<key>/trace_validation.json, trace.stdout.gz   the trace and its validation (agent B)
  extract/ladder|rerun/                 extract.mjs output (tools/replay/harness/extract_all.py)

World: "ladder" pairs the trace with the ladder replay's extract, which it explains only through
`ladder_trusted_through`; "rerun" pairs it with the traced run's own replay (trace.repl26a), which
it always matches (exact_vs_rec), but after that round the opponent puppet replays the ladder blindly.

Trace records are `Rec` dicts (attribute access too) typed per
tools/replay/harness/trace-bot/TRACE_SCHEMA.md: positions are (x, y) tuples, `a/b` and `a,b`
pairs tuples, fight summaries `Fight`, `?` stays the string "?" and `none` the string "none".
Standard library only; `to_frame` needs pandas.
"""
import gzip
import json
import re
import sys
from bisect import bisect_left
from collections import defaultdict, namedtuple
from functools import cached_property, lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
V38 = REPO / "replays/v38-top20"
BATCH = V38 / "runs/batch"
EXTRACT = V38 / "extract"
WORLDS = {"ladder": "ladder", "rerun": "rerun"}

CHAMP_SHORT = {"Ryth": "ryth", "Vesper Vale": "vesper", "Vendetta": "vendetta", "Cassi": "cassi", "Issac": "issac",
               "Stellar": "stellar", "Prism": "prism", "Marcella": "marcella", "Willow": "willow", "Ren": "ren",
               "Varg": "varg", "Tavi": "tavi", "Heart of Ruin": "hor"}

Fight = namedtuple("Fight", "lost tku tkt falls allies enemies")
Fight.__doc__ = "Fight summary T: lost (they win striking first), tku/tkt (their/our turns to kill, 0 = not within the horizon), falls (our champion falls first, None if not asked), fighter counts."

# Events that happen in the actor's own turn (cancels too when `cause` is manual).
OWN_TURN_EVENTS = {"move", "blocked", "attack", "cast", "ward", "shop", "sell", "consumable", "recall_start", "recall_end",
                   "tribute_start", "tribute_end", "tribute_blocked", "lock_place", "teleport_start", "teleport_end", "respawn"}


# Turn-start timers, resolved before the bot runs (rounds.turn_start).
TURN_START_EVENTS = {"respawn", "recall_end", "teleport_end"}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


# ---------------------------------------------------------------- trace parsing

_INT = re.compile(r"-?\d+$")
_FLOAT = re.compile(r"-?(\d+\.\d*|\.\d+|\d+)([eE]-?\d+)?$")
_POS = re.compile(r"-?\d+,-?\d+$")


def _num(s):
    if _INT.match(s):
        return int(s)
    if _FLOAT.match(s):
        return float(s)
    return s


def _fight(s):
    if s in ("?", "none"):
        return s
    p = s.split(":")
    if len(p) != 6:
        return s
    return Fight(*(None if x == "?" else int(x) for x in p))


def _pair(s, sep, conv=_num):
    a, b = s.split(sep, 1)
    return conv(a), conv(b)


def _seq(s):
    """TS seq: [{op, slot?, target?: (kind, id), tile?}]; kind 'e' enemy handle, 'g' (group, member), 'a' ally."""
    if s in ("-", ""):
        return []
    out = []
    for a in s.split("|"):
        tile = None
        if "@" in a:
            a, t = a.split("@", 1)
            tile = tuple(map(int, t.split(",")))
        tgt = None
        if ":" in a:
            a, t = a.split(":", 1)
            kind, rest = t[0], t[1:]
            tgt = (kind, tuple(map(int, rest.split("."))) if kind == "g" else int(rest))
        act = {"op": a}
        if a.startswith("s") and a[1:].isdigit():
            act = {"op": "s", "slot": int(a[1:])}
        if tgt:
            act["target"] = tgt
        if tile:
            act["tile"] = tile
        out.append(act)
    return out


def _alt(s):
    """TS alt: [{tile, total, rm, kl, exact}] (schema 1 before the kl split had no kl: None)."""
    out = []
    for x in filter(None, s.split(";")):
        p = x.split(":")
        tile, tot, rm, exact = p[0], p[1], p[2], p[-1]
        kl = int(p[3], 16) if len(p) == 5 else None
        out.append({"tile": tuple(map(int, tile.split(","))), "total": float(tot), "rm": int(rm, 16), "kl": kl, "exact": int(exact)})
    return out


def _kill(s):
    out = {}
    if s in ("-", ""):
        return out
    for x in s.split(";"):
        h, v, tile = x.split(":")
        out[int(h)] = (float(v), tuple(map(int, tile.split(","))))
    return out


def _cand(s):
    return [tuple(_num(y) for y in x.split(":")) for x in filter(None, s.split(";"))]


def _generic(v):
    if v in ("?", "none", "-", ""):
        return v
    if _POS.match(v):
        return tuple(map(int, v.split(",")))
    n = _num(v)
    if not isinstance(n, str):
        return n
    for sep in ("/", ","):
        if sep in v:
            parts = v.split(sep)
            conv = [_num(x) for x in parts]
            if all(not isinstance(x, str) for x in conv):
                return tuple(conv)
    m = re.match(r"(\d+)-(\d+)$", v)
    if m:
        return int(m.group(1)), int(m.group(2))
    if ":" in v:
        a, b = v.split(":", 1)
        return a if not _INT.match(a) else int(a), _num(b)
    return v


_SPECIAL = {
    ("TT", "fs"): _fight, ("TT", "fe"): _fight, ("TE", "t"): _fight, ("TF", "t"): _fight,
    ("TT", "ch"): lambda v: _pair(v, ":"), ("TT", "chq"): lambda v: _pair(v, ":"), ("TB", "ch"): lambda v: _pair(v, ":"),
    ("TT", "wa"): lambda v: _pair(v, ":"),
    ("TB", "rsp"): lambda v: v if v == "now" else _pair(v, "-"),
    ("TA", "x"): lambda v: [] if v == "-" else [int(x) for x in v.split(",")],
    ("TS", "rm"): lambda v: int(v, 16), ("TS", "kl"): lambda v: int(v, 16), ("TS", "seq"): _seq, ("TS", "alt"): _alt,
    ("TS", "kill"): _kill, ("TS", "stun"): _kill,
    ("TE", "cand"): _cand, ("TE", "key"): lambda v: int(v, 16), ("TF", "key"): lambda v: int(v, 16),
    ("TE", "why"): str, ("TE", "k"): str, ("TA", "a"): str, ("TA", "s"): str, ("TT", "d"): str, ("TT", "t"): str,
    ("TB", "t"): str, ("TB", "s"): str, ("TB", "src"): str, ("TV", "t"): str, ("TV", "team"): str, ("TV", "game"): str,
    ("TV", "win"): lambda v: _pair(v, "-"),
}


class Rec(dict):
    """One trace line: dict of typed fields plus `tag` and `raw`. Missing optional fields read as None."""
    __slots__ = ("tag", "line")

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            if k.startswith("__"):
                raise AttributeError(k)
            return None

    def __repr__(self):
        return f"<{self.line}>"


TAGGED = ("TV", "TT", "TB", "TA", "TS", "TE", "TF", "TQ")


def parse_line(line):
    """A trace line as a Rec, or None for an empty line. T* lines are key=value; @ harness lines and the
    bot's own debug lines (D, SRCH, FSEED, ...) get positional fields (`args`) and, when their first two
    fields are integers, `r` and `c` (round and champion), as v38's debug lines put them first."""
    p = line.split()
    if not p:
        return None
    rec = Rec()
    rec.tag, rec.line = p[0], line
    tag = p[0]
    if tag in TAGGED:
        for kv in p[1:]:
            k, _, v = kv.partition("=")
            f = _SPECIAL.get((tag, k))
            rec[k] = f(v) if f else _generic(v)
        if tag == "TT":
            rec["a"] = bool(rec.get("a"))
            rec["ok"] = rec.get("ok", 1)
        return rec
    args = [_num(x) for x in p[1:]]
    rec["args"] = args
    if tag == "@v":
        rec.update(c=args[0], seg=args[1], r=args[2], calls=args[3], hash=args[4])
    elif tag == "@o":
        rec.update(c=args[0], seg=args[1], idx=args[2], r=args[3], after=len(args) > 4)
    elif tag == "@!":
        rec.update(kind=args[0], c=args[1] if len(args) > 1 else None)
    elif len(args) >= 2 and isinstance(args[0], int) and isinstance(args[1], int):
        rec.update(r=args[0], c=args[1])
    return rec


def parse_trace(path):
    """All records of a trace.stdout(.gz), in file order."""
    op = gzip.open if str(path).endswith(".gz") else open
    out = []
    with op(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            r = parse_line(line.rstrip("\n").replace("\0", ""))
            if r is not None:
                out.append(r)
    return out


# ---------------------------------------------------------------- data files

def _read_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def manifest():
    """{key: manifest row}"""
    m = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    return {f"{g['group'][:8]}-{g['position']}": g for g in m["games"]}


def keys():
    return list(manifest())


def traced_keys():
    """Keys with a trace.stdout.gz and status ok."""
    return [k for k in manifest() if (BATCH / k / "trace.stdout.gz").exists()
            and ((_read_json(BATCH / k / "trace_validation.json") or {}).get("status") == "ok")]


_ROWS = None


def _validation_rows():
    global _ROWS
    if _ROWS is None:
        _ROWS = {r["key"]: r for r in (_read_json(BATCH / "validation.json") or [])}
    return _ROWS


@lru_cache(maxsize=None)
def _keymap(world):
    return _read_json(EXTRACT / WORLDS[world] / "keys.json") or {}


class Death(dict):
    __getattr__ = Rec.__getattr__

    def __repr__(self):
        return (f"<death r{self['r']} {self['victim']}({self['v']}) by {self['killer']} gems={self['gems']} "
                f"at={self['at']}{' trusted' if self['trusted'] else ''}>")


class Turn:
    """One champion turn (round r, champion c): trace records, extract state and events, damage."""

    def __init__(self, g, r, c):
        self.g, self.r, self.c = g, r, c
        recs = g._by_rc.get((r, c), {})
        self.recs = recs
        self.tt = (recs.get("TT") or [None])[-1]
        self.tb = [x for x in recs.get("TB", ()) if x.s == "e"]
        self.tb_allies = [x for x in recs.get("TB", ()) if x.s == "a"]
        self.ta = recs.get("TA", [])
        self.ts = recs.get("TS", [])
        self.te = recs.get("TE", [])
        self.tf = recs.get("TF", [])
        self.tq = recs.get("TQ", [])
        self.debug = recs.get("other", [])
        self.trusted = g.trusted(r)

    def __repr__(self):
        return f"<turn r{self.r} c{self.c} {'TT' if self.tt else 'no TT'}{'' if self.trusted else ' untrusted'}>"

    @property
    def ran_out(self):
        """This turn ran out of fuel (an @o line resumes it in round r+1); the extract then shows no action in
        round r, and the turn's TT (`ok=0`, its end fields) is printed in round r+1 after the stale actions."""
        return (self.c, self.r + 1) in self.g._rollovers

    @property
    def t(self):
        """Turn index within the round (extract's event `t`)."""
        return self.g.turn_index(self.r, self.c)

    @property
    def start(self):
        """Extract state at the end of the previous round."""
        return self.g.state(self.r - 1, self.c)

    @property
    def end(self):
        """Extract state at the end of this round."""
        return self.g.state(self.r, self.c)

    @property
    def events(self):
        """Extract events of this champion's own turn (its actions, and what they caused)."""
        t = self.t
        return [e for e in self.g.events_in_round(self.r) if e["t"] == t]

    def belief(self, handle):
        return next((x for x in self.tb if x.h == handle), None)

    def te_kind(self, kind):
        return [x for x in self.te if x.k == kind]

    @property
    def actual(self):
        """Damage taken (after shields: health plus shield lost) from the end of this turn to the start of
        the champion's next turn, from the extract's events."""
        return self.g.damage_after(self.r, self.c)

    @property
    def predicted(self):
        """The trace's predictions for the window `actual` covers: lethal (worst case) at the end tile, or at
        the start tile when the champion did not move (`le`, else `ls` if p == q), camp damage per camp
        phase, and the fight sim at the end tile (`fe`, else `fs` if p == q). The start-tile values are
        also given as lethal_start, fight_start and camp_start, whether or not the champion moved."""
        tt = self.tt
        if not tt:
            return None
        stayed = tt.p == tt.q
        lethal = tt.le if tt.le is not None else (tt.ls if stayed else None)
        camp = tt.ce if tt.ce is not None else (tt.cs if stayed else None)
        fight = tt.fe if tt.fe not in (None, "?") else (tt.fs if stayed and tt.fs != "?" else None)
        return {"lethal": lethal, "camp": camp, "fight": fight, "threatened": tt.ts if stayed else None, "stayed": stayed,
                "lethal_start": tt.ls, "fight_start": tt.fs, "camp_start": tt.cs}


class Game:
    def __init__(self, key, world="ladder", row=None):
        if world not in WORLDS:
            raise ValueError(f"world {world!r}: one of {list(WORLDS)}")
        self.key, self.world = key, world
        self.row = row or manifest()[key]
        r = self.row
        self.map_name, self.our_side, self.opponent, self.opp_rank = r["map"], r["our_side"], r["opponent"], r.get("opp_rank")
        self.our_team = 0 if self.our_side == "a" else 1
        self.opp_team = 1 - self.our_team
        self.rounds_played, self.result = r["rounds"], r["result"]
        self.dir = BATCH / key

    def __repr__(self):
        return (f"<game {self.key} {self.map_name} side {self.our_side} vs {self.opponent} {self.result} {self.rounds_played}r "
                f"traced={self.traced} trusted<={self.ladder_trusted_through} world={self.world}>")

    # ---- validation
    @cached_property
    def validation(self):
        """runs/batch/<key>/validation.json: release and recorder re-runs vs the ladder; while batch.py is
        redoing a game (it deletes the file first) its row of runs/batch/validation.json, which has the
        same `release` / `rec` comparisons in snake_case; None if neither exists."""
        v = _read_json(self.dir / "validation.json")
        if v is None:
            v = _validation_rows().get(self.key)
        return v

    @cached_property
    def trace_validation(self):
        v = _read_json(self.dir / "trace_validation.json")
        if v is None:
            v = (_read_json(BATCH / "trace_validation.json") or {}).get(self.key)
        return v

    @property
    def traced(self):
        return bool(self.trace_validation and self.trace_validation.get("status") == "ok"
                    and (self.dir / "trace.stdout.gz").exists())

    @property
    def trace_stale(self):
        """The recorder run was redone after this trace was made: re-trace before trusting it."""
        rs, tv = self.dir / "rec.stdout", self.dir / "trace_validation.json"
        return self.traced and rs.exists() and tv.exists() and rs.stat().st_mtime > tv.stat().st_mtime

    @staticmethod
    def _trusted_from(cmp, rounds):
        if not cmp:
            return None
        if cmp.get("exact") or cmp.get("exactIgnoringRollovers") or cmp.get("exact_ignoring_rollovers"):
            return rounds
        diffs = [x["round"] for x in (cmp.get("firstInputDiff", cmp.get("first_input_diff")),
                                      cmp.get("firstRoundDiff", cmp.get("first_round_diff"))) if x]
        return min(diffs) - 1 if diffs else None

    @cached_property
    def rec_ladder_trusted_through(self):
        """The last round the recorder run shares with the ladder (from validation.json); None if not run."""
        return self._trusted_from((self.validation or {}).get("rec"), self.rounds_played)

    @cached_property
    def ladder_trusted_through(self):
        """The last round the trace explains the ladder game (None: no trace). Older trace_validation.json
        files lack the field; it is then derived from their vs_ladder comparison the way trace_batch.py does."""
        if not self.traced:
            return None
        tv = self.trace_validation
        if tv.get("ladder_trusted_through") is not None:
            t = tv["ladder_trusted_through"]
        else:
            t = self._trusted_from(tv.get("vs_ladder"), self.rounds_played) or 0
        if not tv.get("exact_vs_rec") and tv.get("rec_trusted_through") is not None:
            t = min(t, tv["rec_trusted_through"])
        return t

    def trusted(self, r):
        """True when the trace of round r is verified and explains this world's game: always (when traced and
        exact vs the recorder) in the rerun world, through ladder_trusted_through in the ladder world."""
        if not self.traced:
            return False
        if self.world == "rerun":
            tv = self.trace_validation
            return tv.get("exact_vs_rec", False) or r <= (tv.get("rec_trusted_through") or 0)
        return r <= self.ladder_trusted_through

    # ---- extract
    @cached_property
    def _extract_dir(self):
        km = _keymap(self.world).get(self.key)
        if not km:
            return None
        d = EXTRACT / WORLDS[self.world] / km["dir"]
        return d if (d / "meta.json").exists() else None

    @property
    def replay_sha(self):
        """sha256 of the ladder replay (from extract/ladder/keys.json); equal for byte-identical rematches."""
        return (_keymap("ladder").get(self.key) or {}).get("sha256")

    @property
    def has_extract(self):
        return self._extract_dir is not None

    def _need_extract(self):
        if self._extract_dir is None:
            raise LookupError(f"{self.key}: no {self.world} extract; run py tools/replay/harness/extract_all.py "
                              f"--kinds {'ladder' if self.world == 'ladder' else 'trace'} --keys {self.key}")
        return self._extract_dir

    @cached_property
    def meta(self):
        return json.loads((self._need_extract() / "meta.json").read_text())

    @cached_property
    def map(self):
        """Static map: walls, holes, bushes, altars (tile lists), camps, groups, spawn; plus `bush_set` and
        `wall_set` of (x, y)."""
        d = self._need_extract()
        m = json.loads((d / self.meta["mapFile"]).resolve().read_text())
        m["bush_set"] = {tuple(t) for t in m["bushes"]}
        m["wall_set"] = {tuple(t) for t in m["walls"]}
        return m

    def on_spawn(self, pos, team=None):
        """pos inside team's spawn region (default ours)."""
        sp = self.map["spawn"][self.our_team if team is None else team]
        return pos is not None and sp["minX"] <= pos[0] <= sp["maxX"] and sp["minY"] <= pos[1] <= sp["maxY"]

    @cached_property
    def events(self):
        with gzip.open(self._need_extract() / "events.jsonl.gz", "rt") as fh:
            return [json.loads(line) for line in fh]

    @cached_property
    def _events_by_round(self):
        out = defaultdict(list)
        for e in self.events:
            out[e["r"]].append(e)
        return out

    def events_in_round(self, r):
        return self._events_by_round.get(r, [])

    def events_where(self, kinds=None, rounds=None, actor=None, about=None):
        """Events filtered by kind(s), rounds (range or iterable), actor `a`, or `about` (actor, victim,
        target or damaged champion id)."""
        kinds = {kinds} if isinstance(kinds, str) else set(kinds) if kinds else None
        rs = rounds if rounds is not None else sorted(self._events_by_round)
        for r in rs:
            for e in self.events_in_round(r):
                if kinds and e["k"] not in kinds:
                    continue
                if actor is not None and e.get("a") != actor:
                    continue
                if about is not None and not (e.get("a") == about or e.get("v") == about or e.get("tgt") == about
                                              or any(x[0] == about for x in e.get("dmg", ()))):
                    continue
                yield e

    @cached_property
    def _rounds(self):
        with gzip.open(self._need_extract() / "rounds.json.gz", "rt") as fh:
            return json.load(fh)

    @cached_property
    def champions(self):
        """[{id, team, type (engine name), short (trace type), ours}] by id."""
        return {c["id"]: {"id": c["id"], "team": c["team"], "type": c["name"], "short": CHAMP_SHORT.get(c["name"], c["name"]),
                          "ours": c["team"] == self.our_team, "maxHp": c["maxHp"]} for c in self.meta["champions"]}

    @property
    def ours(self):
        """Our champion ids (from the extract, else from the trace's TV lines)."""
        if not self.has_extract:
            return sorted(self.instances)
        return [c for c, v in self.champions.items() if v["ours"]]

    @property
    def theirs(self):
        return [c for c, v in self.champions.items() if not v["ours"]]

    @cached_property
    def _champ_index(self):
        return {c["id"]: i for i, c in enumerate(self._rounds["champions"])}

    def state(self, r, c):
        """Champion c at the end of round r (extract rounds.json): x, y, hp, maxHp, alive, gems, chan, cd0,
        cd1, shield, stun, prio, ward, turn, sees, seenBy, ... Round 0 is the start (full health on spawn,
        approximated from round 1 with hp = maxHp); None outside the game."""
        R = self._rounds
        if r < 1:
            s = self.state(1, c)
            return s and dict(s, hp=s["maxHp"], gems=0)
        i = r - R["round"][0]
        if not 0 <= i < len(R["round"]):
            return None
        ch = R["champions"][self._champ_index[c]]
        return {k: (v[i] if isinstance(v, list) else v) for k, v in ch.items()}

    def positions(self, r):
        """{id: (x, y) or None (dead)} at the end of round r."""
        out = {}
        for c in self.champions:
            s = self.state(r, c)
            out[c] = (s["x"], s["y"]) if s and s["alive"] else None
        return out

    # ---- turn order
    def turn_order(self, r):
        """Champion ids in turn order for round r (rules: team A starts odd rounds, teams alternate one
        champion at a time, within a team higher priority first then id; priority set in a round applies
        from the next). Index = the extract events' `t`."""
        prio = {c: (self.state(r - 1, c) or {}).get("prio", 0) if r > 1 else 0 for c in self.champions}
        teams = [sorted((c for c, v in self.champions.items() if v["team"] == tm), key=lambda c: (-prio[c], c)) for tm in (0, 1)]
        first = 0 if r % 2 == 1 else 1
        a, b = teams[first], teams[1 - first]
        out = []
        for i in range(max(len(a), len(b))):
            out += ([a[i]] if i < len(a) else []) + ([b[i]] if i < len(b) else [])
        return out

    @cached_property
    def _observed_t(self):
        """(r, c) -> t from the champions' own events."""
        out = {}
        for e in self.events:
            k = e["k"]
            if e["t"] >= 0 and "a" in e and (k in OWN_TURN_EVENTS or k.endswith("_cancel") and e.get("cause") == "manual"):
                out.setdefault((e["r"], e["a"]), e["t"])
        return out

    def turn_index(self, r, c):
        """c's turn index in round r: from its own events when it acted, else from turn_order."""
        t = self._observed_t.get((r, c))
        if t is not None:
            return t
        order = self.turn_order(r)
        return order.index(c) if c in order else None

    def check_turn_order(self):
        """(agree, disagree, first disagreement) between turn_order and the events' t."""
        ok = bad = 0
        first = None
        for (r, c), t in self._observed_t.items():
            if self.turn_order(r).index(c) == t:
                ok += 1
            else:
                bad += 1
                first = first or (r, c, t, self.turn_order(r))
        return ok, bad, first

    def positions_at(self, r, t):
        """{id: (x, y) or None} at the start of turn t of round r, after its turn-start timers (respawn, recall
        and teleport arrival), as the bot sees it; from the end of round r-1 and this round's moves, dashes,
        arrivals, respawns and deaths. t = -1: before the camp phases."""
        if r > 1:
            pos = self.positions(r - 1)
        else:
            pos = self.positions(1)
            for e in reversed(self.events_in_round(1)):
                if e.get("f") and "a" in e:
                    pos[e["a"]] = tuple(e["f"])
        for e in self.events_in_round(r):
            k = e["k"]
            if e["t"] > t or e["t"] == t and k not in TURN_START_EVENTS:
                break
            if k in ("move", "recall_end", "teleport_end"):
                pos[e["a"]] = tuple(e["to"])
            elif k == "cast" and e.get("moved"):
                pos[e["a"]] = tuple(e["moved"])
            elif k == "respawn":
                pos[e["a"]] = tuple(e["at"])
            elif k == "death":
                pos[e["v"]] = None
        return pos

    # ---- damage
    def damage_events(self, c, start, end):
        """Damage to champion c strictly between turn positions start=(r, t) and end=(r, t), ordered by
        (round, turn index; camp phases are t = -1): [(r, t, source, amount, kind)], amounts after shields
        (health plus shield lost). Sources: champion id or 'camp:<group>'."""
        idx = self._damage_index.get(c, ([], []))
        lo, hi = bisect_left(idx[0], (start[0], start[1] + 1)), bisect_left(idx[0], end)
        return idx[1][lo:hi]

    @cached_property
    def _damage_index(self):
        """{champion: (sorted (r, t) keys, damage tuples)} over the whole game."""
        out = defaultdict(list)
        for e in self.events:
            r, k = e["r"], e["k"]
            if k in ("attack", "cast"):
                for vid, amt in e.get("dmg", ()):
                    out[vid].append((r, e["t"], e["a"], amt, k))
                if e.get("refl"):
                    out[e["a"]].append((r, e["t"], e.get("reflBy"), e["refl"], "refl"))
            elif k == "camp_attack":
                if e.get("tgt") is not None:
                    out[e["tgt"]].append((r, e["t"], f"camp:{e.get('g')}", e["dmg"], k))
                for vid, amt in e.get("xdmg", ()) or ():
                    out[vid].append((r, e["t"], f"camp:{e.get('g')}", amt, k))
            elif k == "other_dmg":
                for vid, amt in e.get("dmg", ()) or ():
                    out[vid].append((r, e["t"], None, amt, k))
        return {c: ([(x[0], x[1]) for x in v], v) for c, v in out.items()}

    def damage_after(self, r, c):
        """Damage to c from the end of its turn in round r to the start of its turn in round r+1."""
        t0, t1 = self.turn_index(r, c), self.turn_index(r + 1, c)
        if t0 is None:
            return None
        end = (r + 1, t1 if t1 is not None else 1 << 20)
        return round(sum(x[3] for x in self.damage_events(c, (r, t0), end)), 1)

    # ---- deaths
    def deaths(self, team="us"):
        """Deaths from the extract (`death` events), with killer and gem details and the trust flag.
        team: 'us', 'them' or 'all'. `by` is the killer's id (None for a camp kill: `camp` True and
        `camp_id`); `linked` marks the Cassi/Issac partner body (its value is the partner)."""
        out = []
        for e in self.events_where("death"):
            v = e["v"]
            mine = self.champions[v]["ours"]
            if team == "us" and not mine or team == "them" and mine:
                continue
            by = e.get("by")
            camp = e.get("camp") is not None or by == "camp"
            if by == "camp":
                by = None
            out.append(Death(r=e["r"], t=e["t"], s=e["s"], v=v, victim=self.champions[v]["short"], ours=mine,
                             at=tuple(e["at"]) if e.get("at") else None, gems=e.get("gems", 0), hp=e.get("hp"),
                             by=by, killer=("camp" if camp else self.champions[by]["short"] if by is not None else None),
                             camp=camp, camp_id=e.get("camp"), gemsTo=e.get("gemsTo", 0), gold=e.get("gold", 0), assists=e.get("assists", []),
                             cause=e.get("cause"), linked=e.get("linked"), trusted=self.trusted(e["r"]), event=e))
        return out

    # ---- trace
    @cached_property
    def records(self):
        """Every parsed trace record (empty if the game is not traced)."""
        if not self.traced:
            return []
        return parse_trace(self.dir / "trace.stdout.gz")

    @cached_property
    def _by_rc(self):
        out = defaultdict(lambda: defaultdict(list))
        for rec in self.records:
            if rec.tag.startswith("@") or rec.get("r") is None or rec.get("c") is None:
                continue
            tag = rec.tag if rec.tag in TAGGED else "other"
            out[(rec.r, rec.c)][tag].append(rec)
        return out

    @cached_property
    def harness(self):
        """@ lines: {'@v': [...], '@o': [...], '@!': [...]}."""
        out = defaultdict(list)
        for rec in self.records:
            if rec.tag.startswith("@"):
                out[rec.tag].append(rec)
        return out

    @cached_property
    def _rollovers(self):
        return {(r.c, r.r) for r in self.harness.get("@o", ())}

    @cached_property
    def instances(self):
        """TV records by champion id."""
        return {r.c: r for r in self.records if r.tag == "TV"}

    def trace(self, r, c):
        """{tag: [Rec]} of round r, champion c (TT, TB, TA, TS, TE, TF, TQ, other)."""
        return {k: list(v) for k, v in self._by_rc.get((r, c), {}).items()}

    def turn(self, r, c):
        return Turn(self, r, c)

    def turns(self, champ=None, rounds=None, trusted_only=False):
        """Turns of our champions (or `champ`, an id or list) over `rounds` (range or iterable; default: every
        round with trace records, or every played round without a trace)."""
        champs = [champ] if isinstance(champ, int) else list(champ) if champ is not None else None
        if rounds is None:
            if self.records:
                rounds = sorted({r for (r, _) in self._by_rc})
            else:
                rounds = range(1, self.rounds_played + 1)
        for r in rounds:
            for c in champs if champs is not None else self.ours:
                if trusted_only and not self.trusted(r):
                    continue
                if self.records and (r, c) not in self._by_rc and champs is None:
                    continue
                yield Turn(self, r, c)

    def window(self, r, c, before=5, after=0):
        """Turns of champion c in rounds r-before .. r+after."""
        return list(self.turns(c, range(max(1, r - before), r + after + 1)))

    def actual_damage(self, r, c):
        """Damage taken by c between its turns in rounds r and r+1 (Turn.actual)."""
        return self.damage_after(r, c)

    def enemy_index(self):
        """{enemy index i: handle} from TB lines (TS `rm` masks use indices, `kill` handles)."""
        out = {}
        for rec in self.records:
            if rec.tag == "TB" and rec.s == "e":
                out.setdefault(rec.i, rec.h)
                if len(out) == len(self.theirs or [0] * 6):
                    break
        return out

    def to_frame(self, tag="TT"):
        """pandas DataFrame of every record with this tag (needs pandas)."""
        import pandas as pd
        return pd.DataFrame([dict(r) for r in self.records if r.tag == tag])


def load_game(key, world="ladder"):
    return Game(key, world)


def games(filter=None, traced=None, world="ladder", distinct=False):
    """Games of the manifest. filter: a callable(Game) or a dict of manifest fields to match
    (e.g. {"map": "00swirl", "our_side": "a"}); traced: True/False to keep only (un)traced games;
    distinct: keep one game per ladder replay content (byte-identical rematches: 60 of the 390 keys
    repeat another), preferring a traced copy."""
    out = []
    rows = list(manifest().items())
    if distinct:
        km = _keymap("ladder")
        rows.sort(key=lambda kr: not (BATCH / kr[0] / "trace.stdout.gz").exists())
        seen, keep = set(), []
        for k, row in rows:
            d = (km.get(k) or {}).get("dir", k)
            if d not in seen:
                seen.add(d)
                keep.append((k, row))
        order = {k: i for i, k in enumerate(manifest())}
        rows = sorted(keep, key=lambda kr: order[kr[0]])
    for k, row in rows:
        g = Game(k, world, row)
        if traced is not None and g.traced != traced:
            continue
        if isinstance(filter, dict) and any(row.get(f) != v for f, v in filter.items()):
            continue
        if callable(filter) and not filter(g):
            continue
        out.append(g)
    return out


def extract_diff(key, a="ladder", b="rerun"):
    """Compare two worlds' extracts of a game: {"events": (n_a, n_b, first differing index or None),
    "rounds": first (round, field, champion) whose state differs or None, "result": equal?}. The meta
    (sources, team names, timings) is not compared."""
    ga, gb = Game(key, a), Game(key, b)
    if not ga.has_extract or not gb.has_extract:
        return None
    ea, eb = ga.events, gb.events
    first_ev = next((i for i, (x, y) in enumerate(zip(ea, eb)) if x != y), None)
    if first_ev is None and len(ea) != len(eb):
        first_ev = min(len(ea), len(eb))
    ra, rb = ga._rounds, gb._rounds
    first_round = None
    n = min(len(ra["round"]), len(rb["round"]))
    for i in range(n):
        if ra["round"][i] != rb["round"][i] or ra["gems"][0][i] != rb["gems"][0][i] or ra["gems"][1][i] != rb["gems"][1][i]:
            first_round = (ra["round"][i], "gems", None)
            break
        diff = next(((ca["id"], f) for ca, cb in zip(ra["champions"], rb["champions"]) for f in ca
                     if isinstance(ca[f], list) and ca[f][i] != cb[f][i]), None)
        if diff:
            first_round = (ra["round"][i], diff[1], diff[0])
            break
        if any(ra[f][i] != rb[f][i] for f in ("wards", "controlWards", "locks")):
            first_round = (ra["round"][i], "wards/locks", None)
            break
    if first_round is None and len(ra["round"]) != len(rb["round"]):
        first_round = (ra["round"][n - 1] + 1, "length", None)
    groups_equal = ra["groups"] == rb["groups"]
    return {"events": (len(ea), len(eb), first_ev, ea[first_ev]["r"] if first_ev is not None and first_ev < len(ea) else None),
            "rounds": first_round, "groups_equal": groups_equal, "result": ga.meta["result"] == gb.meta["result"],
            "champions_equal": [{k: v for k, v in c.items() if k != "stats"} for c in ga.meta["champions"]]
            == [{k: v for k, v in c.items() if k != "stats"} for c in gb.meta["champions"]]}


def summary():
    rows = []
    for g in games():
        tv = g.trace_validation or {}
        rows.append((g.key, g.map_name, g.our_side, g.opponent, g.rounds_played, g.has_extract,
                     Game(g.key, "rerun").has_extract, g.traced, tv.get("exact_vs_rec"), tv.get("exact_vs_ladder"),
                     g.ladder_trusted_through, g.rec_ladder_trusted_through, g.trace_stale))
    print("key map side opponent rounds extract_ladder extract_rerun traced exact_vs_rec exact_vs_ladder ladder_trusted_through rec_ladder_trusted_through stale")
    for r in rows:
        if r[7] or "--all" in sys.argv:
            print(*r)
    print(f"{len(rows)} games: ladder extract {sum(r[5] for r in rows)}, rerun extract {sum(r[6] for r in rows)}, traced {sum(r[7] for r in rows)}, "
          f"recorder run shares the whole game with the ladder in {sum(r[11] == r[4] for r in rows)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary":
        summary()
    elif cmd == "extract-check":
        ks = sys.argv[2].split(",") if len(sys.argv) > 2 else traced_keys()
        for k in ks:
            g = Game(k)
            print(k, f"trusted<={g.ladder_trusted_through}/{g.rounds_played}", extract_diff(k))
    elif cmd == "examples":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import v38lib_examples
        v38lib_examples.main(sys.argv[2:])
    else:
        sys.exit(__doc__)
