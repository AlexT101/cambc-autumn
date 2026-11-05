"""Economic decision episodes from econ_rows output (ECONOMY.md).

    python3 tools/fish/econ_episodes.py OUT.jsonl.gz [--rows replays/fish-econ/rows-v3.jsonl.gz]

Kinds, one JSON line each; `x` holds only the actor's turn-start (causal) state, `y` the label
from later frames:
  payout   turn start right after the actor's own capture share (gems or gold rose while it
           stood on the group tile it ended its last turn on), off spawn. y.end: first of
           farm (camp hit or another empty group occupied), home (completed arrival, by recall or
           walk), trib (successful tribute start), dead, timeout (60 rounds); y.enemy: an enemy
           seen in any context between the episode start and that endpoint.
  t1       a recall channel at timer 1 at turn start (its last cancel opportunity), off spawn,
           alive, unstunned. y.keep (no cancel), y.arrive (next turn starts on spawn).
  t4       the same at timer 4 (the first keep decision of a prepared recall). y.keep, y.arrive
           (this channel completes), y.interrupted.
  arrival  every completed home arrival. x: state at the chain's timer-4 turn (recall) or at the
           start of the monotone walk (walk); y.kind recall/walk, y.next: the next camp group hit
           after leaving spawn.
  trib     every successful tribute start; x at that turn start plus the approach start.
  adj      turn starts within 1 of an altar with gems, not channelling a tribute, tribute start
           unused this round; y.start (a successful tribute start this turn).
Refuses to overwrite OUT.
"""
import argparse, gzip, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from econ_common import games, home_events, MOVE, RECALL, CANCEL, WARD, BLOCKED, LOCK, TRIB_OK, TELE, ROWS  # noqa: E402

QUIET = MOVE | RECALL | CANCEL | WARD | BLOCKED | LOCK
X = ('r', 'x', 'y', 'hp', 'maxhp', 'gems', 'gold', 'ch', 'tm', 'ne', 'ned', 'nal', 'al_gems', 'al_trib', 'al_trib_gems',
     'al_recall_gems', 'home_walk', 'alt_walk', 'alt_idx', 'alt_cheb', 'grp', 'gstate', 'gteam', 'gtimer',
     'score_own', 'score_opp', 'camps_live_near', 'awake_near', 'shards', 'ready', 'ready_walk', 'ready_wait',
     'ready_grp', 'ready_gold', 'ready_gems', 'n_ready10', 'own_resp', 'ready_home', 'ready_home_grp')


def feat(r):
    return {k: getattr(r, k) for k in X}


def endpoint(rows, i, arr):
    r0 = rows[i]
    enemy = False
    for k in range(i, len(rows)):
        q = rows[k]
        if q.r > r0.r + 60:
            return dict(end='timeout', enemy=enemy)
        if not q.alive:
            return dict(end='dead', at=q.r, enemy=enemy)
        if k in arr and k > i:
            return dict(end='home', mode=arr[k]['kind'], at=q.r, enemy=enemy)
        enemy |= q.ne_any > 0
        if q.acts & TRIB_OK:
            return dict(end='trib', at=q.r, enemy=enemy)
        if q.hit is not None or (k > i and q.gstate == 2 and q.grp != r0.grp):
            return dict(end='farm', at=q.r, group=q.hit if q.hit is not None else q.grp, enemy=enemy)
    return dict(end='censored', enemy=enemy)


def walk_start(rows, a):
    """First turn of the monotone, quiet walk that ends on spawn at arrival index a."""
    j = a - 1
    while j - 1 >= 0:
        q = rows[j - 1]
        if not q.alive or q.home_walk in (0, None) or q.acts & ~QUIET or q.ch in (2, 3):
            break
        if not (rows[j].home_walk is not None and rows[j].home_walk < q.home_walk):
            break
        j -= 1
    return j


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out'); p.add_argument('--rows', default=ROWS)
    a = p.parse_args()
    if os.path.exists(a.out): sys.exit(f'refusing to overwrite {a.out}')
    n = 0
    with gzip.open(a.out + '.part', 'wt') as out:
        def emit(kind, g, aid, x, y):
            nonlocal n
            out.write(json.dumps(dict(kind=kind, cohort=g['cohort'], game=g['game'], group=g['group'], map=g['map'],
                                      actor=aid, type=g['names'][aid], n=g['n'], n_altars=len(g['altars']), x=x, y=y), separators=(',', ':')) + '\n')
            n += 1
        for g in games(a.rows):
            for aid, rows in g['actors'].items():
                evs = home_events(rows)
                arr = {e['arrive']: e for e in evs}
                for i in range(1, len(rows)):
                    p_, r = rows[i - 1], rows[i]
                    ok = r.alive and not r.stun and r.fin == 'End turn' and r.home_walk not in (0, None)
                    if ok and p_.alive and p_.ealive and (r.x, r.y) == (p_.ex, p_.ey) and p_.grp is not None \
                            and (r.gems > p_.egems or r.gold > p_.egold):
                        emit('payout', g, aid, feat(r) | dict(dgems=r.gems - p_.egems, dgold=r.gold - p_.egold), endpoint(rows, i, arr))
                    if ok and r.ch == 1 and r.tm in (1, 4) and i + 1 < len(rows):
                        keep = not r.acts & CANCEL
                        if r.tm == 1:
                            nx = rows[i + 1]
                            emit('t1', g, aid, feat(r), dict(keep=keep, arrive=keep and nx.alive and nx.home_walk == 0))
                        else:
                            done = any(e['kind'] == 'recall' and e['i4'] == i for e in evs)
                            # interrupted: kept, but a later turn of the chain has no channel
                            intr = False
                            if keep and not done:
                                for k in range(i + 1, min(i + 4, len(rows))):
                                    q = rows[k]
                                    if not q.alive or q.ch != 1:
                                        intr = True; break
                                    if q.acts & CANCEL: break
                            emit('t4', g, aid, feat(r), dict(keep=keep, arrive=done, interrupted=intr))
                    if r.alive and r.alt_cheb is not None and r.alt_cheb <= 1 and r.gems > 0 and r.ch != 2 \
                            and not r.stun and not r.flags & 128 and r.fin == 'End turn':
                        emit('adj', g, aid, feat(r), dict(start=bool(r.acts & TRIB_OK)))
                    if r.alive and r.acts & TRIB_OK:
                        j = i
                        while j - 1 >= 0 and rows[j - 1].alive and not rows[j - 1].acts & ~QUIET and rows[j - 1].ch != 2 \
                                and rows[j - 1].alt_walk is not None and rows[j].alt_walk is not None and rows[j].alt_walk <= rows[j - 1].alt_walk:
                            j -= 1
                        emit('trib', g, aid, feat(r) | dict(sub_gems=r.sub_gems, prior_payout=None),
                             dict(approach=i - j, approach_x=feat(rows[j])))
                for e in evs:
                    k0 = e['i4'] if e['kind'] == 'recall' else walk_start(rows, e['arrive'])
                    x = feat(rows[k0])
                    if e['kind'] == 'recall':
                        x['t1'] = feat(rows[e['i1']])
                        x['start_acts'] = rows[e['start']].acts
                        x['start_hp'] = rows[e['start']].hp
                    nxt = None
                    for k in range(e['arrive'], min(len(rows), e['arrive'] + 80)):
                        q = rows[k]
                        if not q.alive: break
                        if q.hit is not None:
                            nxt = dict(group=q.hit, at=q.r); break
                    emit('arrival', g, aid, x, dict(kind=e['kind'], at=rows[e['arrive']].r, next=nxt,
                                                    gold_arrive=rows[e['arrive']].gold, spent=rows[e['arrive']].spent))
    os.rename(a.out + '.part', a.out)
    print(f'{n} episodes -> {a.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
