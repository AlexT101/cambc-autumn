"""Freeze prospective inputs only; no games, map generation or compilation."""
import json
import shutil
from run import R, D, OLD, T, BASE, CAND, BODY, CONFIGS, sha, source, write, config_for


def main():
    D.mkdir(exist_ok=True)
    for arm in CAND:
        src = R.parent / 'tmp-offload/localq/reservations' / ('cond-runtime-' + arm) / 'seeds.json'
        shutil.copyfile(src, D / ('seeds-' + arm + '.json'))
        (D / arm).mkdir(exist_ok=True)
    smoke = json.loads((OLD / 'smoke-maps.json').read_text())
    write(D / 'smoke-maps.json', smoke)
    write(D / 'smoke-config.json', config_for([{'name': __import__('pathlib').Path(row['path']).stem,
                                              'sha256': sha(row['path'])} for row in smoke]))
    ladder = [{'name': p.stem, 'path': str(p), 'sha256': sha(p)} for p in sorted((R / 'maps').glob('*.map26a'))]
    assert len(ladder) == 128
    write(D / 'ladder-maps.json', ladder)
    write(D / 'ladder-config.json', config_for(ladder))
    write(D / 'protocol.json', {'namespace': 'conditional-batch506', 'base': BASE, 'candidates': CAND, 'replicas': BODY,
          'our_turn_fuel': 200000, 'opponent_unmetered': True, 'game_timeout_seconds': 120,
          'timeout_policy': 'Per-game ownedworker watchdog afterprecompile; anytimeout failsclosed/no retry or resultclaim',
          'panels': 4, 'maps_per_panel': 10240, 'ab_games_per_panel': 20480,
          'fresh_games_used_per_arm': 327680, 'fresh_games_new': {'chanM': 327680, 'bagfF': 163840},
          'shared_controls': 'Prospective sharedChanMpanels/configs/reference games; correlatedarmestimates; Fishreservationunused',
          'configs': CONFIGS, 'seed_assignment': 'Within panel sort by map SHA/name then index modulo8',
          'map_generation': '8 independent pooled1 serial-node suite processes; merge reservedseed/path order; byte novelty, no outcomes',
          'decision': 'One fixed final map-cluster95%read; target lower>0; off-target lower>-.0025; otherwise unresolved or negative/harm',
          'ladder': '128maps/bothsides/two replicas/candidate+reference, once only',
          'mirror': 'Existing prospectivelyauthorized8192maps/bothsides/Ocean506, bothteams200k; chanM reuse admitted beforeoutcomes',
          'no_pooling': 'Old stopped conditional gate is unresolved; do not combine old replica results',
          'ordering': 'ChanM coordinatorreview thenFish coordinatorreview then draft17 then tune8; no automatic100k or merges',
          'resources': '4 ABcontrollers, native matches share86slots; only2 reusable replica bodies; no noise-specific compilation'})
    print('Prepared inputs; runtime validation proof and final seal still required before admission.')


if __name__ == '__main__':
    main()
