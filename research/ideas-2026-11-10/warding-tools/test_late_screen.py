"""Admission boundary checks only; never runs games."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import late_screen as screen

class ScreenTests(unittest.TestCase):
    def test_prespecified_stop_budget(self):
        self.assertTrue(screen.valid_stop(3, 'LIVE BAR H1'))
        self.assertTrue(screen.valid_stop(8, 'undecided'))
        self.assertFalse(screen.valid_stop(3, 'undecided'))
        self.assertFalse(screen.valid_stop(9, 'LIVE BAR H1'))

    def test_positive_interval_required(self):
        self.assertGreater(screen.estimate([.25] * 128)[2], 0)
        self.assertLess(screen.estimate([0] * 127 + [.25])[2], 0)
        self.assertEqual(screen.estimate([0] * 128)[2], 0)

    def test_normal_admission_checks(self):
        sources = json.loads((screen.T / 'sources.json').read_text())
        base = {'decision': 'positive', 'complete_blocks': 3, 'valid_terminal_stop': True,
                'validated_cells': True, 'fuel': 200000, 'fresh_lower_pp': .1,
                'sources': {k: sources[k] for k in screen.ARMS}}
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            for change, okay in [({}, True), ({'fresh_lower_pp': 0}, False),
                                 ({'decision': 'hold'}, False), ({'validated_cells': False}, False),
                                 ({'valid_terminal_stop': False}, False), ({'complete_blocks': 9}, False),
                                 ({'fuel': 100000}, False), ({'sources': {}}, False)]:
                proof = copy.deepcopy(base); proof.update(change)
                raw = json.dumps(proof).encode(); (d / 'proof.json').write_bytes(raw)
                admission = {'authorized_by': 'coordinator', 'screen_proof': str(d / 'proof.json'),
                             'screen_sha256': hashlib.sha256(raw).hexdigest()}
                (d / 'admission.json').write_text(json.dumps(admission))
                result = subprocess.run([sys.executable, str(screen.T / 'run_gate.py'), 'oc-wlate-498',
                                         '--fuel', '100000', '--check', '--screen-admission', str(d / 'admission.json')],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, okay, (change, result.stderr))

if __name__ == '__main__':
    unittest.main()
