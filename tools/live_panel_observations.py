"""Sparse same-own-version observations during a long existing-version campaign."""
from ladder_opp_check import Evidence


def tick(detector, st, live, campaign_id, allow_new, timestamp, rsets, max_epochs=24):
    ls = detector.ls
    evidence = Evidence(ls)
    detector.bootstrap(st, evidence)
    detector.finish(st, evidence)
    d = st['opp_detector']
    clock = st.setdefault('panel_observations', {'next_due': timestamp+3600, 'epochs': 0, 'campaign': campaign_id})
    if clock['campaign'] != campaign_id:
        raise ValueError('observation campaign identity changed')
    ours = lambda k: k.startswith(campaign_id + '-hour')
    pending = any(ours(k) and r['status'] in ('pending', 'held') for k, r in d['runs'].items())
    if allow_new and not pending and timestamp >= clock['next_due'] and clock['epochs'] < max_epochs:
        epoch = clock['epochs'] + 1
        specs = {}
        for opp in ('fish', 'mite'):
            oid = ls.TEAMS[opp][0]
            fixtures = sorted((t for t in evidence.tasks.values() if t['version'] == live
                               and t.get('purpose') == 'set' and t.get('part') == 'core'
                               and t['opp_id'] == oid and t.get('refset') == rsets[opp]
                               and t['id'] not in evidence.dropped), key=lambda t: t.get('order', 0))
            if not fixtures:
                raise ValueError('no exact Fish/Mite primary fixture for same-own-version observation')
            base = fixtures[0]
            source = d['snapshots'][opp]['source_group']
            if source not in evidence.finished:
                raise ValueError('detector snapshot not collected')
            key = f'{campaign_id}-hour{epoch}-v{live}-{opp}'
            b = dict(base, id=key+'-observed', purpose='oppcheck', pin=source, refset=None,
                     is_ref=False, priority=98, planned=detector.now(), note='Hourly same-version detector baseline')
            c = dict(b, id=key+'-cur', pin='none', note='Hourly current opponent, never a testing repin')
            specs[key] = {'status': 'pending', 'opponent': opp, 'version': live,
                          'snapshot_group': source, 'testing_source': evidence.refs[(rsets[opp], oid)],
                          'testing_refset': rsets[opp], 'baseline_task': b['id'], 'current_task': c['id'],
                          'task_specs': [b, c], 'planned_at': detector.now()}
        d['runs'].update(specs)
        clock.update(epochs=epoch, next_due=timestamp+3600)
        detector.save(st)  # Intents and clock precede appends, so restart cannot add another epoch.
    for key, run in d['runs'].items():
        if not ours(key):
            continue
        if run['status'] in ('invalid', 'held'):
            raise ValueError(f'campaign observation needs review: {key}: {run.get("reason")}')
        if run['status'] != 'pending':
            continue
        if run['version'] != live:
            raise ValueError('own version switched before pending observations drained')
        for task in run['task_specs']:
            old = evidence.tasks.get(task['id'])
            if old and any(old.get(k) != task.get(k) for k in ('version', 'opp_id', 'pin', 'refset', 'games', 'purpose')):
                raise ValueError('observation task identity conflicts')
            if not old:
                ls.append_jsonl(ls.DATA / 'tasks.jsonl', task)
                evidence.tasks[task['id']] = task
    for event in d['outbox'].values():
        if not event['delivered']:
            detector.wake(event['record'])
            event['delivered'] = True
            detector.save(st)
    return any(ours(k) and r['status'] == 'pending' for k, r in d['runs'].items())
