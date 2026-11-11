"""Explicit, operator-armed 114 -> existing113/r6 -> prepared506 campaign.

No discovery, repinning, building or automatic extension. The immutable plan is
installed only after the authorized reference transaction; ordinary scheduling
is untouched when no plan exists. Runtime progress lives in scheduler state.
"""
import hashlib
import json
from pathlib import Path

MITE_SOURCE = '01a1c835-46e0-7303-a3de-76a426db6b27'
FISH_SOURCE = '01a1b8b6-16fd-7b80-8eb3-381dae25a9cc'
REQUIRED = {'fish': 'r2', 'mite': 'r6'}
SOURCES = {'fish': FISH_SOURCE, 'mite': MITE_SOURCE}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(path):
    path = Path(path)
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def artifact(spec):
    if sha(spec['path']) != spec['sha256']:
        raise ValueError('campaign artifact changed')
    return json.loads(Path(spec['path']).read_text())


class Campaign:
    def __init__(self, scheduler, detector):
        self.s, self.detector = scheduler, detector

    def save(self, st, phase=None, **fields):
        c = st['r6_campaign']
        if phase:
            c['phase'] = phase
        c.update(fields)
        self.s.save(st)

    def validate(self, plan):
        bridge, proof = artifact(plan['bridge']), artifact(plan['prepared'])
        if bridge['existing_submission'] != 113 or bridge['required_refsets'] != REQUIRED:
            raise ValueError('wrong bridge identity')
        c = dict(proof['candidate'])
        if (not proof.get('ready') or not proof.get('canonical_patch_exact') or not proof.get('drained')
                or proof.get('remaining_processes') or proof.get('stock_smoke_games') != 1):
            raise ValueError('prepared506 validation/resource proof is not complete')
        if c['label'] != 'live-main506' or not proof['sdk_matches_v113'] or not proof['mask_matches_v113']:
            raise ValueError('wrong prepared506 context')
        w = Path(c['workspace'])
        if tree(w / 'bots/ocean/src') != proof['platform_source'] or tree(w / 'sdk/cpp') != proof['platform_sdk']:
            raise ValueError('prepared platform source/SDK changed')
        if tree(Path(c['dir']) / 'src') != proof['source'] or sha(proof['wasm_path']) != proof['wasm_sha256']:
            raise ValueError('prepared source/WASM changed')
        if not c.get('masked') or c['mask_rev'] != self.s.mask_rev() or 'finished:' not in c.get('smoke', ''):
            raise ValueError('prepared mask/smoke not valid')
        b = Path(bridge['workspace'])
        if tree(b / 'bots/ocean/src') != bridge['source_hashes'] or tree(b / 'sdk/cpp') != bridge['sdk_hashes']:
            raise ValueError('archived113 source/SDK changed')
        if any(sha(b / p) != digest for p, digest in bridge['wasm_hashes_current_archive'].items()):
            raise ValueError('archived113 local artifact changed; selection provenance needs review')
        c.update(required_refsets=REQUIRED, required_sources=SOURCES, opponents=['fish', 'mite'])
        self.s.gate_refsets(c)
        return bridge, c

    def progress(self, version, rsets):
        ls = self.s.ls
        tasks, created, finished, dropped, _ = ls.state()
        ids = {ls.TEAMS[k][0]: v for k, v in rsets.items()}
        mine = [t for t in tasks if t['version'] == version and t.get('purpose') == 'set'
                and t.get('part') in ('core', 'ext') and t.get('pin') == 'ref'
                and t.get('refset') == ids.get(t['opp_id'])]
        if len(mine) != 52 * len(rsets):
            raise ValueError('campaign task coverage is not exactly52 groups per opponent')
        if any(t['id'] in dropped for t in mine):
            raise ValueError('campaign task dropped; review required')
        groups = [created[t['id']]['group'] for t in mine if t['id'] in created]
        for t in mine:
            if t['id'] in created:
                e = created[t['id']]
                opp = next(k for k in rsets if ls.TEAMS[k][0] == t['opp_id'])
                if e.get('live') != version or e.get('selected') != version or e.get('source_group') != SOURCES[opp]:
                    raise ValueError('campaign created group has wrong own selection/opponent snapshot')
        if len(groups) != len(mine) or any(g not in finished for g in groups):
            return False
        rows = [r for r in ls.read_jsonl(ls.DATA / 'games.jsonl') if r['group'] in set(groups)]
        unique = {(r['group'], r['position']): r for r in rows}
        if len(unique) != len(groups) * 5 or any(r.get('status') != 'finished' or r.get('result') not in ('win', 'loss') or not r.get('replay')
                or not (ls.ROOT / r['replay']).is_file() for r in unique.values()):
            raise ValueError('campaign completed groups lack valid collected replays')
        cells = {(r['opp_id'], r['map'], r['side']) for r in unique.values() if not r.get('filler')}
        if len(cells) != 256 * len(rsets):
            raise ValueError('campaign lacks256 unique non-filler cells per opponent')
        if set(groups) & ls.suspect_groups():
            raise ValueError('campaign contains suspect groups')
        return not any(e['group'] not in finished for e in created.values())

    def selection(self, d, old, target):
        live, selected = d['active']['version'], d['selected']['version']
        if live not in (old, target) or selected not in (old, target):
            raise ValueError(f'outside selection during campaign: live{live} selected{selected}')
        return live == target and selected == target, selected

    def activate(self, st, d, old, target, next_phase):
        ready, selected = self.selection(d, old, target)
        if ready:
            self.save(st, next_phase)
        elif selected != target:
            rc, out = self.s.sh(['cambc', 'submissions', 'activate', str(target)])
            self.s.log(f'campaign activate existing v{target}: rc{rc} {out[-160:]}')
        # A queued/building activation waits; it is not a reason to upload again.

    def tick(self, st):
        path = self.s.H / 'r6-campaign.json'
        if not path.exists():
            if st.get('r6_campaign', {}).get('phase') not in (None, 'done'):
                self.s.hold('active r6 campaign plan missing')
                return True
            return False
        if st.get('r6_campaign', {}).get('phase') == 'done':
            return False
        if (self.s.H / 'PAUSE').exists() or (self.s.H / 'HOLD').exists():
            return True
        try:
            plan = json.loads(path.read_text())
            digest = sha(path)
            if plan.get('id') != 'bridge113-r6-main506':
                raise ValueError('unrecognized explicitly authorized campaign')
            bridge, c = self.validate(plan)
            if 'r6_campaign' not in st:
                g = self.s.gate(114)
                if g['pending'] or g['inflight'] or g['any_inflight'] or not g['planned']:
                    return True
                if self.detector.tick(st, 114, REQUIRED):
                    return True
                self.save_initial(st, digest)
            state = st['r6_campaign']
            if state['plan_sha256'] != digest:
                raise ValueError('active campaign plan changed')
            try:
                d = self.s.submissions_json()
            except self.s.ls.CambcError as e:
                self.s.log(f'campaign submissions read deferred: {e}')
                return True
            phase = state['phase']
            if phase == 'activate113':
                self.activate(st, d, 114, 113, 'bridge')
            elif phase == 'bridge':
                if not self.selection(d, 113, 113)[0]:
                    return True
                self.s.plan_gate(113, {'mite': 'r6'})
                if self.progress(113, {'mite': 'r6'}):
                    record = {'event_id': 'bridge113-mite-r6-complete', 'version': 113,
                              'groups': 52, 'testing_refsets': {'mite': 'r6'}, 'at': self.s.now()}
                    self.s.wake(record)
                    self.save(st, 'upload506', bridge_result=record)
            elif phase == 'upload506':
                self.selection(d, 113, 113)
                if not self.progress(113, {'mite': 'r6'}):
                    return True
                c['note'] = plan['submission_note'].strip()
                self.save(st, 'upload_intent', upload_note=c['note'])
                rc, out = self.s.sh(['cambc', 'submit', 'ocean', '-n', c['note']], cwd=c['workspace'], timeout=600)
                self.s.log(f'campaign prepared506 upload rc{rc}: {out[-200:]}')
                if rc:
                    self.s.hold('campaign506 upload result uncertain; reconcile note before retry, never rebuild')
                else:
                    self.save(st, 'wait506')
            elif phase in ('upload_intent', 'wait506'):
                self.selection(d, 113, 113)
                matches = [x for x in d['submissions'] if x['version'] > 114
                           and x.get('note', '').strip() == state['upload_note']]
                if len(matches) > 1:
                    raise ValueError('multiple campaign506 submissions; explicit reconciliation required')
                if not matches:
                    if phase == 'upload_intent':
                        self.s.hold('interrupted campaign upload has no identifiable submission; do not duplicate')
                    return True
                row = matches[0]
                status = row.get('status', '').lower()
                if any(x in status for x in ('fail', 'error')):
                    raise ValueError('campaign506 platform build failed')
                if status not in ('active', 'inactive', 'ready', 'compiled', 'success', 'successful'):
                    return True
                self.save(st, 'activate506', version506=row['version'])
            elif phase == 'activate506':
                self.activate(st, d, 113, state['version506'], 'main506')
            elif phase == 'main506':
                v = state['version506']
                self.selection(d, v, v)
                if not any(h['version'] == v for h in st['history']):
                    st['history'].append(dict(c, version=v, base_version=113, live_at=self.s.now(),
                                              note=state['upload_note'], testing_refsets=REQUIRED))
                    self.s.save(st)
                self.s.plan_gate(v, REQUIRED)
                pending = self.detector.tick(st, v, REQUIRED)
                if self.progress(v, REQUIRED) and not pending:
                    record = {'event_id': f'main506-v{v}-r6-complete', 'version': v, 'groups': 104,
                              'testing_refsets': REQUIRED, 'at': self.s.now(), 'entry': st['history'][-1]}
                    self.s.wake(record)
                    if v not in st['reported']:
                        self.s.ls.append_jsonl(self.s.H / 'gates.jsonl', record)
                        st['reported'].append(v)
                    self.save(st, 'done', result=record)
            else:
                raise ValueError(f'unknown campaign phase {phase}')
        except Exception as e:
            self.s.hold(f'r6 campaign: {type(e).__name__}: {e}')
        return True

    def save_initial(self, st, digest):
        st['r6_campaign'] = {'phase': 'activate113', 'plan_sha256': digest, 'started_at': self.s.now()}
        self.s.save(st)
