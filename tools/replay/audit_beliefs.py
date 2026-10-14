"""Audit aphelios' world beliefs against replay ground truth.

Build the bot with `debug_beliefs = true` (bots/aphelios/src/util.h); each champion then prints a
"BD" line every `debug_beliefs_period` rounds (and in rounds 1-3), which local replays keep in
team-a.stdout / team-b.stdout inside the .repl26a zip. Extract the replays first, then audit:

    node tools/replay/extract.mjs replays/batch-X
    py tools/replay/audit_beliefs.py replays/batch-X [more dirs or .repl26a files] [--examples 20] [--out FILE]

Beliefs are dumped at the end of the champion's turn and compared with the truth at the start of
that turn (enemies do not move during it; camp and altar beliefs are not refreshed during it).
"""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "replays" / ".analysis"
DIGITS = {c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")}
LINE = re.compile(r"(B[DM]) (\S+)")
ACTIONS = {"move", "attack", "cast", "ward", "recall_start", "tribute_start", "shop", "consumable", "lock_place",
           "teleport_start", "blocked", "sell", "tribute_blocked"}
TURN_START = {"recall_end", "teleport_end", "respawn"}
STATE = {0: "alive", 1: "cleared", 2: "respawning"}  # bot CampState
TRUE_STATE = {1: 0, 2: 1, 3: 2}  # replay group state -> bot CampState
AWAKE = {0: "asleep", 1: "awake", 2: "unknown"}
SOURCE = {0: "none", 1: "seen", 2: "comms", 3: "inferred"}
ENEMY_FIELDS = ["id", "alive", "visible", "tracked", "x", "y", "pos_round", "source", "fixed_round", "at_round",
                "at_slot", "turns", "ready0", "ready1", "respawn_earliest", "respawn_latest", "count"]
GROUP_FIELDS = ["handle", "state", "awake", "state_round", "respawn_round", "holder", "held_since", "damaged",
                "quiet", "tiles_seen"]
ALTAR_FIELDS = ["x", "y", "ally", "enemy", "seen_round"]


class Reader:
    """Varints: zigzag, 5 bits per base64 digit, least significant first, bit 5 = more."""

    def __init__(self, text):
        self.text, self.i = text, 0

    def done(self):
        return self.i >= len(self.text)

    def num(self):
        n = shift = 0
        while True:
            d = DIGITS[self.text[self.i]]
            self.i += 1
            n |= (d & 31) << shift
            shift += 5
            if not d & 32:
                return (n >> 1) ^ -(n & 1)

    def word(self):
        w = 0
        for k in range(11):
            w |= DIGITS[self.text[self.i + k]] << (6 * k)
        self.i += 11
        return w & (2 ** 64 - 1)

    def chunks(self, chunked_width):
        tiles, last = set(), 0
        while not self.done():
            code = self.num()
            i = last + (code >> 1)
            last = i
            w = 2 ** 64 - 1 if code & 1 else self.word()
            cy, cx = divmod(i, chunked_width)
            while w:
                b = (w & -w).bit_length() - 1
                tiles.add((cx * 8 + (b & 7), cy * 8 + (b >> 3)))
                w &= w - 1
        return tiles


def parse_dumps(text):
    groups_at, dumps = {}, []
    for raw in text.splitlines():
        m = LINE.search(raw)
        if not m:
            continue
        sections = m.group(2).split("|")
        r = Reader(sections[0])
        if m.group(1) == "BM":
            r.num()
            r.num()
            while not r.done():
                handle, x, y = r.num(), r.num(), r.num()
                groups_at[handle] = (x, y)
            continue
        head = [r.num() for _ in range(8)]
        d = dict(zip(["round", "id", "slot", "x", "y", "alive", "prev_cost", "chunked_width"], head))
        d["enemies"], d["groups"], d["altars"] = [], {}, []
        for sec in sections[1:]:
            r = Reader(sec[1:])
            if sec[0] == "E":
                e = dict(zip(ENEMY_FIELDS, [r.num() for _ in ENEMY_FIELDS]))
                e["tiles"] = r.chunks(d["chunked_width"]) if e["count"] >= 0 else None
                d["enemies"].append(e)
            elif sec[0] == "G":
                g = dict(zip(GROUP_FIELDS, [r.num() for _ in GROUP_FIELDS]))
                d["groups"][g["handle"]] = g
            elif sec[0] == "A":
                d["altars"].append(dict(zip(ALTAR_FIELDS, [r.num() for _ in ALTAR_FIELDS])))
        dumps.append(d)
    return groups_at, dumps


def find_replays(inputs):
    out = []
    for i in inputs:
        p = Path(i)
        out += sorted(p.rglob("*.repl26a")) if p.is_dir() else [p]
    return [p for p in out if ".analysis" not in p.parts]


class Truth:
    def __init__(self, folder):
        self.dir = folder
        self.meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        self.map = json.loads((folder / self.meta["mapFile"]).read_text(encoding="utf-8"))
        self.rounds = json.load(gzip.open(folder / "rounds.json.gz"))
        self.events = [json.loads(l) for l in gzip.open(folder / "events.jsonl.gz", "rt", encoding="utf-8")]
        self.by_round = defaultdict(list)
        for e in self.events:
            self.by_round[e["r"]].append(e)
        self.index = {r: i for i, r in enumerate(self.rounds["round"])}
        self.champs = {c["id"]: c for c in self.rounds["champions"]}
        self.team = {c["id"]: c["team"] for c in self.meta["champions"]}
        self.width, self.height = self.map["width"], self.map["height"]
        self.blocked = {tuple(p) for k in ("walls", "holes", "altars") for p in self.map[k]}
        # Group rows are written on change; keep each group's history to forward-fill.
        self.group_rows = defaultdict(list)
        for row in self.rounds["groups"]:
            self.group_rows[row[1]].append(row)
        self.respawns = defaultdict(list)
        self.group_respawns = defaultdict(list)
        self.captures = defaultdict(list)
        self.casts = defaultdict(list)  # (champion, slot) -> [(round, turn)]
        self.resets = defaultdict(list)  # champion -> [(round, turn)] readying both slots: respawns, Vendetta kills
        vendettas = {c["id"] for c in self.meta["champions"] if c["name"] == "Vendetta"}
        for e in self.events:
            if e["k"] == "cast":
                self.casts[(e["a"], e["slot"])].append((e["r"], e["t"]))
            elif e["k"] == "respawn":
                self.resets[e["a"]].append((e["r"], e["t"]))
            elif e["k"] == "death" and e.get("by") in vendettas:
                self.resets[e["by"]].append((e["r"], e["t"]))
            elif e["k"] == "camp_death" and e.get("by") in vendettas:
                self.resets[e["by"]].append((e["r"], e["t"]))
        for e in self.events:
            if e["k"] == "respawn":
                self.respawns[e["a"]].append(e["r"])
            elif e["k"] == "group_respawn":
                self.group_respawns[e["g"]].append(e["r"])
            elif e["k"] == "capture":
                self.captures[e["g"]].append(e["r"])

    def at(self, column, cid, r):
        i = self.index.get(r)
        return None if i is None else self.champs[cid][column][i]

    def turn_index(self, cid, r):
        """The champion's turn index in round r: teams alternate, team A first in odd rounds;
        within a team, higher priority first, then lower id; the larger team's extras go last."""
        first = 0 if r % 2 == 1 else 1
        prio = lambda c: self.at("prio", c, r - 1) or 0 if r > 1 else 0
        team = self.team[cid]
        mine = sorted((c for c in self.team if self.team[c] == team), key=lambda c: (-prio(c), c))
        others = sum(1 for c in self.team if self.team[c] != team)
        rank = mine.index(cid)
        return 2 * rank + (0 if team == first else 1) if rank < others else others + rank

    def action_turns(self, cid, r):
        return {e["t"] for e in self.by_round[r] if e.get("a") == cid and e["k"] in ACTIONS}

    def champion_at(self, cid, r, t, own_turn_start=False):
        """(alive, (x, y)) at the start of turn t of round r: the end of round r, with this round's
        events from turn t on undone. With own_turn_start, the champion's own turn-start events
        (recall and teleport landings, respawn) stay applied, as its bot sees them."""
        alive = self.at("alive", cid, r)
        pos = (self.at("x", cid, r), self.at("y", cid, r))
        tele_from = None
        later = [e for e in self.by_round[r] if e["t"] >= t
                 and not (own_turn_start and e["t"] == t and e.get("a") == cid and e["k"] in TURN_START)]
        for e in self.by_round[r]:
            if e["k"] == "teleport_start" and e.get("a") == cid:
                tele_from = tuple(e["f"])
        for e in reversed(later):
            k = e["k"]
            if k == "death" and e["v"] == cid:
                alive, pos = 1, tuple(e["at"])
            elif e.get("a") != cid:
                continue
            elif k == "respawn":
                alive, pos = 0, (None, None)
            elif k in ("move", "recall_end") or (k == "cast" and "moved" in e):
                pos = tuple(e["f"])
            elif k == "teleport_end":
                pos = tuple(e["f"]) if "f" in e else tele_from or pos
        return bool(alive), pos

    def holder_at(self, g, r, t, positions):
        """The team alone on a group's camp tiles, or 2."""
        tiles = {tuple(p) for p in self.map["groups"][g]["tiles"]}
        teams = {self.team[c] for c, (alive, pos) in positions.items() if alive and pos in tiles}
        return teams.pop() if len(teams) == 1 else 2

    def occupied(self, g, r):
        """Any champion on the group's camp tiles at the start of round r."""
        tiles = {tuple(p) for p in self.map["groups"][g]["tiles"]}
        i = self.index.get(r - 1)
        return i is not None and any((c["x"][i], c["y"][i]) in tiles for c in self.rounds["champions"])

    def next_payout(self, g, r, t):
        """Round of the next capture of g if the hold now lasts until it, else None."""
        for rr in range(r, max(self.index) + 1):
            for e in self.by_round[rr]:
                if e.get("g") != g or (rr, e["t"]) < (r, t):
                    continue
                if e["k"] == "capture":
                    return rr
                if e["k"] in ("capture_reset", "capture_flip"):
                    return None
        return None

    def ready_round(self, cid, slot, r, t):
        """Earliest round the slot can be cast, as of the start of turn t of round r."""
        last = max((x for x in self.casts[(cid, slot)] if x < (r, t)), default=None)
        if last is None or any(last < x < (r, t) for x in self.resets[cid]):
            return 0
        return last[0] + 8

    def killed_in_turn(self, cid, r, t):
        return any(e["k"] == "death" and e["v"] == cid and e["t"] == t for e in self.by_round[r])

    def group_at(self, g, r, t):
        """{state, team, awake} at the start of turn t of round r (t = -1 phases count as before)."""
        state, team, awake = 1, 2, 0
        for row in self.group_rows[g]:
            if row[0] > r - 1:
                break
            state, team, awake = row[2], row[3], row[6]
        for e in self.by_round[r]:
            if e["t"] >= t or e.get("g") != g:
                continue
            k = e["k"]
            if k == "group_clear":
                state, awake, team = 2, -1, 2
            elif k in ("capture_hold", "capture_flip"):
                team = e["team"]
            elif k == "capture_reset":
                team = 2
            elif k == "capture":
                state, team = 3, 2
            elif k == "group_respawn":
                state, awake, team = 1, 0, 2
            elif k == "group_wake":
                awake = 1
            elif k == "group_sleep":
                awake = 0
        return state, team, awake

    def locks_at(self, r, t):
        locks = {(l[0], l[1], l[2]) for l in (self.rounds["locks"][self.index[r - 1]] if r - 1 in self.index else [])}
        for e in self.by_round[r]:
            if e["t"] >= t:
                break
            if e["k"] == "lock_place":
                locks.add((e["team"], *e["to"]))
            elif e["k"] == "lock_destroyed":
                locks.discard((e["team"], *e["at"]))
        return locks

    def moved_between(self, cid, start, end):
        """Teleports, recalls, respawns and dashes of a champion between two (round, turn) points."""
        kinds = set()
        for r in range(max(start[0], 1), end[0] + 1):
            for e in self.by_round[r]:
                if e.get("a") != cid or not (start <= (e["r"], e["t"]) < end):
                    continue
                if e["k"] in ("teleport_start", "teleport_end"):
                    kinds.add("teleport")
                elif e["k"] == "recall_end":
                    kinds.add("recall")
                elif e["k"] == "respawn":
                    kinds.add("respawn")
                elif e["k"] == "cast" and "moved" in e:
                    kinds.add("dash")
        return kinds


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def bucket(n, edges):
    for lo, hi in edges:
        if lo <= n <= hi:
            return f"{lo}-{hi}" if lo != hi else str(lo)
    return f">{edges[-1][1]}"


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def quantile(values, q):
    if not values:
        return "-"
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


def audit(replays, n_examples):
    c = Counter()
    examples = defaultdict(list)
    sizes = defaultdict(list)
    costs = []
    games = 0

    def note(kind, text):
        c[kind] += 1
        if len(examples[kind]) < n_examples:
            examples[kind].append(text)

    for path in replays:
        data = path.read_bytes()
        folder = ANALYSIS / hashlib.sha256(data).hexdigest()[:16]
        if not (folder / "meta.json").is_file():
            print(f"skip {path}: not extracted (run node tools/replay/extract.mjs on it)", file=sys.stderr)
            continue
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            continue
        T = None
        for side, name in ((0, "team-a.stdout"), (1, "team-b.stdout")):
            if name not in z.namelist():
                continue
            groups_at, dumps = parse_dumps(z.read(name).decode("utf-8", "replace"))
            if not dumps:
                continue
            T = T or Truth(folder)
            games += 1
            where = f"{folder.name} ({path.name}, side {'AB'[side]})"
            for handle, (x, y) in groups_at.items():
                tiles = T.map["groups"][handle]["tiles"] if handle < len(T.map["groups"]) else []
                c["group_map_checked"] += 1
                if [x, y] not in tiles:
                    note("group_map_mismatch", f"{where} handle {handle} at {(x, y)}")
            for d in dumps:
                r, me = d["round"], d["id"]
                if r not in T.index or (r > 1 and r - 1 not in T.index):
                    continue
                c["dumps"] += 1
                if d["prev_cost"] > 0:
                    costs.append(d["prev_cost"])
                if T.team.get(me) != side:
                    note("self_team_mismatch", f"{where} r{r} c{me}")
                    continue
                t = T.turn_index(me, r)
                acted = T.action_turns(me, r)
                c["slot_checked"] += 1
                if d["slot"] != t:
                    note("slot_wrong", f"{where} r{r} c{me}: bot slot {d['slot']}, rule {t}, action turns {sorted(acted)}")
                if acted and acted != {t}:
                    note("slot_rule_vs_events", f"{where} r{r} c{me}: rule {t}, action turns {sorted(acted)}")
                my_alive, my_pos = T.champion_at(me, r, t, own_turn_start=True)
                start_pos = T.champion_at(me, r, t)[1]
                moved = d["alive"] and ((d["x"], d["y"]) != my_pos or my_pos != start_pos)
                positions = {cid: T.champion_at(cid, r, t, own_turn_start=cid == me) for cid in T.team}
                if bool(d["alive"]) != my_alive:
                    note("self_alive_wrong", f"{where} r{r} c{me}")
                sees = set(T.at("sees", me, r) or [])

                for e in d["enemies"]:
                    eid = e["id"]
                    if e["tiles"] is not None:  # chunk padding past the map edge holds garbage
                        e["tiles"] = {p for p in e["tiles"] if p[0] < T.width and p[1] < T.height}
                    alive, pos = T.champion_at(eid, r, t)
                    c["enemy_checks"] += 1
                    tag = f"{where} r{r} c{me} slot {t} -> e{eid}"
                    if T.killed_in_turn(eid, r, t):
                        c["enemy_killed_this_turn"] += 1
                        continue
                    if bool(e["alive"]) != alive:
                        note("enemy_alive_wrong", f"{tag}: believed alive={e['alive']}, true {alive}")
                        continue
                    if not alive:
                        c["enemy_dead"] += 1
                        later = [x for x in T.respawns[eid] if x >= r]
                        if later and e["respawn_earliest"] >= 0:
                            c["respawn_window_checked"] += 1
                            if not e["respawn_earliest"] <= later[0] <= e["respawn_latest"]:
                                note("respawn_window_wrong", f"{tag}: window r{e['respawn_earliest']}-r{e['respawn_latest']}, respawned r{later[0]}")
                        continue
                    for slot in (0, 1):
                        believed, true = e[f"ready{slot}"], T.ready_round(eid, slot, r, t)
                        # As the bot counts: the first round whose own turn, from now on, finds it ready.
                        now = r + 1 if T.turn_index(eid, r) < t else r
                        believed, true = max(believed, now), max(true, now)
                        c["ready_checks"] += 1
                        if believed > true:
                            note("ready_round_too_late" + ("_visible" if e["visible"] else ""),
                                 f"{tag} slot {slot}: believed ready r{believed}, truly r{true}")
                        elif believed < true and e["visible"]:
                            note("ready_round_early_visible", f"{tag} slot {slot}: believed ready r{believed}, truly r{true}")
                        elif believed < true:
                            c["ready_round_early_unseen_cast"] += 1
                    if e["visible"]:
                        c["enemy_visible"] += 1
                        if (e["x"], e["y"]) != pos:
                            note("visible_pos_wrong", f"{tag}: believed {(e['x'], e['y'])}, true {pos}")
                        if e["tiles"] is not None and e["tiles"] != {pos}:
                            note("visible_set_wrong", f"{tag}: set {sorted(e['tiles'])[:4]}..., true {pos}")
                        continue
                    if not moved and eid in sees:
                        note("visible_missed", f"{tag}: engine shows it at {pos} at turn start")
                    if not e["tracked"]:
                        c["enemy_untracked"] += 1
                        continue
                    if e["count"] == -2 or e["tiles"] is None:
                        c["enemy_set_skipped"] += 1
                        continue
                    c["possible_checked"] += 1
                    if len(e["tiles"]) != e["count"]:
                        note("decode_count_mismatch", f"{tag}: decoded {len(e['tiles'])}, dumped {e['count']}")
                    rounds_since = r - e["fixed_round"]
                    sizes[bucket(rounds_since, [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20)])].append(e["count"])
                    small = e["count"] <= 9
                    c["possible_small"] += small
                    if pos in e["tiles"]:
                        continue
                    c["possible_small_miss"] += small
                    kinds = T.moved_between(eid, (e["fixed_round"], -1), (r, t))
                    miss = min((cheb(pos, q) for q in e["tiles"]), default=None)
                    if "teleport" in kinds:
                        cat = "teleport"
                    elif e["source"] == 2:
                        cat = "comms_fix"
                    elif "respawn" in kinds:
                        cat = "after_respawn"
                    elif "recall" in kinds:
                        cat = "after_recall"
                    elif "dash" in kinds:
                        cat = "after_dash"
                    else:
                        cat = "other"
                    note(f"possible_miss_{cat}", f"{tag}: true {pos} {miss} outside {e['count']} tiles; fixed r{e['fixed_round']} "
                         f"source {SOURCE.get(e['source'])} at r{e['at_round']}/{e['at_slot']} turns {e['turns']} "
                         f"ready {e['ready0']},{e['ready1']} events {sorted(kinds)}")

                for g in range(len(T.map["groups"])):
                    b = d["groups"].get(g) or {"state": 0, "awake": 0, "state_round": -1, "respawn_round": -1,
                                               "holder": -1, "held_since": -1, "damaged": -1, "quiet": 0, "tiles_seen": -1}
                    state, team, awake = T.group_at(g, r, t)
                    true_state = TRUE_STATE.get(state)
                    seen = b["state_round"] == r
                    c["group_checks"] += 1
                    c["group_checks_seen" if seen else "group_checks_unseen"] += 1
                    tag = f"{where} r{r} c{me} slot {t} g{g}"
                    if b["state"] != true_state:
                        kind = "camp_state_wrong_seen" if seen else "camp_state_stale"
                        if not seen:
                            c[f"stale {STATE[b['state']]} -> true {STATE.get(true_state, state)}"] += 1
                        note(kind, f"{tag}: believed {STATE[b['state']]}, true {STATE.get(true_state, state)}"
                             f" (bot respawn r{b['respawn_round']}, last seen r{b['state_round']})")
                        if seen:
                            continue
                    if b["state"] == 0 and true_state == 0:
                        c["awake_checks"] += 1
                        if b["awake"] == 2:
                            c["awake_unknown"] += 1
                        elif b["awake"] != awake:
                            kind = ("awake_believed_asleep" if awake == 1 else "awake_believed_awake") + ("_seen" if seen else "_unseen")
                            note(kind, f"{tag}: believed {AWAKE[b['awake']]}, true {'awake' if awake == 1 else 'asleep'}"
                                 f" (damaged r{b.get('damaged')}, quiet {b.get('quiet')})")
                    if b["state"] == 2 and true_state == 2:
                        c["respawn_checks"] += 1
                        later = [x for x in T.group_respawns[g] if x >= r]
                        if later:
                            diff = b["respawn_round"] - later[0]
                            if diff < 0 and any(T.occupied(g, x) for x in range(b["respawn_round"], later[0])):
                                c["respawn_delayed_by_occupancy"] += 1
                            elif diff:
                                note(f"respawn_round_{'early' if diff < 0 else 'late'}" + ("_seen" if seen else "_unseen"),
                                     f"{tag}: believed r{b['respawn_round']}, respawned r{later[0]}")
                    if b["state"] == 1 and true_state == 1:
                        c["holder_checks"] += 1
                        on = T.holder_at(g, r, t, positions)
                        true_holder = -1 if on == 2 else 0 if on == side else 1
                        if b["holder"] != true_holder:
                            kind = "holder_wrong_seen" if b["tiles_seen"] == 1 and not moved else "holder_stale"
                            note(kind, f"{tag}: believed {b['holder']}, true {true_holder} (0 us, 1 them, -1 nobody; engine {team})")
                        elif b["holder"] >= 0:
                            pay = T.next_payout(g, r, t)
                            if pay:
                                c["payout_checks"] += 1
                                if b["held_since"] + 6 != pay:
                                    note("payout_round_off", f"{tag}: held_since r{b['held_since']} (payout r{b['held_since'] + 6}), paid r{pay}")

                locks = T.locks_at(r, t)
                believed = {(0 if a["ally"] else 1, a["x"], a["y"]) for a in d["altars"]}
                truth = {(0 if team == side else 1, x, y) for team, x, y in locks}
                c["altar_checks"] += 1
                if believed != truth:
                    note("altar_locks_wrong", f"{where} r{r} c{me}: believed {sorted(believed)}, true {sorted(truth)}")
    return c, examples, sizes, costs, games


def report(c, examples, sizes, costs, games):
    out = [f"# Belief audit\n\n{games} team-games, {c['dumps']} dumps.\n"]
    rows = [
        ("Enemy true tile not in `possible`", sum(v for k, v in c.items() if k.startswith("possible_miss_")), c["possible_checked"]),
        ("  of which teleport (unmodelled)", c["possible_miss_teleport"], c["possible_checked"]),
        ("  of which after a comms fix", c["possible_miss_comms_fix"], c["possible_checked"]),
        ("  of which after respawn / recall / dash", c["possible_miss_after_respawn"] + c["possible_miss_after_recall"] + c["possible_miss_after_dash"], c["possible_checked"]),
        ("  of which other", c["possible_miss_other"], c["possible_checked"]),
        ("  in sets of 9 tiles or fewer (ground-cast targets)", c["possible_small_miss"], c["possible_small"]),
        ("Enemy ability ready before the bot believes, unseen", c["ready_round_too_late"], c["ready_checks"]),
        ("  same while visible", c["ready_round_too_late_visible"], c["ready_checks"]),
        ("Enemy ability believed ready before it is, visible", c["ready_round_early_visible"], c["ready_checks"]),
        ("  unseen (a cast we missed; expected)", c["ready_round_early_unseen_cast"], c["ready_checks"]),
        ("Visible enemy at the wrong tile", c["visible_pos_wrong"], c["enemy_visible"]),
        ("Enemy in sight but not visible (did not move)", c["visible_missed"], c["enemy_checks"]),
        ("Enemy alive/dead wrong", c["enemy_alive_wrong"], c["enemy_checks"]),
        ("Respawn window misses the respawn", c["respawn_window_wrong"], c["respawn_window_checked"]),
        ("Camp state wrong, seen this turn", c["camp_state_wrong_seen"], c["group_checks_seen"]),
        ("Camp state stale (not seen)", c["camp_state_stale"], c["group_checks_unseen"]),
        ("Awake believed asleep, seen", c["awake_believed_asleep_seen"], c["awake_checks"]),
        ("Awake believed asleep, unseen", c["awake_believed_asleep_unseen"], c["awake_checks"]),
        ("Asleep believed awake, seen", c["awake_believed_awake_seen"], c["awake_checks"]),
        ("Asleep believed awake, unseen", c["awake_believed_awake_unseen"], c["awake_checks"]),
        ("Awake unknown", c["awake_unknown"], c["awake_checks"]),
        ("Respawn round early, seen", c["respawn_round_early_seen"], c["respawn_checks"]),
        ("Respawn round late, seen", c["respawn_round_late_seen"], c["respawn_checks"]),
        ("Respawn round off, unseen", c["respawn_round_early_unseen"] + c["respawn_round_late_unseen"], c["respawn_checks"]),
        ("Capture holder wrong, tiles in view", c["holder_wrong_seen"], c["holder_checks"]),
        ("Capture holder stale", c["holder_stale"], c["holder_checks"]),
        ("Payout round (held_since + 6) wrong", c["payout_round_off"], c["payout_checks"]),
        ("Respawn later than believed: tiles occupied (expected)", c["respawn_delayed_by_occupancy"], c["respawn_checks"]),
        ("Altar locks wrong", c["altar_locks_wrong"], c["altar_checks"]),
        ("Own turn slot wrong", c["slot_wrong"], c["slot_checked"]),
    ]
    out.append("| Check | Wrong | Checked | Rate |\n| --- | ---: | ---: | ---: |")
    for name, bad, total in rows:
        out.append(f"| {name} | {bad} | {total} | {pct(bad, total)} |")
    out.append("")
    stale = sorted((k, v) for k, v in c.items() if k.startswith("stale "))
    out.append("Stale camp states (believed -> true): " + ", ".join(f"{k[6:]} {v}" for k, v in stale) + ".\n")
    alive_unseen = c["enemy_untracked"] + c["possible_checked"] + c["enemy_set_skipped"]
    out.append(f"Unseen live enemies: {alive_unseen}; untracked (anywhere) {pct(c['enemy_untracked'], alive_unseen)}, "
               f"set left out for fuel {c['enemy_set_skipped']}.\n")
    out.append("`possible` size by rounds since last fixed:\n\n| Rounds | n | median | p90 | max |\n| --- | ---: | ---: | ---: | ---: |")
    for k in ["0", "1-2", "3-5", "6-10", "11-20", ">20"]:
        v = sizes.get(k, [])
        out.append(f"| {k} | {len(v)} | {quantile(v, 0.5)} | {quantile(v, 0.9)} | {max(v) if v else '-'} |")
    out.append("")
    if costs:
        out.append(f"Dump fuel: median {quantile(costs, 0.5)}, p90 {quantile(costs, 0.9)}, max {max(costs)}.\n")
    integrity = ["decode_count_mismatch", "visible_set_wrong", "group_map_mismatch", "self_team_mismatch", "self_alive_wrong",
                 "slot_rule_vs_events"]
    out.append("Integrity: " + ", ".join(f"{k} {c[k]}" for k in integrity) + f" (group map checked {c['group_map_checked']}).\n")
    for kind in sorted(examples):
        out.append(f"## {kind} ({c[kind]})\n")
        out += [f"- {x}" for x in examples[kind]]
        out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="Batch directories or .repl26a files")
    parser.add_argument("--examples", type=int, default=8, help="Examples listed per discrepancy kind")
    parser.add_argument("--out", type=Path, help="Also write the report here")
    args = parser.parse_args()
    text = report(*audit(find_replays(args.inputs), args.examples))
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
