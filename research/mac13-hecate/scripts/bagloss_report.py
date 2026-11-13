"""Report for bagloss.py's JSON: trace-side deaths by class, per game, weighted by gems lost; Prism and first-Prism deaths.
Usage: bagloss_report.py rows.json [--examples N]"""
import sys, json, collections

res = json.load(open(sys.argv[1]))
NEX = int(sys.argv[sys.argv.index('--examples') + 1]) if '--examples' in sys.argv else 3
G = len(res)
BR = {'R': 'retreat', 'E': 'stop_game_ender', 'T': 'tribute', 't': 'tribute', 'P': 'hold', 'X': 'contest', 'A': 'attack', 'C': 'chase',
      'F': 'farm', 'B': 'bank', 'K': 'recall', 'k': 'recall', 'H': 'mend', 'G': 'siege', 'W': 'wait_altar', 'U': 'guard_altar',
      'S': 'shop', 'Q': 'capture_recall', 'h': 'willow', 'r': 'prism_recovery', '-': 'none'}


def unseen_why(x):
    if x.get('k_bush'):
        return 'killer in a bush'
    v, t = x.get('v_saw_ago'), x.get('t_saw_ago')
    if v is not None and v <= 3:
        return 'victim saw it <=3 rounds ago'
    if t is not None and t <= 3:
        return 'only a teammate saw it <=3 rounds ago'
    if v is not None and v <= 20:
        return 'victim saw it 4-20 rounds ago'
    return 'not seen by the victim for 20+ rounds'


def retreat_tag(x):
    # the retreat's start: its first R turn in the run of R turns up to the death, and its verdicts then
    h = x.get('hist', [])
    j = len(h)
    while j > 0 and h[j - 1][1] == 'R':
        j -= 1
    if j == len(h):
        return ''
    start = h[j]
    n = len(h) - j
    why = {'s': 'stand lost', 'z': 'pack zone', 'l': 'recall line'}.get(start[3], 'other')
    return f" [began {'lethal' if start[2] else 'safe'} ({why})" + (f", {('1' if n == 1 else '2-4' if n <= 4 else '5+')} turns" if '--turns' in sys.argv else '') + ']'


def classify(x):
    if x.get('cls') == 'camp':
        return 'camp kill'
    if x.get('cls') == 'noturn':
        return 'no traced turn'
    if not x.get('bl'):
        return 'unseen (no V/T enemy within 10): ' + unseen_why(x)
    kt = x.get('ktok')
    line = x.get('dec_line') if x.get('stunned_last') and x.get('dec_line') else x['bl_line']
    ktd = x.get('dec_ktok') if x.get('stunned_last') and x.get('dec_line') else kt
    if kt is None or kt['kind'] == 'N':
        if ktd and ktd['kind'] == 'V':
            pass  # seen at the decision turn before a stun: judged below
        else:
            return 'unseen (killer untracked, others believed): ' + unseen_why(x)
    elif kt['kind'] == 'T':
        return 'unseen: killer tracked but out of sight'
    stun = '' if not x.get('stunned_last') else 'stunned last turn; '
    if line['lethal']:
        br = BR.get(line['br'], line['br'])
        if line['br'] == 'R':
            e = line.get('esc')
            return f"{stun}lethal: retreat " + (('(escape plan: no clear way)' if e and min(e) >= 1 else '(escape plan clear)' if e else '(no escape plan)') if '--esc' in sys.argv else '') + retreat_tag(x)
        return f"{stun}lethal: acted anyway ({br})"
    # model: not lethal
    att = [a for a in x.get('attackers', []) if a is not None]
    if x.get('stunned_last'):
        return 'safe-said: stunned last turn (stun then kill)'
    if x.get('stun_in_win') and x.get('k_turns', 0) >= 1 and len(att) >= 1 and x.get('all_dmg', 0) > 0:
        tag = 'stun in window'
    else:
        tag = ''
    if x.get('k_turns', 0) >= 2:
        return 'safe-said: killer had 2 turns before ours (turn order)'
    if len(att) >= 2:
        return 'safe-said: several attackers' + (' (one unbelieved)' if any(a not in x.get('believed', att) for a in att) else '')
    blow = ktd['blow'] if ktd else -1
    if blow >= 0 and x.get('k_dmg', 0) > blow + 1:
        return 'safe-said: killer blow under-predicted'
    return 'safe-said: other' + (f' ({tag})' if tag else '')


def main():
    allrows = [r for g in res for r in g['rows']]
    rows = [r for r in allrows if r.get('cls') != 'truncated']
    trunc = sum(1 for g in res if g.get('trunc'))
    print(f'deaths after a truncated trace (left out): {len(allrows) - len(rows)}, gems {sum(r["gems"] for r in allrows) - sum(r["gems"] for r in rows)}')
    for r in rows:
        r['class'] = classify(r)
    print(f'games {G}, truncated trace stdout {trunc}; trace-side deaths {len(rows)} ({len(rows)/G:.2f}/game), gems lost {sum(r["gems"] for r in rows)/G:.1f}/game')
    def table(sel, title):
        c = collections.Counter(); gm = collections.Counter()
        for r in sel:
            c[r['class']] += 1; gm[r['class']] += r['gems']
        tg = sum(gm.values()) or 1
        print(f'\n## {title}: {len(sel)} deaths ({len(sel)/G:.3f}/game), {sum(gm.values())/G:.1f} gems/game')
        print(f'{"class":75s} {"deaths/g":>8s} {"gems/g":>7s} {"gem%":>5s} {"mean bag":>8s}')
        for k, v in sorted(gm.items(), key=lambda kv: -kv[1]):
            print(f'{k:75s} {c[k]/G:8.3f} {v/G:7.1f} {100*v/tg:5.1f} {v/c[k]:8.1f}')
    # pair: a linked death is the same event as its partner's; gems count for both bodies
    table(rows, 'All deaths (bodies)')
    table([r for r in rows if r['vname'] == 'Prism'], 'Prism deaths')
    table([r for r in rows if r.get('first_prism')], 'First Prism death of each game')
    table([r for r in rows if r['gems'] >= 50], 'Deaths with 50+ gems')
    # turn ends by verdict and branch: share followed by this champion's death within a round
    st = collections.Counter()
    for g in res:
        st.update(g['st'])
    print('\n## Traced turn ends (BL) by lethal verdict and branch: per game, and died by the next round')
    for L in ('L1', 'L0'):
        print(f"{L}: {st[L]/G:.1f}/game, died {st[L+'_die']/max(1,st[L]):.3f}")
        brs = sorted({k[len(L)+3:].replace('_die','') for k in st if k.startswith(L+'_br')}, key=lambda b: -st[f'{L}_br{b}'])
        for b in brs:
            n = st[f'{L}_br{b}']
            if n / G >= 0.2: print(f"   {BR.get(b, b):16s} {n/G:7.1f}/game died {st[f'{L}_br{b}_die']/n:.3f} ({st[f'{L}_br{b}_die']/G:.2f}/game)")
    # examples
    by = collections.defaultdict(list)
    for r in rows:
        by[r['class']].append(r)
    print('\n## Examples (largest bags)')
    for k, v in sorted(by.items(), key=lambda kv: -sum(r['gems'] for r in kv[1])):
        print(f'\n### {k}')
        for r in sorted(v, key=lambda r: -r['gems'])[:NEX]:
            print(f"- {r['src']} r{r['r']} victim {r['vname']}#{r['v']}{' (linked to #'+str(r['linked'])+')' if r.get('linked') is not None else ''} "
                  f"bag {r['gems']} by {r.get('kname')}#{r.get('by')} ({r.get('cause')}); last turn r{r.get('last')} {r.get('last_br')}; "
                  f"window attackers {r.get('attackers')} killer turns {r.get('k_turns')} killer dmg {r.get('k_dmg', 0):.0f} all {r.get('all_dmg', 0):.0f} "
                  f"camp {r.get('camp_dmg', 0):.0f} stun {r.get('stun_in_win')}; killer true dist {r.get('kd_true')} seen by victim {r.get('k_seen_by_v')} "
                  f"team {r.get('k_seen_by_team')}; Focus k/v {r.get('k_foc')}/{r.get('v_foc')}; killer V in victim lines {r.get('k_V_rounds')} of 40")
            for l in r.get('raw_hist', []):
                print(f'    BL {l}')


if __name__ == '__main__':
    main()
