"""The fresh-map gate: py tools/fgate.py CAND REF.

Default: large batches of fresh maps against run-time-configured, unmetered Fish/Mite bodies, with no opponent
compile a batch (fgate_batch.py; --help lists its options).

--blocks: the gate as it was before 2026-11-11, for reproducing older reads: 256-game noise blocks, a compiled
opponent pair a block, with bounded compile-ahead (16 workers, 8 blocks). Its statistical/game arguments pass
unchanged to research/ideas-2026-11-09/freshgate-tools/fgate.py; resource overrides: --no-compile-ahead,
--compile-workers N, --compile-lookahead N. The two modes play different opponent populations (metered against
unmetered bodies, a seed a block against a seed a map), so their runs and result files are separate.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import gate_compile_ahead as ahead


def legacy_settings(argv):
    """Recognize every legacy option so its value cannot become a bot positional."""
    settings=argparse.ArgumentParser(add_help=False)
    settings.add_argument('cand');settings.add_argument('ref')
    for name,default in (('sprt','0.505,0.5075'),('low','0.4975,0.50'),('fish-body','Flp4'),('mite-body','Mt3q')):
        settings.add_argument('--'+name,default=default)
    for name,default in (('max-seeds',1000),('jobs',8),('ahead',2),('seed',0),('min-blocks',8)):
        settings.add_argument('--'+name,type=int,default=default)
    settings.add_argument('--fuel',type=int);settings.add_argument('--ci',type=float,default=.25)
    settings.add_argument('--no-run',action='store_true');settings.add_argument('--zone-stop',action='store_true')
    return settings.parse_args(argv)


def main():
    os.environ.setdefault('CAMBC_SLOTS','86')
    os.environ.setdefault('FASTRUNNER_MODE','native')
    os.environ.setdefault('CAMBC_BIN',str(ahead.CLI))
    if '--blocks' not in sys.argv[1:]:
        import fgate_batch
        return fgate_batch.main(sys.argv[1:])
    sys.argv.remove('--blocks')
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--no-compile-ahead',action='store_true')
    parser.add_argument('--compile-workers',type=int,default=ahead.DEFAULT_WORKERS)
    parser.add_argument('--compile-lookahead',type=int,default=ahead.DEFAULT_LOOKAHEAD)
    resource,argv=parser.parse_known_args()
    if not 1<=resource.compile_workers<=32 or not 0<=resource.compile_lookahead<=32:
        parser.error('compile workers must be1..32 and lookahead0..32')
    source=ahead.R/'research/ideas-2026-11-09/freshgate-tools/fgate.py'
    spec=importlib.util.spec_from_file_location('default_fgate',source)
    fg=importlib.util.module_from_spec(spec);spec.loader.exec_module(fg)
    sys.argv=[str(source),*argv]
    if '--help' in argv or '-h' in argv:print(__doc__)
    if resource.no_compile_ahead or os.environ.get('CAMBC_COMPILE_AHEAD','1')=='0' or '--no-run' in argv or '--help' in argv or '-h' in argv:
        fg.main();return
    chosen=legacy_settings(argv)
    root=ahead.R/'replays/compile-ahead';root.mkdir(exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='fgate-',dir=root));blocks=directory/'blocks';blocks.mkdir()
    manifest=directory/'manifest.json'
    ahead.snapshot_manifest(manifest,[chosen.cand,chosen.ref],source)
    original=fg.block_units
    def progress(*args,**kwargs):
        result=original(*args,**kwargs)
        ahead.write(blocks/f'{args[2]:04d}.json',{'completed_noise':args[2]})
        return result
    fg.block_units=progress
    with ahead.scope(directory,manifest,blocks,source,[chosen.fish_body,chosen.mite_body],last=chosen.max_seeds,
                     workers=resource.compile_workers,lookahead=resource.compile_lookahead):
        fg.main()


if __name__=='__main__':main()
