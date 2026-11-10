"""Fit the two frozen preference directions and calibrate only on queued OOF data."""
import json
from pathlib import Path
import shutil
from preferences import preference_fit, calibrate
from run import D, write, symlink


def main():
    root=D/'inputs/preferences'
    rows=[json.loads(s) for s in (root/'drafts.jsonl').read_text().splitlines() if s]
    model=json.loads((D/'f92/model.json').read_text())
    assert model['features'][:25] == json.loads((D/'config.json').read_text())['features']
    pref=preference_fit(rows,json.loads((root/'features.json').read_text()),model)
    write(D/'preferences.json',pref)
    oof=[json.loads(s) for s in (D/'oof/rows.jsonl').read_text().splitlines() if s]
    pool=json.loads((D/'oof/pool.json').read_text())
    result=calibrate(pref,oof,pool,model)
    provenance=json.loads((D/'oof/provenance.json').read_text())
    result['oof_provenance']=provenance
    for name,arm in result['arms'].items():
        directory=D/'models'/name;directory.mkdir(parents=True,exist_ok=True)
        for file in ('config.json','maps.jsonl','prior.json'):
            symlink(D/'f92'/file,directory/file)
        write(directory/'model.json',arm.pop('model'))
    write(D/'preference-calibration.json',result)


if __name__=='__main__':main()
