"""Promotion gates with fake platform calls and replay comparisons."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import refresh_live as r


class Promotion(unittest.TestCase):
    def exercise(self, divergence):
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp)
            def save(name,value):
                (w/name).write_text(json.dumps(value))
            save('build-state.json',dict(phase='ready_publication_held',bot='/bots/variants/test-book'))
            save('verify.json',{str(i):None for i in range(410)})
            (w/'stage.DONE').touch()
            (w/'stage.out').write_text('plain: 24 games, 5 bodies handed over, invalid 0\n== 100M\nidentical replays: 52/52\n')
            (w/'bundle.zip').write_bytes(b'zip')
            (w/'REST').write_text('126\n')
            steps=[];book=[];tasks=[];rows=[];created={};finished=set()
            for opp,n in [('mite',20),('fish',10)]:
                cells=[[f'{opp}{i}','a'] for i in range(n)]
                save(f'live-{opp}-cells.json',cells)
                sid=f'check-{opp}'
                steps.append(['cells',sid])
                for i,(mp,side) in enumerate(cells):
                    tid=f'{opp}{i//5}';group=f'g-{tid}'
                    if tid not in created:
                        tasks.append(dict(id=tid,part=sid,version=128))
                        created[tid]={'group':group};finished.add(group)
                    book.append(dict(key=mp,opp=opp,map=mp,side=side))
                    rows.append(dict(group=group,opp_name='Mite' if opp=='mite' else 'Intercontinental Fish',
                                     map=mp,side=side,pin='none',refset=None,version=128,result='win',match=mp))
            save('live-steps.json',steps);save('book_cells.json',book)
            def state():
                return dict(batches=dict(rest=int((w/'REST').read_text()),cur=None),
                            history=[dict(label='test-book',version=128)])
            with mock.patch.object(r.sched,'H',w), mock.patch.object(r.sched,'load',side_effect=state), \
                    mock.patch.object(r.sched,'queue_lines',return_value=[]), \
                    mock.patch.object(r.sched,'submissions',return_value=(128,128,{})) as live, \
                    mock.patch.object(r.subprocess,'run') as upload, \
                    mock.patch.object(r.ls,'state',return_value=(tasks,created,finished,set(),{})), \
                    mock.patch.object(r.ls,'read_jsonl',return_value=rows), \
                    mock.patch.object(r.ls,'suspect_groups',return_value=set()), \
                    mock.patch.object(r.oppwatch,'cell_divergence',return_value=divergence):
                if divergence==-1:
                    r.run(w)
                    self.assertEqual((w/'REST').read_text(),'128\n')
                    self.assertEqual(json.loads((w/'live-check-state.json').read_text())['phase'],'published')
                else:
                    with self.assertRaisesRegex(RuntimeError,'Current opponent differs'):
                        r.run(w)
                    self.assertEqual((w/'REST').read_text(),'126\n')
                    live.assert_not_called()
                self.assertEqual(upload.call_count,1)

    def test_exact_current_wins_promote_existing_version(self):
        self.exercise(-1)

    def test_divergence_never_changes_rest(self):
        self.exercise(0)


if __name__=='__main__':
    unittest.main()
