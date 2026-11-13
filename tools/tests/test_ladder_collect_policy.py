"""Outcome-only baselines must retain drafts and never suppress source/check downloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ladder_scrims as ls


class CollectionPolicy(unittest.TestCase):
    def collect(self, version=128, purpose='set', pin='ref'):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'OUTCOME-ONLY-VERSIONS.json').write_text('[128]\n')
            task=dict(version=version,id='task',purpose=purpose,pin=pin,refset='r12',
                      opp_id='opp',opp_name='Mite',games=[dict(side='a')])
            ev=dict(live=version,group='group',at='now')
            detail=dict(matches=[dict(position=1,matchId='match',map='map',mapId='id',status='finished',
               teams=[dict(teamId=ls.MY_TEAM,side='a',result='loss',draftPicks=[0,1]),
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


if __name__=='__main__':
    unittest.main()
