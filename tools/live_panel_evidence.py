"""Context-matched live comparison; drafts are treatment outcomes, never filters."""
import math
import statistics


def paired(ls, baseline, candidate, opponent, source, refset):
    tasks, created, finished, dropped, _ = ls.state()
    tasks = {t['id']: t for t in tasks}
    bad = ls.suspect_groups()
    arms = {baseline: {}, candidate: {}}
    for r in ls.read_jsonl(ls.DATA / 'games.jsonl'):
        v = r.get('version')
        if (v not in arms or r.get('opp_id') != opponent or r.get('refset') != refset
                or r.get('purpose') != 'set' or r.get('filler')):
            continue
        t, e = tasks.get(r['task']), created.get(r['task'])
        if (not t or not e or t['id'] in dropped or e['group'] not in finished
                or e['group'] in bad or r['group'] != e['group']):
            continue
        actual_source = e.get('source_group') or (e['group'] if e.get('is_ref') else None)
        if (actual_source != source or e.get('live') != v or e.get('selected') != v
                or e.get('opp_id') != opponent or r.get('status') != 'finished'
                or r.get('result') not in ('win', 'loss')):
            raise ValueError('panel row has invalid selection/source/result context')
        if not r.get('engine') or not r.get('engine_hash') or r.get('seed') is None:
            raise ValueError('panel row missing engine/seed context')
        key = (r['map_id'], r['side'])
        if key in arms[v] and arms[v][key] != r:
            # Repeated same context can be reused, but conflicting outcomes cannot.
            old = arms[v][key]
            if any(old.get(f) != r.get(f) for f in ('result', 'engine', 'engine_hash', 'seed', 'our_picks', 'opp_picks')):
                raise ValueError('conflicting repeated panel cell')
        arms[v][key] = r
    if len(arms[baseline]) != 256 or arms[baseline].keys() != arms[candidate].keys():
        raise ValueError('comparison requires complete256 matching cells for each own version')
    maps, flips, draft_changes = {}, {'candidate_only': 0, 'baseline_only': 0}, {'ours': 0, 'opponent': 0}
    wins = [0, 0]
    for key, a in arms[baseline].items():
        b = arms[candidate][key]
        if any(a[f] != b[f] for f in ('engine', 'engine_hash', 'seed')):
            raise ValueError('paired cell crosses engine or deterministic seed')
        aw, bw = a['result'] == 'win', b['result'] == 'win'
        wins[0] += aw; wins[1] += bw
        flips['candidate_only'] += bw and not aw
        flips['baseline_only'] += aw and not bw
        draft_changes['ours'] += a.get('our_picks') != b.get('our_picks')
        draft_changes['opponent'] += a.get('opp_picks') != b.get('opp_picks')
        maps.setdefault(key[0], {})[key[1]] = int(bw) - int(aw)
    if len(maps) != 128 or any(set(x) != {'a', 'b'} for x in maps.values()):
        raise ValueError('comparison must have128 maps on both sides')
    diffs = [statistics.mean(x.values()) for x in maps.values()]
    mean = statistics.mean(diffs)
    half = 1.96 * statistics.stdev(diffs) / math.sqrt(len(diffs))
    return {'baseline': baseline, 'candidate': candidate, 'opponent': opponent, 'source_group': source,
            'refset': refset, 'maps': 128, 'cells': 256, 'baseline_wins': wins[0], 'candidate_wins': wins[1],
            'gain': mean, 'ci95': [mean-half, mean+half], 'flips': flips,
            'draft_changes_descriptive_only': draft_changes,
            'engine_contexts': sorted({(r['engine'], r['engine_hash']) for r in arms[baseline].values()}),
            'zero_discordance': not any(flips.values()),
            'uncertainty': ('paired-map normal95% interval on fixed published pool; no draft conditioning'
                            + ('; zero estimated map variance describes finite observed agreement, not proof of zero uncertainty'
                               if half == 0 else ''))}


def needs_discernment(fish, mite):
    return (any(r['ci95'][0] <= 0 <= r['ci95'][1] for r in (fish, mite))
            or fish['gain'] * mite['gain'] < 0)
