import unittest
from pathlib import Path
from runtime_body import transform

R = Path('/home/ubuntu/cambc-autumn')


class RuntimeBodyTests(unittest.TestCase):
    def test_real_bodies_only_change_seed_access(self):
        for body in ('Flp4', 'Mt3qro'):
            root = R / 'bots/variants' / ('spar-dvn1004-' + body) / 'src'
            old = {str(p.relative_to(root)): p.read_text() for p in root.rglob('*') if p.is_file()}
            new = transform(old)
            self.assertEqual({p for p in new if old.get(p) != new[p]},
                             {'dvp_noise.h', 'draft/fm_draft.h', 'draft/draft.cc', 'experiment_config.h'})
            restored = dict(new)
            restored.pop('experiment_config.h')
            restored['dvp_noise.h'] = restored['dvp_noise.h'].replace(
                'inline std::uint64_t member_seed() { return experiment_config(0); }',
                'inline constexpr std::uint64_t member_seed = 1311004u;').replace(
                'mixw(member_seed(),', 'mixw(member_seed,').replace('\n#include "experiment_config.h"', '')
            restored['draft/fm_draft.h'] = restored['draft/fm_draft.h'].replace(
                'inline std::uint64_t salt() { return experiment_config(1); }',
                'inline constexpr std::uint64_t salt = 1004ull;').replace('\n#include "../experiment_config.h"', '')
            restored['draft/draft.cc'] = restored['draft/draft.cc'].replace('fm::salt() *', 'fm::salt *')
            self.assertEqual(restored, old)
            with self.assertRaises(AssertionError):
                transform(new)


if __name__ == '__main__':
    unittest.main()
