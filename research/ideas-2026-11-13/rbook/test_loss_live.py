"""Offline publication/provenance tests: no API, scheduler mutation or uploads."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

import loss_live as live


class LossLiveTests(unittest.TestCase):
    def test_optional_upload_deadline_refuses_late_helper(self):
        function='before_deadline() {'+live.HELPER.read_text().split('before_deadline() {',1)[1].split('\n}',1)[0]+'\n}'
        import time
        for deadline,ok in (('',True),('1',False),(str(int(time.time())+3600),True)):
            with self.subTest(deadline=deadline):
                result=subprocess.run(['bash','-c',function+'\nbefore_deadline'],
                                      env=dict(os.environ,BOOK_UPLOAD_DEADLINE_EPOCH=deadline))
                self.assertEqual(result.returncode==0,ok)

    def test_helper_restarts_scheduler_in_independent_user_service(self):
        script=live.HELPER.read_text()
        function='start_sched() {'+script.split('start_sched() {',1)[1].split('\n}',1)[0]+'\n}'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bin_dir=root/'bin';bin_dir.mkdir()
            (root/'sched.lock').write_text(str(os.getpid()))
            (root/'STOP').touch()
            launcher=bin_dir/'systemd-run'
            launcher.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TRACE"\nexit "${LAUNCH_RC:-0}"\n')
            launcher.chmod(0o755)
            (bin_dir/'sleep').write_text('#!/bin/sh\nexit 0\n');(bin_dir/'sleep').chmod(0o755)
            env=dict(os.environ,S=str(root),R=str(root),TRACE=str(root/'trace'),PATH=str(bin_dir)+os.pathsep+os.environ['PATH'])
            result=subprocess.run(['bash','-c',function+'\nstart_sched'],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            args=(root/'trace').read_text().splitlines()
            self.assertIn('--user',args);self.assertIn('--collect',args)
            self.assertIn('--property=Type=exec',args)
            self.assertIn('--property=StandardOutput=append:'+str(root/'sched.out'),args)
            self.assertEqual(args[-2:],['/home/ubuntu/venv/bin/python','tools/live_sched.py'])
            self.assertFalse((root/'STOP').exists())
            env['LAUNCH_RC']='1'
            result=subprocess.run(['bash','-c',function+'\nstart_sched'],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)

    def test_prepare_is_local_and_preserves_an_active_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'after-queue.json').write_text('[]')
            state=dict(batches=dict(rest=130,cur=dict(version=129,phase='batch',task_ids=['protected'])),history=[])
            before=copy.deepcopy(state)
            a=dict(specs={'inc-check':{}},bot='/bot',digest='frozen',pin_groups={'mite':'pin'})
            with mock.patch.object(live,'artifacts',return_value=a),mock.patch.object(live.sched,'H',root), \
                 mock.patch.object(live.ls,'DATA',root),mock.patch.object(live.sched,'load',return_value=state), \
                 mock.patch.object(live.sched,'queue_lines',return_value=[]), \
                 mock.patch.object(live.ls,'state',return_value=([],{},{},set(),{})), \
                 mock.patch.object(live.ls,'quota') as quota, \
                 mock.patch.object(live.ls,'live_version') as platform, \
                 mock.patch.object(live.subprocess,'run') as helper:
                self.assertEqual(live.prepare(root,130)['phase'],'prepared')
                self.assertEqual(state,before)
                quota.assert_not_called();platform.assert_not_called();helper.assert_not_called()

    def test_helper_boundary_yields_all_usable_quota_to_active_campaign(self):
        script=live.HELPER.read_text()
        code=script.split('ready_to_upload() {',1)[1].split("<<'EOF'\n",1)[1].split('\nEOF',1)[0]
        cases=[(None,0,50,'--rest','yes',False),
               ('rest',49,50,'--rest','no',True),
               ('rest',50,50,'--rest','yes',True),
               ('rest',100,50,'--rest','yes',True),
               ('rest',99,0,'--rest','no',True),
               ('rest',100,0,'--rest','yes',True),
               ('rest',0,100,'--rest','yes',True),
               ('activate_batch',100,50,'--rest','no',False),
               ('batch',100,50,'--rest','no',False),
               ('activate_rest',100,50,'--rest','no',False),
               ('rest',0,50,'','yes',False)]
        for phase,used,reserve,mode,wanted,queried in cases:
            with self.subTest(phase=phase,used=used,reserve=reserve,mode=mode), tempfile.TemporaryDirectory() as tmp:
                cur=None if phase is None else dict(version=129,phase=phase,task_ids=['protected'])
                path=Path(tmp)/'state.json';payload=json.dumps(dict(batches=dict(cur=cur)))
                path.write_text(payload)
                quota=mock.Mock(return_value={'quota':dict(used=used,limit=100)})
                modules={'ladder_scrims':types.SimpleNamespace(quota=quota),
                         'live_batches':types.SimpleNamespace(RESERVE=reserve)}
                output=io.StringIO()
                with mock.patch.dict(sys.modules,modules),mock.patch.object(sys,'argv',['boundary',tmp,mode]), \
                     mock.patch.object(sys,'stdout',output),mock.patch.object(sys,'path',sys.path.copy()):
                    exec(compile(code,'live_test.sh boundary','exec'),{})
                self.assertEqual(output.getvalue().strip(),wanted)
                self.assertEqual(quota.called,queried)
                self.assertEqual(path.read_text(),payload)

    def test_guards_allow_waiting_candidate_but_not_activation_or_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state=dict(batches=dict(rest=126,cur=None))
            with mock.patch.object(live.sched,'H',root),mock.patch.object(live.ls,'DATA',root), \
                 mock.patch.object(live.sched,'queue_lines',return_value=[]), \
                 mock.patch.object(live.sched,'load',return_value=state):
                self.assertIs(live.guards(root,126),state)
                state['batches']['cur']=dict(version=129,phase='rest')
                self.assertIs(live.guards(root,126),state)
                for phase in ('activate_batch','batch'):
                    state['batches']['cur']['phase']=phase
                    with self.assertRaisesRegex(RuntimeError,'Batch in progress'):
                        live.guards(root,126)

    def fixture(self):
        spec=dict(id='check',opp='mite',pin='ref',refset='r13',cells=[['map','a']])
        task=dict(id='task',part='check',version=130,purpose='set',opp_id=live.ls.TEAMS['mite'][0],
                  pin='ref',refset='r13',games=[dict(map='map',side='a'),dict(map='fill',side='b',filler=True)])
        ev=dict(live=130,group='group',source_group='pin-group')
        row=dict(task='task',group='group',version=130,purpose='set',opp_id=task['opp_id'],pin='ref',refset='r13',
                 source_group='pin-group',map='map',side='a',status='finished',result='win',match='match',replay='x.zip')
        return dict(expected=[{}],specs={'check':spec},version=130,pin_groups={'mite':'pin-group'},
                    tasks=[task],created={'task':ev},finished={'group'},dropped=set(),suspect=set(),rows=[row])

    def test_partial_plan_accepts_one_requested_cell_and_ignores_filler(self):
        f=self.fixture()
        f['rows'].append(dict(f['rows'][0],map='fill',side='b',filler=True,result='loss'))
        self.assertEqual(len(live.select_results(**f)),1)

    def test_wrong_version_pin_source_suspect_dropped_and_incomplete_rejected(self):
        cases=[('task-version',lambda f:f['tasks'][0].update(version=129)),
               ('row-source',lambda f:f['rows'][0].update(source_group='old-pin')),
               ('created-source',lambda f:f['created']['task'].update(source_group='old-pin')),
               ('row-version',lambda f:f['rows'][0].update(version=129)),
               ('row-pin',lambda f:f['rows'][0].update(pin='none')),
               ('suspect',lambda f:f['suspect'].add('group')),
               ('dropped',lambda f:f['dropped'].add('task')),
               ('unfinished',lambda f:f['finished'].clear()),
               ('missing',lambda f:f['rows'].clear()),
               ('wrong-cell',lambda f:f['tasks'][0]['games'][0].update(map='different'))]
        for name,change in cases:
            with self.subTest(name=name):
                f=self.fixture();change(f)
                with self.assertRaises(RuntimeError): live.select_results(**f)

    def test_duplicate_retry_allowed_but_conflicting_result_rejected(self):
        f=self.fixture();f['rows'].append(copy.deepcopy(f['rows'][0]))
        self.assertEqual(len(live.select_results(**f)),1)
        f['rows'][1]['result']='loss'
        with self.assertRaisesRegex(RuntimeError,'conflicting'): live.select_results(**f)

    def test_current_checks_require_no_source_pin(self):
        f=self.fixture();f['specs']['check']['pin']='none'
        for row in (f['tasks'][0],f['rows'][0]): row.update(pin='none',refset=None)
        f['rows'][0]['source_group']=None;f['created']['task']['source_group']=None
        self.assertEqual(len(live.select_results(**f)),1)
        f['created']['task']['source_group']='pin-group'
        with self.assertRaisesRegex(RuntimeError,'source pin'): live.select_results(**f)

    def validation(self, result='win', diff=42, collateral=False, replay=True):
        f=self.fixture();f['rows'][0]['result']=result
        a=dict(expected=f['expected'],specs=f['specs'],entries=[] if collateral else
               [dict(opp='mite',map='map',side='a',key='source')])
        state=dict(phase='waiting_for_live_checks',version=130,pin_groups=f['pin_groups'])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(live,'unchanged',return_value=a), \
             mock.patch.object(live.ls,'state',return_value=(f['tasks'],f['created'],f['finished'],f['dropped'],{})), \
             mock.patch.object(live.ls,'suspect_groups',return_value=set()), \
             mock.patch.object(live.ls,'read_jsonl',return_value=f['rows']), \
             mock.patch.object(live.oppwatch,'rhash',return_value='hash' if replay else None), \
             mock.patch.object(live.oppwatch,'cell_divergence',return_value=diff):
            return live.validate(Path(tmp),state)

    def test_win_after_divergence_passes(self):
        self.assertEqual(self.validation()['wins_after_divergence'],1)
        self.assertEqual(self.validation(diff=-1)['wins_after_divergence'],0)

    def test_loss_or_missing_replay_or_unreadable_comparison_fails(self):
        for args in (dict(result='loss'),dict(replay=False),dict(diff=None)):
            with self.subTest(args=args),self.assertRaises(RuntimeError): self.validation(**args)

    def test_forced_collateral_needs_win_but_no_same_opponent_recording(self):
        self.assertEqual(self.validation(collateral=True)['wins'],1)
        with self.assertRaisesRegex(RuntimeError,'Required win'):
            self.validation(collateral=True,result='loss')

    def test_upload_intent_prevents_duplicate_helper_invocation(self):
        for phase in ('upload_attempt','waiting_for_live_checks','validated','published'):
            with self.subTest(phase=phase),mock.patch.object(live.subprocess,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'already attempted'):
                    live.upload(Path('/unused'),dict(phase=phase))
                run.assert_not_called()

    def test_crash_during_helper_persists_nonretryable_upload_intent(self):
        state=dict(phase='prepared',expected_rest=126,history_before=[126],bot='/bot')
        a=dict(specs={},entries=[{}],build=dict(pins=dict(fish='r9',mite='r13'),host_name='Charybdis 531 (c451e33)'))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(live,'unchanged',return_value=a), \
             mock.patch.object(live,'guards',return_value={'history':[{'version':126}]}), \
             mock.patch.object(live,'read',return_value=[]),mock.patch.object(live.sched,'MASK_UPLOADS',False), \
             mock.patch.object(live.subprocess,'run',side_effect=RuntimeError('interrupted')) as run:
            work=Path(tmp)
            with self.assertRaisesRegex(RuntimeError,'interrupted'): live.upload(work,state)
            saved=json.loads((work/live.STATE).read_text())
            self.assertEqual(saved['phase'],'upload_attempt')
            self.assertTrue(saved['rest_on_upload'])
            self.assertTrue(saved['note'].startswith('Charybdis 531 (c451e33) + Fish r9/Mite r13'))
            self.assertEqual(run.call_args.args[0][-1],'--rest')
            with self.assertRaisesRegex(RuntimeError,'already attempted'): live.upload(work,saved)
            self.assertEqual(run.call_count,1)

    def test_reconcile_missing_queue_preserves_uploaded_version_and_never_uploads(self):
        state=dict(phase='upload_attempt',history_before=[126],bot='/bot')
        a=dict(specs={'check':dict(id='check',opp='mite')})
        st=dict(history=[dict(version=130,label='bot',dir='/bot',masked=False)])
        with tempfile.TemporaryDirectory() as tmp,mock.patch.object(live,'unchanged',return_value=a), \
             mock.patch.object(live.sched,'load',return_value=st),mock.patch.object(live,'read',return_value=[]), \
             mock.patch.object(live.subprocess,'run') as run:
            work=Path(tmp)
            with self.assertRaisesRegex(RuntimeError,'repair queue only'): live.reconcile(work,state)
            self.assertEqual(json.loads((work/live.STATE).read_text())['version'],130)
            run.assert_not_called()

    def test_prepare_local_artifact_failures_are_not_uploads(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            (work/'build-state.json').write_text(json.dumps(dict(phase='ready_for_live_checks')))
            (work/'book_cells.json').write_text(json.dumps([dict(key='one')]))
            (work/'verify.json').write_text(json.dumps(dict(other=None)))
            with self.assertRaisesRegex(RuntimeError,'exact verification'): live.artifacts(work)

    def test_partial_local_book_requires_current_sample_and_clean_source_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);bot=work/'bot';(bot/'src').mkdir(parents=True)
            (bot/'src'/'bot.cc').write_text('verified source')
            entry=dict(key='map-a-v126-abcdef123456',opp='mite',map='map',side='a')
            base=dict(version=128,opp_name='Mite',opp_id=live.ls.TEAMS['mite'][0],purpose='set',
                      pin='ref',refset='r13',map='map',side='a',result='loss',our_picks=[],opp_picks=[])
            source=dict(base,result='win',group='source',source_group='pin-group')
            files={'build-state.json':dict(phase='ready_for_live_checks',host_version=128,
                                          pins={'mite':'r13'},bot=str(bot)),
                   'book_cells.json':[entry], 'verify.json':{entry['key']:None},
                   'cells.json':[['map','a']],
                   'live-steps.json':[[str(work/'cells.json'),'current','mite','r13',128,'none']],
                   'live-expectations.json':[dict(step='current',opponent='mite',map='map',side='a',
                                                 pin='none',refset=None,require_win=True)]}
            for name,value in files.items(): (work/name).write_text(json.dumps(value))
            for name in ('force.txt','stage.out','stage.DONE'): (work/name).write_text('')
            (work/'bundle.zip').write_bytes(b'bundle')
            with mock.patch.object(live,'validate_stage'),mock.patch.object(live.ls,'games',return_value=[base]), \
                 mock.patch.object(live.plan,'source_rows',return_value={'abcdef123456':source}), \
                 mock.patch.object(live.ls,'state',return_value=([],{},{},set(),
                     {('r13',live.ls.TEAMS['mite'][0]):'pin-group'})), \
                 mock.patch.object(live.ls,'suspect_groups',return_value=set()):
                self.assertEqual(len(live.artifacts(work)['entries']),1)
                files['build-state.json']['host_profile']={'version':128}
                (work/'build-state.json').write_text(json.dumps(files['build-state.json']))
                (work/'foreign-metadata.json').write_text('{"original_pin":"r8"}')
                before=live.artifacts(work)['digest']
                (work/'foreign-metadata.json').write_text('{"original_pin":"r9"}')
                self.assertNotEqual(live.artifacts(work)['digest'],before)
                source['source_group']='old-pin'
                with self.assertRaisesRegex(RuntimeError,'clean target-pin'): live.artifacts(work)
                source['source_group']='pin-group'
                source['our_picks']=['new pick']
                # Add a Fish natural win: forced collateral must become a pinned live check.
                (work/'force.txt').write_text(entry['key']+'\n')
                (work/'forcecheck.out').write_text('1 forced cells, 0 bad, checked')
                files['build-state.json']['pins']['fish']='r8'
                (work/'build-state.json').write_text(json.dumps(files['build-state.json']))
                fish=dict(base,opp_name='Intercontinental Fish',result='win',refset='r8')
                with mock.patch.object(live.ls,'games',return_value=[base,fish]):
                    with self.assertRaisesRegex(RuntimeError,'collateral pin checks'): live.artifacts(work)

    def test_confirmation_requires_actual_live_and_selected_version(self):
        state=dict(phase='promotion_configured',version=130)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.object(live,'reconcile',return_value=state), \
             mock.patch.object(live.sched,'load',return_value={'batches':{'rest':130}}), \
             mock.patch.object(live.ls,'live_version',return_value=(126,130)) as platform:
            with self.assertRaisesRegex(RuntimeError,'activation pending'): live.confirm(Path(tmp),state)
            platform.return_value=(130,130)
            self.assertEqual(live.confirm(Path(tmp),state)['phase'],'published')

    def test_latest_rest_does_not_imply_live_checks_passed(self):
        state=dict(phase='waiting_for_live_checks',version=130,rest_on_upload=True)
        with tempfile.TemporaryDirectory() as tmp,mock.patch.object(live.ls,'live_version') as platform:
            with self.assertRaisesRegex(RuntimeError,'No promotion requested'):
                live.confirm(Path(tmp),state)
            platform.assert_not_called()


if __name__=='__main__': unittest.main()
