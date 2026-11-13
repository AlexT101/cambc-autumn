"""Outcome-only baselines must retain drafts and never suppress source/check downloads."""
import json
import fcntl
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ladder_scrims as ls


class CollectionPolicy(unittest.TestCase):
    def test_filler_cannot_hide_later_requested_cell(self):
        row=dict(version=128,opp_id='opp',pin='ref',refset='r12',map='map',side='a',
                 result='win',purpose='set',group='group')
        rows=[dict(row,filler=True,match='filler'),dict(row,filler=False,match='requested')]
        with mock.patch.object(ls,'read_jsonl',return_value=rows), \
             mock.patch.object(ls,'suspect_groups',return_value=set()):
            self.assertEqual([r['match'] for r in ls.games(128)],['requested'])

    def test_duplicate_runner_preserves_live_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.lock'
            with path.open('w') as owner:
                owner.write('1908511\n');owner.flush()
                fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with mock.patch.object(ls,'DATA',Path(tmp)):
                    with self.assertRaisesRegex(SystemExit,'holds the lock'):
                        ls.cmd_run(None)
                self.assertEqual(path.read_text(),'1908511\n')

    def collect(self, version=128, purpose='set', pin='ref', wins_only=None, result='loss', live=None,
                cached_replay=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'OUTCOME-ONLY-VERSIONS.json').write_text('[128]\n')
            if wins_only is not None:
                (root/'WINS-ONLY-TASKS.json').write_text(wins_only)
            if cached_replay:
                folder=root/'replays'/'group'
                folder.mkdir(parents=True)
                (folder/'1-map.zip').write_bytes(b'cached')
            task=dict(version=version,id='task',purpose=purpose,pin=pin,refset='r12',
                      opp_id='opp',opp_name='Mite',games=[dict(side='a')])
            ev=dict(live=version if live is None else live,group='group',at='now',source_group='source')
            detail=dict(matches=[dict(position=1,matchId='match',map='map',mapId='id',status='finished',
               teams=[dict(teamId=ls.MY_TEAM,side='a',result=result,draftPicks=[0,1]),
                      dict(teamId='opp',name='Mite',side='b',draftPicks=[2,3])])])
            calls=[]
            def cambc(*args,**kwargs):
                calls.append(args)
                if '-o' in args:
                    Path(args[args.index('-o')+1]).write_bytes(b'fixture')
                return ''
            with mock.patch.multiple(ls,DATA=root,ROOT=root,REPLAYS=root/'replays'), \
                 mock.patch.object(ls,'cambc',side_effect=cambc), \
                 mock.patch.object(ls,'summary_fields',return_value={'rounds':1000}):
                rows=ls.collect(task,ev,detail)
                self.assertEqual(ls.read_jsonl(root/'games.jsonl'),rows)
            return rows,calls

    def test_host_baseline_keeps_outcome_and_draft_without_downloads(self):
        rows,calls=self.collect()
        self.assertEqual(calls,[])
        self.assertEqual(rows[0]['result'],'loss')
        self.assertEqual(rows[0]['our_picks'],[ls.CHAMPS[0],ls.CHAMPS[1]])
        self.assertEqual(rows[0]['collection'],'outcome_only')
        self.assertIsNone(rows[0]['replay'])

    def test_other_versions_keep_replay_and_summary(self):
        rows,calls=self.collect(version=126)
        self.assertEqual([c[1] for c in calls],['download','summary'])
        self.assertTrue(rows[0]['replay'])
        self.assertEqual(rows[0]['rounds'],1000)

    def test_current_opponent_checks_keep_full_evidence(self):
        rows,calls=self.collect(purpose='oppcheck',pin='none')
        self.assertEqual([c[1] for c in calls],['download','summary'])
        self.assertNotIn('collection',rows[0])

    def test_selected_source_loss_keeps_outcome_drafts_and_provenance(self):
        rows,calls=self.collect(version=126,wins_only='["task"]')
        self.assertEqual(calls,[])
        row=rows[0]
        self.assertEqual(row['collection'],'loss_outcome_only')
        self.assertIsNone(row['replay'])
        self.assertEqual(row['result'],'loss')
        self.assertEqual(row['our_picks'],[ls.CHAMPS[0],ls.CHAMPS[1]])
        self.assertEqual(row['opp_picks'],[ls.CHAMPS[2],ls.CHAMPS[3]])
        self.assertEqual({k:row[k] for k in ('version','task','group','source_group','refset','pin','map','side')},
                         dict(version=126,task='task',group='group',source_group='source',refset='r12',
                              pin='ref',map='map',side='a'))

    def test_selected_source_wins_and_unknown_results_keep_full_downloads(self):
        for result in ('win',None,'draw',''):
            with self.subTest(result=result):
                rows,calls=self.collect(version=126,wins_only='["task"]',result=result)
                self.assertEqual([c[1] for c in calls],['download','summary'])
                self.assertTrue(rows[0]['replay'])
                self.assertEqual(rows[0]['rounds'],1000)

    def test_loss_skip_is_exact_task_and_pinned_set_only(self):
        for override in (dict(wins_only='["task-other"]'), dict(wins_only='{"task": true}'),
                         dict(wins_only='invalid json'), dict(purpose='oppcheck'), dict(pin='none'),
                         dict(live=127)):
            with self.subTest(override=override):
                args=dict(version=126,wins_only='["task"]')
                args.update(override)
                rows,calls=self.collect(**args)
                self.assertEqual([c[1] for c in calls],['download','summary'])
                self.assertNotIn('collection',rows[0])

    def test_selected_source_loss_preserves_cached_replay_link(self):
        rows,calls=self.collect(version=126,wins_only='["task"]',cached_replay=True)
        self.assertEqual(calls,[])
        self.assertEqual(rows[0]['replay'],'replays/group/1-map.zip')


if __name__=='__main__':
    unittest.main()
