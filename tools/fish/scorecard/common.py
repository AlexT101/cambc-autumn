"""Datasets of the Fish fidelity scorecard: where each part's manifest and caches live.

A dataset is a list of parts. Each part is a set of games whose replay hashes are unique within it,
with one side marked as Fish's ("Fish's role"): a pinned Fish ladder cohort, or one side (A or B) of a
local batch. Splitting a local batch by side keeps the caches, which are keyed by replay hash, apart
when a mirror match writes byte-identical replays for both sides.

  fish             = fish-seventh + fish-fifth + fish-sixth (the default Fish column)
  fish-<cohort>    = one pinned cohort (model, confirm, third, fourth, fifth, sixth, seventh)
  <name>           = a local dataset made by build.py under replays/fish-scorecard/<name>/
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tools/fish

ROOT = Path('replays/fish-scorecard')
RES = Path('research/fish-2026-11-05')
FISH_COHORTS = {
    'model': 'manifest.json', 'confirm': 'confirmation-manifest.json', 'third': 'third-manifest.json',
    'fourth': 'fourth-manifest.json', 'fifth': 'fifth-manifest.json', 'sixth': 'sixth-manifest.json',
    'seventh': 'seventh-manifest.json',
}
FISH_DEFAULT = ['seventh', 'fifth', 'sixth']


def fish_part(cohort):
    team = 'replays/fish-engage/team-seventh' if cohort == 'seventh' else 'replays/fish-team'
    return dict(dataset='fish', part=cohort, manifest=str(RES / FISH_COHORTS[cohort]), actor=f'replays/fish-{cohort}',
                team=team, obs=str(ROOT / 'fish-obs'),
                engage=f'replays/fish-engage/{cohort}-rows-v1.jsonl.gz',
                combat=f'replays/fish-combat/{cohort}-combat-v2.jsonl.gz',
                tiles=f'replays/fish-combat/{cohort}-tiles-v1.jsonl.gz')


def local_part(name, part):
    d = ROOT / name / part
    return dict(dataset=name, part=part, manifest=str(d / 'manifest.json'), actor=str(d / 'actor'), team=str(d / 'team'),
                obs=str(d / 'obs'), engage=str(d / 'engage-rows-v1.jsonl.gz'), combat=str(d / 'combat-v2.jsonl.gz'),
                tiles=str(d / 'tiles-v1.jsonl.gz'))


def parts(name):
    """Parts of one dataset name (see module doc); a comma list concatenates datasets."""
    out = []
    for n in name.split(','):
        if n == 'fish':
            out += [fish_part(c) for c in FISH_DEFAULT]
        elif n.startswith('fish-') and n[5:] in FISH_COHORTS:
            out.append(fish_part(n[5:]))
        else:
            meta = ROOT / n / 'dataset.json'
            if not meta.exists():
                raise SystemExit(f'unknown dataset {n}: no {meta} (make it with tools/fish/scorecard/build.py)')
            out += [local_part(n, p) for p in json.loads(meta.read_text())['parts']]
    return out


def entries(part):
    return json.loads(Path(part['manifest']).read_text())
