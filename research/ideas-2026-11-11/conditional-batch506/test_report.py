import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import report
from run import sha


class CompleteEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        cfg = root / 'config.json'
        team = {'seed': 1330001, 'salt': 20001, 'unmetered': True}
        cfg.write_text(json.dumps({'schema': 1, 'opponent_index': 1, 'maps': {'m': team}}))
        proof = {'sha256': sha(cfg)}
        rows = [{'map': 'm.map26a', 'order': [0, 1], 'winner': 0, 'runtime_config': {'a': None, 'b': team}},
                {'map': 'm.map26a', 'order': [1, 0], 'winner': 1, 'runtime_config': {'a': team, 'b': None}}]
        batch = {'scheduled': 2, 'completed': 2, 'errors': 0, 'release': True, 'fuel': 200000, 'game_timeout': 120,
                 'experiment_config': proof, 'matches': rows}
        directory = root / 'batch'
        directory.mkdir()
        bp = directory / 'results.json'
        bp.write_text(json.dumps(batch))
        summary = {'games': 2, 'errors': 0, 'release': True, 'fuel': 200000, 'game_timeout': 120, 'cambc': '5.0.1',
                   'cand': {'spec': 'candidate'}, 'ref': {'spec': 'body'}, 'experiment_config': proof,
                   'suites': [{'batch': 'batch'}]}
        directory = root / 'replays/ab/test'
        directory.mkdir(parents=True)
        (directory / 'summary.json').write_text(json.dumps(summary))
        return cfg, bp, batch

    def test_paired_side_mapping_and_hash_are_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg, bp, batch = self.fixture(root)
            with patch.object(report, 'R', root):
                values, _ = report.read_batch('test', 'candidate', 'body', {'m'}, cfg)
                self.assertEqual(values, {('m', (0, 1)): 1, ('m', (1, 0)): 0})
                batch['matches'][1]['runtime_config'] = batch['matches'][0]['runtime_config']
                bp.write_text(json.dumps(batch))
                with self.assertRaises(AssertionError):
                    report.read_batch('test', 'candidate', 'body', {'m'}, cfg)

    def test_timeout_or_partial_batch_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg, bp, batch = self.fixture(root)
            batch.update(errors=1, completed=1)
            bp.write_text(json.dumps(batch))
            with patch.object(report, 'R', root), self.assertRaises(AssertionError):
                report.read_batch('test', 'candidate', 'body', {'m'}, cfg)


if __name__ == '__main__':
    unittest.main()
