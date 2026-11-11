"""Fixed conditional descending-opponent panel, reusing two existing submissions.

Installed explicitly by ops after review. No upload, build, repin or adaptive
winner selection. Normal live scheduling is unchanged without live-panel.json.
"""
import json
import time
from pathlib import Path

from ladder_opp_check import Evidence
from live_panel_evidence import paired, needs_discernment
from live_panel_observations import tick as observations
from live_r6_campaign import REQUIRED, SOURCES, sha


class Panel:
    def __init__(self, scheduler, detector):
        self.s, self.detector = scheduler, detector

    def save(self, st, **fields):
        st['live_panel'].update(fields)
        self.s.save(st)

    def hold(self, why):
        # The existing creation barrier leaves collection running. Ops clears it
        # only after review; a scheduler HOLD alone would not stop queued groups.
        ls = self.s.ls
        with ls.live_lock(ls.DATA):
            marker = ls.DATA / 'version-check-active.json'
            if not marker.exists():
                marker.write_text(json.dumps({'kind': 'live-panel-hold', 'reason': why, 'at': self.s.now()})+'\n')
        self.s.hold(why)

    def validate(self, plan):
        if plan['id'] != 'conditional113-main506-descending-20261111':
            raise ValueError('unrecognized fixed panel')
        entries = plan['fixed_entries']
        if ([e['rank_at_design'] for e in entries] != list(range(4, 18))
                or len({e['team_id'] for e in entries}) != 14
                or len({e['refset'] for e in entries}) != 14
                or any(not self.s.ls.UUID.fullmatch(e['team_id']) for e in entries)):
            raise ValueError('fixed descending14-team panel changed')
        if plan['tranches'] != [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14]]:
            raise ValueError('unexpected tranche allocation')
        if sha(self.s.ls.DATA / 'set-v1.json') != plan['map_set_sha256']:
            raise ValueError('published map fixture changed')
        if self.s.refsets() != REQUIRED:
            raise ValueError('primary testing pins changed during panel')
        _, _, finished, _, refs = self.s.ls.state()
        for opp, source in SOURCES.items():
            if refs.get((REQUIRED[opp], self.s.ls.TEAMS[opp][0])) != source or source not in finished:
                raise ValueError('primary source pin changed')

    def tasks(self, plan, entry, version, source=None, baseline=False):
        ls = self.s.ls
        maps = ls.load_set('v1')
        out = []
        for part, prio in (('core', 99), ('ext', 90)):
            for i, games in enumerate(ls.set_groups(maps[part], maps['core']), 1):
                first = baseline and part == 'core' and i == 1
                out.append({'id': f"panel-{plan['id']}-v{version}-{entry['team_id']}-{part}-{i:02d}",
                    'version': version, 'set': 'v1', 'part': part, 'purpose': 'set',
                    'opp_id': entry['team_id'], 'opp_name': entry['name'], 'pin': 'ref' if first else source,
                    'refset': entry['refset'], 'games': games, 'priority': prio, 'order': i,
                    'planned': self.s.now(), 'campaign': plan['id']})
        if len(out) != 52:
            raise ValueError('map fixture no longer generates52 groups')
        return out

    def append(self, specs, evidence):
        for t in specs:
            old = evidence.tasks.get(t['id'])
            if old:
                if any(old.get(k) != t.get(k) for k in ('version', 'opp_id', 'pin', 'refset', 'games', 'purpose')):
                    raise ValueError('panel task identity conflicts with prior plan')
            else:
                if t['pin'] is None:
                    raise ValueError('cannot dispatch a panel cell before its snapshot is fixed')
                self.s.ls.append_jsonl(self.s.ls.DATA / 'tasks.jsonl', t)
                evidence.tasks[t['id']] = t

    def verify_group(self, evidence, task, source, engines):
        group = evidence.group(task['id'])
        if group is None:
            return False
        e = group['created']
        effective = e.get('source_group') or (e['group'] if e.get('is_ref') else None)
        if effective != source:
            raise ValueError('panel group did not use its frozen opponent snapshot')
        if any((c['engine'], c['engine_hash']) not in engines for c in group['cells'].values()):
            raise ValueError('panel engine changed from primary comparison')
        rows = evidence.rows[task['id']]
        if any(not r.get('replay') or not (self.s.ls.ROOT / r['replay']).is_file() for r in rows):
            raise ValueError('finished panel group lacks collected replay')
        return True

    def team(self, st, plan, entry, version, baseline, engines):
        ls = self.s.ls
        state = st['live_panel']
        evidence = Evidence(ls)
        source = state['sources'].get(entry['team_id'])
        if source is None:
            if not baseline:
                raise ValueError('candidate attempted before baseline snapshot')
            first = self.tasks(plan, entry, version, baseline=True)[0]
            existing_ref = evidence.refs.get((entry['refset'], entry['team_id']))
            event = evidence.created.get(first['id'])
            if existing_ref and (not event or event['group'] != existing_ref):
                raise ValueError('new team reference namespace already belongs to another capture')
            self.append([first], evidence)
            group = evidence.group(first['id'])
            if group is None:
                return False
            if group['created'].get('source_group') is not None or not group['created'].get('is_ref'):
                raise ValueError('first baseline capture was not the designated unpinned reference')
            source = group['created']['group']
            self.verify_group(evidence, first, source, engines)
            state['sources'][entry['team_id']] = source
            state['captures'][entry['team_id']] = {'task': first['id'], 'source_group': source,
                'fingerprint': group['fingerprint'], 'own_version': version, 'engine_contexts': sorted(engines)}
            self.s.save(st)  # No later group is planned before this validated snapshot is durable.
        elif evidence.refs.get((entry['refset'], entry['team_id'])) != source:
            raise ValueError('persisted team snapshot differs from reference journal')
        specs = self.tasks(plan, entry, version, source, baseline)
        self.append(specs, evidence)
        return all(self.verify_group(evidence, t, source, engines) for t in specs)

    def drained(self):
        _, created, finished, _, _ = self.s.ls.state()
        return not any(e['group'] not in finished for e in created.values())

    def platform(self, st, old, target):
        d = self.s.submissions_json()
        a, b = d['active']['version'], d['selected']['version']
        if a not in (old, target) or b not in (old, target):
            raise ValueError(f'outside selection: live{a} selected{b}; not restoring over it')
        by_version = {x['version']: x for x in d['submissions']}
        for v, identity in st['live_panel']['submission_ids'].items():
            if by_version.get(int(v), {}).get('id') != identity:
                raise ValueError('existing submission identity changed/missing')
            status = by_version[int(v)].get('status', '').lower()
            if any(x in status for x in ('fail', 'error')):
                raise ValueError('existing submission activation build failed')
        return a == target and b == target, b

    def primary(self, version):
        return {opp: paired(self.s.ls, 113, version, self.s.ls.TEAMS[opp][0], SOURCES[opp], REQUIRED[opp])
                for opp in ('fish', 'mite')}

    def tick(self, st):
        path = self.s.H / 'live-panel.json'
        if st.get('live_panel', {}).get('phase') in ('done', 'not_needed'):
            return False
        if not path.exists():
            if st.get('live_panel'):
                self.hold('active opponent panel plan missing')
                return True
            return False
        if (self.s.H / 'PAUSE').exists() or (self.s.H / 'HOLD').exists():
            return True
        try:
            plan = json.loads(path.read_text())
            narrow = st.get('r6_campaign', {})
            if narrow.get('phase') != 'done':
                return False
            self.validate(plan)
            version = narrow['version506']
            if 'live_panel' not in st:
                primary = self.primary(version)
                state = {'phase': 'activate_baseline', 'plan_sha256': sha(path), 'version506': version,
                         'primary': primary, 'tranche': 0, 'index': 0, 'sources': {}, 'captures': {}, 'reports': {},
                         'started_at': self.s.now()}
                if not needs_discernment(primary['fish'], primary['mite']):
                    state['phase'] = 'not_needed'
                    st['live_panel'] = state
                    self.s.save(st)
                    self.s.wake({'event_id': plan['id']+'-not-needed', 'primary': primary,
                                 'note': 'Prospective closeness condition false; no broader games queued'})
                    return False
                d = self.s.submissions_json()
                if d['active']['version'] != version or d['selected']['version'] != version:
                    raise ValueError('primary completed but selected own version changed')
                state['submission_ids'] = {str(x['version']): x['id'] for x in d['submissions']
                                           if x['version'] in (113, version)}
                if len(state['submission_ids']) != 2:
                    raise ValueError('both existing own submissions must remain selectable')
                st['live_panel'] = state
                self.s.save(st)
            state = st['live_panel']
            if state['plan_sha256'] != sha(path) or state['version506'] != version:
                raise ValueError('active panel identity changed')
            engines = {tuple(e) for r in state['primary'].values() for e in r['engine_contexts']}
            if len(engines) != 1:
                raise ValueError('primary comparison spans multiple engine contexts')
            phase = state['phase']
            baseline = phase in ('activate_baseline', 'baseline')
            live = 113 if baseline else version
            if phase.startswith('activate_'):
                old = version if baseline else 113
                with self.s.ls.live_lock(self.s.ls.DATA):
                    if not self.drained():
                        return True
                    ready, selected = self.platform(st, old, live)
                    if ready:
                        self.save(st, phase='baseline' if baseline else 'candidate', index=0)
                    elif selected != live:
                        rc, out = self.s.sh(['cambc', 'submissions', 'activate', str(live)])
                        self.s.log(f'panel activate existing{live}: rc{rc} {out[-120:]}')
                return True
            if phase not in ('baseline', 'candidate'):
                raise ValueError('unknown panel phase')
            if not self.platform(st, live, live)[0]:
                return True
            tranche = plan['tranches'][state['tranche']]
            if state['index'] < len(tranche):
                entry = plan['fixed_entries'][tranche[state['index']]-1]
                complete = self.team(st, plan, entry, live, baseline, engines)
                observations(self.detector, st, live, plan['id'], not complete, time.time(), REQUIRED)
                if complete:
                    if not baseline:
                        result = paired(self.s.ls, 113, version, entry['team_id'],
                                        state['sources'][entry['team_id']], entry['refset'])
                        state['reports'][entry['team_id']] = dict(result, name=entry['name'], rank=entry['rank_at_design'])
                        self.s.wake({'event_id': plan['id']+'-'+entry['team_id'], 'result': state['reports'][entry['team_id']]})
                    self.save(st, index=state['index']+1)
                return True
            pending = observations(self.detector, st, live, plan['id'], False, time.time(), REQUIRED)
            if pending or not self.drained():
                return True
            if baseline:
                self.save(st, phase='activate_candidate')
            elif state['tranche']+1 < len(plan['tranches']):
                self.save(st, phase='activate_baseline', tranche=state['tranche']+1)
            else:
                # The final candidate tranche ends on506; never select over an outside owner.
                self.save(st, phase='done', completed_at=self.s.now())
                self.s.wake({'event_id': plan['id']+'-complete', 'reports': state['reports'],
                             'note': 'Fixed secondary opponent panel complete; no automatic merge or repin'})
        except self.s.ls.CambcError as e:
            self.s.log(f'panel read-only API deferred: {e}')
        except Exception as e:
            self.hold(f'live opponent panel: {type(e).__name__}: {e}')
        return True
