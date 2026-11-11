"""Validate every planned cell/configuration and publish only the fixed-allocation read."""
import argparse
import json
from pathlib import Path
from run import R, D, BASE, CAND, BODY, sha, source, verify, verify_maps, batch_name, write, validate_receipt
from stats import cells, paired, interval, decision


def read_batch(name, bot, body, expected, config_path):
    path = R / 'replays/ab' / name / 'summary.json'
    result = json.loads(path.read_text())
    games = len(expected) * 2
    assert result['games'] == games and result['errors'] == 0 and result['release'] is True
    assert result['fuel'] == 200000 and result['cambc'] == '5.0.1'
    assert result['game_timeout'] == 120
    assert result['cand']['spec'] == bot and result['ref']['spec'] == body
    assert result['experiment_config']['sha256'] == sha(config_path)
    config = json.loads(config_path.read_text())['maps']
    rows = []
    batches = {}
    for suite in result['suites']:
        bp = R / suite['batch'] / 'results.json'
        batch = json.loads(bp.read_text())
        assert batch['scheduled'] == batch['completed'] == games and batch['errors'] == 0
        assert batch['fuel'] == 200000 and batch['release'] is True
        assert batch['game_timeout'] == 120
        assert batch['experiment_config']['sha256'] == sha(config_path)
        for row in batch['matches']:
            wanted = {side: config[Path(row['map']).stem] if logical == 1 else None
                      for side, logical in zip(('a', 'b'), row['order'])}
            assert row['runtime_config'] == wanted, ('Wrong per-team runtime config', name)
            rows.append(row)
        batches[str(bp)] = sha(bp)
    values = cells(rows, expected)
    return values, {'name': name, 'summary_sha256': sha(path), 'batches': batches,
                    'draft_counts': {k: result.get(k) for k in ('early_losses', 'handoff_failures', 'capped_drafts')}}


def panel(arm, index, rows):
    expected = {row['name'] for row in rows if row['panel'] == index}
    assert len(expected) == 10240
    config = D / 'chanM' / ('config-' + str(index) + '.json')
    audits = []
    values = {}
    for body in 'FM':
        observations = {}
        for label, bot in [('cand', CAND[arm]), ('base', BASE)]:
            name = batch_name(arm, 'p' + str(index), label, body)
            observations[label], audit = read_batch(name, bot, BODY[body], expected, config)
            audit['provenance_sha256'] = validate_receipt(name, bot, BODY[body], D / 'chanM/pool' / str(index), config)
            audits.append(audit)
        values[body] = paired(observations['cand'], observations['base'])
    return values, audits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=CAND)
    parser.add_argument('--validate-panel', type=int, choices=range(4))
    args = parser.parse_args()
    manifest = verify()
    rows = verify_maps(args.arm)
    if args.validate_panel is not None:
        _, audit = panel(args.arm, args.validate_panel, rows)
        write(D / args.arm / ('panel-' + str(args.validate_panel) + '-validated.json'), {'audit': audit})
        return
    values = {'F': {}, 'M': {}}
    audits = []
    for index in range(4):
        block, audit = panel(args.arm, index, rows)
        for body in 'FM':
            assert not values[body].keys() & block[body].keys()
            values[body].update(block[body])
        audits.extend(audit)
    assert all(len(values[b]) == 40960 for b in 'FM')
    features = {x['name']: x for x in map(json.loads, (D / 'chanM' / 'features.jsonl').read_text().splitlines())}
    config = {}
    for index in range(4):
        config.update(json.loads((D / 'chanM' / ('config-' + str(index) + '.json')).read_text())['maps'])
    stats = {body: interval(list(values[body].values())) for body in 'FM'}
    diagnostic = {body: {'by_salt': {str(salt): interval([v for m, v in values[body].items() if config[m]['salt'] == salt])
                                   for salt in sorted({v['salt'] for v in config.values()})},
                         'by_pickcount': {str(n): interval([v for m, v in values[body].items() if features[m]['picks'] == n])
                                          for n in sorted({features[m]['picks'] for m in values[body]})}}
                  for body in 'FM'}
    ladder = {}
    names = {p.stem for p in (R / 'maps').glob('*.map26a')}
    assert len(names) == 128
    for body in 'FM':
        observations = {}
        for label, bot in [('cand', CAND[args.arm]), ('base', BASE)]:
            observations[label], audit = read_batch(batch_name(args.arm, 'ladder', label, body), bot, BODY[body],
                                                    names, D / 'ladder-config.json')
            audit['provenance_sha256'] = validate_receipt(batch_name(args.arm, 'ladder', label, body), bot, BODY[body],
                                                        R / 'maps', D / 'ladder-config.json')
            audits.append(audit)
        ladder[body] = interval(list(paired(observations['cand'], observations['base']).values()))
    on, off = ('M', 'F') if args.arm == 'chanM' else ('F', 'M')
    totals = {}
    for audit in audits:
        for key, count in audit['draft_counts'].items():
            if isinstance(count, dict):
                totals[key] = totals.get(key, 0) + sum(v for v in count.values() if isinstance(v, (int, float)))
    verify()
    result = {'arm': args.arm, 'candidate': CAND[args.arm], 'reference': BASE, 'our_turn_fuel': 200000,
              'game_timeout_seconds': 120,
              'runtime': manifest['runtime'],
              'opponent_unmetered': True, 'fresh_games_used': 327680, 'fresh_games_new': 327680 if args.arm == 'chanM' else 163840,
              'shared_reference_games': 163840, 'fresh_maps': 40960, 'fresh': stats,
              'target': on, 'offtarget': off, 'outcome': decision(stats[on], stats[off]),
              'diagnostics': diagnostic, 'ladder': ladder, 'audit': audits, 'draft_counts_total': totals,
              'candidate_sources': {bot: source(bot) for bot in (BASE, CAND[args.arm])},
              'manifest_sha256': sha(D / 'manifest.json'), 'maps_manifest_sha256': sha(D / 'chanM' / 'maps.json'),
              'shared_control_caveat': 'Arms share maps/configurations/506control outcomes prospectively; their estimates are correlated, not independent replications.',
              'scope': 'Fixed final map-cluster read; eight runtime configurations. No old-gate pooling, automatic extension,100k run or merge.'}
    write(D / args.arm / 'map-paired-values.json', values)
    result['map_values_sha256'] = sha(D / args.arm / 'map-paired-values.json')
    write(D / args.arm / 'result-200000.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
