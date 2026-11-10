"""Rolling opponent behavior snapshots, separate from the fixed live-test pins.

No API calls: schedule ordinary oppcheck tasks and inspect the runner's saved results.
A changed five-cell comparison advances only this detector's source-group snapshot.
"""
import hashlib
import json

LEGACY_BOOTSTRAP_MAX_VERSION = 112

FIELDS = ('result', 'rounds', 'our_gems', 'opp_gems', 'our_kills', 'opp_kills', 'our_picks', 'opp_picks')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class InvalidComparison(ValueError):
    pass


class Evidence:
    def __init__(self, ls):
        tasks, self.created, self.finished, self.dropped, self.refs = ls.state()
        self.tasks = {t['id']: t for t in tasks}
        self.suspect = ls.suspect_groups()
        self.rows = {}
        for row in ls.read_jsonl(ls.DATA / 'games.jsonl'):
            self.rows.setdefault(row['task'], []).append(row)

    def group(self, tid):
        """None while incomplete; invalid evidence never becomes a change notification."""
        if tid in self.dropped:
            raise InvalidComparison(f'dropped task {tid}')
        task, ev = self.tasks.get(tid), self.created.get(tid)
        if task is None or ev is None or ev['group'] not in self.finished:
            return None
        if ev['group'] in self.suspect:
            raise InvalidComparison(f'suspect group {ev["group"]}')
        if ev.get('live') != task['version'] or ev.get('selected') != task['version'] or ev.get('opp_id') != task['opp_id']:
            raise InvalidComparison('own version changed at creation')
        expected = {(i, g['map_id'], g['map'], g['side']) for i, g in enumerate(task['games'], 1)}
        if len(task['games']) != 5 or len({g['map_id'] for g in task['games']}) != 5:
            raise InvalidComparison('expected exactly five distinct cells')
        cells = {}
        for row in self.rows.get(tid, []):
            if row.get('group') != ev['group']:
                raise InvalidComparison('multiple groups recorded for task')
            key = (row.get('position'), row.get('map_id'), row.get('map'), row.get('side'))
            if key not in expected or row.get('version') != task['version'] or row.get('opp_id') != task['opp_id']:
                raise InvalidComparison('wrong map, side, opponent or own version')
            if row.get('status') != 'finished' or row.get('result') not in ('win', 'loss'):
                raise InvalidComparison('failed or unfinished match')
            if (row.get('source_group') != ev.get('source_group') or row.get('pin') != task.get('pin')
                    or row.get('purpose') != task.get('purpose') or row.get('refset') != task.get('refset')):
                raise InvalidComparison('row/source provenance differs from created task')
            if any(row.get(f) is None for f in FIELDS) or not row.get('engine') or not row.get('engine_hash'):
                raise InvalidComparison('missing comparison metrics or engine identity')
            if row.get('seed') is None:
                raise InvalidComparison('missing deterministic game seed')
            if not row.get('match') or not row['our_picks'] or not row['opp_picks']:
                raise InvalidComparison('missing ordered drafts')
            normalized = {f: row[f] for f in (*FIELDS, 'engine', 'engine_hash', 'seed', 'match')}
            if key in cells and cells[key] != normalized:
                raise InvalidComparison('conflicting duplicate cell')
            cells[key] = normalized
        if set(cells) != expected:
            return None  # Collection can be interrupted between its five append-only rows.
        return {'task': task, 'created': ev, 'cells': cells,
                'fingerprint': digest([[list(k), v] for k, v in sorted(cells.items())])}


def compare(base, current):
    if base['task']['version'] != current['task']['version'] or base['task']['opp_id'] != current['task']['opp_id']:
        raise InvalidComparison('comparison crosses own versions or opponents')
    if base['cells'].keys() != current['cells'].keys():
        raise InvalidComparison('comparison cells differ')
    changed = []
    for key, row in current['cells'].items():
        old = base['cells'][key]
        if (row['engine'], row['engine_hash']) != (old['engine'], old['engine_hash']):
            raise InvalidComparison('comparison crosses engine builds')
        if row['seed'] != old['seed']:
            raise InvalidComparison('comparison crosses deterministic game seeds')
        if any(row[f] != old[f] for f in FIELDS):
            changed.append(f'{key[2]}/{key[3]}')
    return sorted(changed)


class OpponentDetector:
    def __init__(self, ls, save, log, wake, now):
        self.ls, self.save, self.log, self.wake, self.now = ls, save, log, wake, now

    def bootstrap(self, st, evidence):
        if 'opp_detector' in st:
            return
        detector = {'schema': 1, 'snapshots': {}, 'runs': {}, 'outbox': {}, 'migration': {'at': self.now(), 'observations': []}}
        for opp in ('fish', 'mite'):
            oid = self.ls.TEAMS[opp][0]
            choices = sorted((t for t in evidence.tasks.values() if t['opp_id'] == oid
                              and t.get('purpose') == 'oppcheck' and t.get('pin') == 'none'
                              and t['id'].endswith('-cur') and t['version'] <= LEGACY_BOOTSTRAP_MAX_VERSION
                              and t['id'] in st.get('opp_checks', {})),
                             key=lambda t: (t['version'], t.get('planned', '')), reverse=True)
            for task in choices:
                try:
                    cur = evidence.group(task['id']); base = evidence.group(task['id'][:-4])
                    if cur is None or base is None:
                        continue
                    if cur['created'].get('source_group') is not None or base['task'].get('pin') != 'ref':
                        raise InvalidComparison('legacy pair is not current versus testing pin')
                    changed = compare(base, cur)
                except InvalidComparison:
                    continue
                source = cur['created']['group'] if changed else (base['created'].get('source_group') or base['created']['group'])
                detector['snapshots'][opp] = {'source_group': source, 'observation_task': task['id'],
                    'observation_version': task['version'], 'observed_at': cur['created']['at'],
                    'fingerprint': cur['fingerprint'], 'generation': 0,
                    'equivalent_test_source': None if changed else source}
                detector['migration']['observations'].append({'opponent': opp, 'task': task['id'], 'source_group': source,
                    'through_version': task['version'], 'note': 'Starting observation only; legacy comparisons cannot establish additional intervening uploads.'})
                break
        st['opp_detector'] = detector
        self.save(st)
        self.log('opp-detector initialized from latest valid saved observations; testing pins unchanged; no new upload-count claim')

    def finish(self, st, evidence):
        d = st['opp_detector']
        for key, run in d['runs'].items():
            if run['status'] != 'pending':
                continue
            try:
                base = evidence.group(run['baseline_task']); cur = evidence.group(run['current_task'])
                if base is None or cur is None:
                    continue
                if (base['created'].get('source_group') or base['created']['group']) != run['snapshot_group']:
                    raise InvalidComparison('baseline did not use captured detector snapshot')
                if cur['created'].get('source_group') is not None or cur['task'].get('pin') != 'none':
                    raise InvalidComparison('current observation was pinned')
                changed = compare(base, cur)
                snapshot = d['snapshots'].get(run['opponent'])
                if snapshot and snapshot['source_group'] != run['snapshot_group']:
                    raise InvalidComparison('superseded comparison snapshot')
            except InvalidComparison as exc:
                run.update(status='invalid', reason=str(exc), completed_at=self.now())
                self.save(st); self.log(f'opp-check invalid {key}: {exc}; detector snapshot unchanged')
                continue
            rec = {'ev': 'opp-check', 'event_id': f'opp-observation-{key}', 'at': self.now(), 'task': run['current_task'],
                   'opponent': cur['task']['opp_name'], 'version': run['version'], 'changed': bool(changed), 'maps': changed,
                   'comparison': 'rolling observed behavior snapshot', 'previous_snapshot': run['snapshot_group'],
                   'baseline_task': run['baseline_task'], 'baseline_group': base['created']['group'],
                   'current_group': cur['created']['group'], 'baseline_fingerprint': base['fingerprint'],
                   'current_fingerprint': cur['fingerprint'], 'testing_pins_unchanged': True,
                   'note': 'Observed behavior difference on five matched cells, not an inferred upload count.'}
            if changed:
                d['snapshots'][run['opponent']] = {'source_group': cur['created']['group'],
                    'observation_task': run['current_task'], 'observation_version': run['version'],
                    'observed_at': cur['created']['at'], 'fingerprint': cur['fingerprint'],
                    'generation': (snapshot or {}).get('generation', 0) + 1, 'equivalent_test_source': None}
                d['outbox'][rec['event_id']] = {'record': rec, 'delivered': False}
            elif snapshot is None:
                d['snapshots'][run['opponent']] = {'source_group': run['snapshot_group'],
                    'observation_task': run['current_task'], 'observation_version': run['version'],
                    'observed_at': cur['created']['at'], 'fingerprint': cur['fingerprint'],
                    'generation': 0, 'equivalent_test_source': run['snapshot_group']}
            run.update(status='complete', completed_at=self.now(), result=rec)
            st.setdefault('opp_checks', {})[run['current_task']] = rec
            self.save(st)  # Advance and notification outbox are committed together before any external signal.
            self.log(f"opp-check {rec['opponent']} v{rec['version']}: {'CHANGED; detector snapshot advanced' if changed else 'unchanged from detector snapshot'}; testing pins unchanged")

    def plan(self, st, live, rsets, evidence):
        d = st['opp_detector']
        for opp in ('fish', 'mite'):
            key = f'{live}-{opp}'
            if key in d['runs']:
                continue
            migrated = [x['through_version'] for x in d['migration']['observations'] if x['opponent'] == opp]
            if migrated and live <= max(migrated):
                continue
            oid = self.ls.TEAMS[opp][0]
            bases = sorted((t for t in evidence.tasks.values() if t['version'] == live and t.get('purpose') == 'set'
                            and t.get('part') == 'core' and t.get('pin') == 'ref' and t.get('refset') == rsets[opp]
                            and t['opp_id'] == oid), key=lambda t: (t.get('order', 0), t['id']))
            test_source = evidence.refs.get((rsets[opp], oid))
            if not bases or not test_source or test_source not in evidence.finished:
                continue
            base = bases[0]; snapshot = d['snapshots'].get(opp); source = snapshot['source_group'] if snapshot else test_source
            specs = []
            if source == test_source:
                baseline_task = base['id']
            else:
                baseline_task = base['id'] + '-observed'
                specs.append(dict(base, id=baseline_task, purpose='oppcheck', pin=source, refset=None, is_ref=False,
                                  priority=98, planned=self.now(), note='Detector baseline only; fixed testing pin unchanged'))
            current_task = base['id'] + '-cur'
            specs.append(dict(base, id=current_task, purpose='oppcheck', pin='none', refset=None, is_ref=False,
                              priority=98, planned=self.now(), note='Current opponent versus rolling detector snapshot'))
            d['runs'][key] = {'status': 'pending', 'opponent': opp, 'version': live, 'snapshot_group': source,
                             'testing_source': test_source, 'baseline_task': baseline_task,
                             'current_task': current_task, 'task_specs': specs, 'planned_at': self.now()}
            self.save(st)  # Persist intended pair before appending either task; the next tick repairs partial planning.
        for key, run in d['runs'].items():
            if run['status'] != 'pending' or run['version'] != live:
                continue
            for task in run['task_specs']:
                existing = evidence.tasks.get(task['id'])
                if existing:
                    fields = ('id', 'version', 'purpose', 'opp_id', 'pin', 'refset', 'games')
                    if any(existing.get(f) != task.get(f) for f in fields):
                        run.update(status='invalid', reason='existing task identity conflicts with detector plan')
                        self.save(st); self.log(f'opp-check invalid {key}: task identity conflict')
                        break
                    continue
                self.ls.append_jsonl(self.ls.DATA / 'tasks.jsonl', task)
                evidence.tasks[task['id']] = task
                self.log(f'opp-check planned {task["id"]}: rolling snapshot, testing pins unchanged')

    def tick(self, st, live, rsets):
        evidence = Evidence(self.ls)
        self.bootstrap(st, evidence)
        self.finish(st, evidence)
        self.plan(st, live, rsets, evidence)
        for event in st['opp_detector']['outbox'].values():
            if not event['delivered']:
                self.wake(event['record'])  # Stable event_id lets the append-only wake journal deduplicate recovery.
                event['delivered'] = True
                self.save(st)
        return any(r['status'] == 'pending' and r['version'] == live for r in st['opp_detector']['runs'].values())
