import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
spec=importlib.util.spec_from_file_location('tested_default_fgate',TOOLS/'fgate.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)


class EntryTests(unittest.TestCase):
    def test_all_legacy_flag_values_before_or_after_bots(self):
        flags=['--fuel','200000','--sprt','.5,.5025','--low','.4975,.5','--ci','0','--jobs','4','--ahead','0',
               '--seed','987','--max-seeds','1000','--min-blocks','8','--fish-body','Flp4','--mite-body','Mt3qro','--zone-stop']
        for argv in (flags+['variants/cand','variants/ref'],['variants/cand','variants/ref']+flags):
            result=entry.legacy_settings(argv)
            self.assertEqual((result.cand,result.ref,result.fuel,result.mite_body),('variants/cand','variants/ref',200000,'Mt3qro'))

    def run_entry(self, extra, enabled):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'replays').mkdir();directory=root/'run';directory.mkdir()
            args=['variants/cand','variants/ref','--fuel','200000','--ci','0','--max-seeds','17','--mite-body','Mt3qro',*extra]
            result={'unchanged':'paired statistics'};seen=[]
            class FG:
                block_units=staticmethod(lambda *a:result)
                def main(self):
                    seen.extend(sys.argv)
                    assert self.block_units('cand','ref',1,None) is result
            fg=FG()
            with patch.object(entry.sys,'argv',['tools/fgate.py','--blocks',*args]),patch.object(entry.ahead,'R',root),patch.object(entry.ahead,'snapshot_manifest') as seal,patch.object(entry.ahead,'scope') as scope,patch.object(entry.tempfile,'mkdtemp',return_value=str(directory)),patch.object(entry.importlib.util,'module_from_spec',return_value=fg),patch.object(entry.importlib.util,'spec_from_file_location') as loader:
                loader.return_value.loader.exec_module.return_value=None
                entry.main()
                self.assertEqual(seal.call_count,int(enabled));self.assertEqual(scope.call_count,int(enabled))
                if enabled:
                    self.assertEqual(scope.call_args.kwargs,{'last':17,'workers':16,'lookahead':8})
                    self.assertEqual(scope.call_args.args[4],['Flp4','Mt3qro'])
            self.assertEqual(seen[1:],[x for x in args if x!='--no-compile-ahead'])

    def test_default_is_batch_mode_and_blocks_flag_is_consumed(self):
        seen=[]
        with patch.dict(sys.modules,{'fgate_batch':type(sys)('fgate_batch')}):
            sys.modules['fgate_batch'].main=lambda argv:seen.append(list(argv))
            with patch.object(entry.sys,'argv',['tools/fgate.py','variants/cand','variants/ref','--fuel','200000']),patch.object(entry.importlib.util,'spec_from_file_location') as loader:
                entry.main()
                loader.assert_not_called()
        self.assertEqual(seen,[['variants/cand','variants/ref','--fuel','200000']])

    def test_blocks_preserves_game_arguments_and_units(self):self.run_entry([],True)
    def test_explicit_optout_has_no_helper(self):self.run_entry(['--no-compile-ahead'],False)
    def test_no_run_never_precompiles(self):self.run_entry(['--no-run'],False)


if __name__=='__main__':unittest.main()
