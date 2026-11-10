"""Historical null-a context without API calls, queue mutations or repinning."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import live_sched as sched


class NullReferenceTests(unittest.TestCase):
    def state(self, source=None, finished=True):
        source = sched.NULL_A_MITE_SOURCE if source is None else source
        refs={('r3',sched.ls.TEAMS['mite'][0]):source,('r2',sched.ls.TEAMS['fish'][0]):'fish-r2'}
        return [],{},({source:{},'fish-r2':{}} if finished else {}),set(),refs

    def test_only_named_queue_arm_overrides_global_defaults(self):
        default={'fish':'r2','mite':'r5'}
        with patch.object(sched,'refsets',return_value=default),patch.object(sched.ls,'state',return_value=self.state()):
            self.assertEqual(sched.gate_refsets({'kind':'queue','label':'v87-null-a'}),{'fish':'r2','mite':'r3'})
            for c in ({'kind':'queue','label':'v87-null-b'},{'kind':'ocean','label':'v87-null-a'},
                      {'kind':'queue','label':'live-v105-control'}):
                self.assertEqual(sched.gate_refsets(c),default)
            self.assertEqual(default,{'fish':'r2','mite':'r5'})

    def test_both_core_and_extension_use_same_historical_refs(self):
        with patch.object(sched,'sh',return_value=(0,'planned')) as sh,patch.object(sched,'log'):
            sched.plan_gate(114,{'fish':'r2','mite':'r3'})
        seen={}
        for call in sh.call_args_list:
            argv=call.args[0]
            self.assertEqual(argv[2:4],['plan','--version']);self.assertEqual(argv[4],'114')
            seen[argv[argv.index('--sets')+1],argv[argv.index('--opps')+1]]=argv[argv.index('--refset')+1]
            self.assertNotIn('repin',argv)
        self.assertEqual(seen,{('core','fish'):'r2',('ext','fish'):'r2',('core','mite'):'r3',('ext','mite'):'r3'})

    def test_wrong_or_incomplete_snapshot_fails_before_submission(self):
        for state in (self.state('wrong'),self.state(finished=False)):
            with self.subTest(state=state),tempfile.TemporaryDirectory() as td:
                header=Path(td)/'bots/ocean/src/model'/sched.MASK_HEADER
                header.parent.mkdir(parents=True);header.touch()
                c={'kind':'queue','label':'v87-null-a','workspace':td,'dir':td}
                with patch.object(sched.ls,'state',return_value=state),patch.object(sched,'sh') as sh:
                    with self.assertRaises(ValueError):sched.submit({},c,113)
                    sh.assert_not_called()

if __name__=='__main__':unittest.main()
