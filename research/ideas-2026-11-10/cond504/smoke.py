"""Scheduled release validity and separately instrumented debug classifier/activation fixtures."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import zipfile

from run import R,D,T,BASE,CAND,sha,source,write,command,pooled,verify,body_seal


def summaries(name, bot, body, release):
    sp=R/'replays/ab'/name/'summary.json';s=json.loads(sp.read_text())
    assert s['games']==8 and s['errors']==0 and s['release'] is release and s['fuel']==200000 and s['cambc']=='5.0.1'
    assert s['cand']['spec']==bot and s['ref']['spec']==body
    assert not any(s.get('handoff_failures',{}).values()) and not any(s.get('early_losses',{}).values()),name
    records=[]
    for suite in s['suites']:
        path=R/suite['batch']/'results.json';b=json.loads(path.read_text())
        assert b['scheduled']==b['completed']==8 and b['errors']==0
        for x in b['matches']:
            assert x.get('winner') in (0,1) and x['order'] in ([0,1],[1,0])
            records.append(x)
    cells={(Path(x['map']).stem,tuple(x['order'])) for x in records}
    expected={(p.stem,order) for p in (D/'smoke-maps').glob('*.map26a') for order in ((0,1),(1,0))}
    assert len(records)==len(cells)==8 and cells==expected
    return s,records


def play(arm,bot,body,label,debug=False):
    scope='shared' if bot==BASE else arm
    name='exploit504-'+scope+'-'+label+'-200k'
    argv=[sys.executable,R/'tools/ab.py',bot,body,'--no-test-draft','--fuel','200000','--suites',D/'smoke-maps','--keep-replays','8','--name',name]
    if debug:argv.append('--debug')
    if not (R/'replays/ab'/name/'summary.json').exists():
        command(argv,D/arm/'smoke-runs.log')
    s,records=summaries(name,bot,body,not debug)
    return name,s,records


def trace_copy(arm):
    trace='variants/oc506-'+arm+'-trace'
    assert not (R/'bots'/trace).exists(),'Partial trace preparation needs review'
    command(['./copybot',CAND[arm],trace],D/arm/'trace-build.log')
    root=R/'bots'/trace/'src'
    if arm=='chanM':
        p=root/'model/turn_order.cc';s=p.read_text();old='    if (oppx::mite(world)) {\n        wish.offer(protect, value);'
        new='''    if (oppx::mite(world)) {
        debug_block({ static int shown = 0; if (shown++ < 32) { const auto& pp = opp::posterior(world);
            std::printf("EXPACT M %d %d %.4f %.4f\\n", world.round, static_cast<int>(world.me().handle), pp.fish, pp.mite); } });
        wish.offer(protect, value);'''
    else:
        p=root/'combat/support.cc';s=p.read_text();old='        const float key = static_cast<float>(crowd) + (carry ? static_cast<float>(std::min(comms::bag_of(world, a.index), 120)) / 40.0f : 0.0f);'
        new='''        debug_block({ static int shown = 0; if (carry && comms::bag_of(world, a.index) > 0 && shown++ < 32) {
            const auto& pp = opp::posterior(world);
            std::printf("EXPACT F %d %d %.4f %.4f\\n", world.round, static_cast<int>(world.me().handle), pp.fish, pp.mite); } });
''' + old
    assert s.count(old)==1;p.write_text(s.replace(old,new))
    assert (root/'params.h').read_text().count('opp_fish_stub = -1.0f, opp_mite_stub = -1.0f;')==1
    write(D/arm/'trace-source.json',source(trace))
    return trace


def drafts(arm, label, rows):
    listing=D/arm/(label+'-replays.txt')
    listing.write_text(''.join(str(Path(x['replay']).resolve())+'\n' for x in rows))
    log=D/arm/(label+'-drafts.tsv')
    pooled(['node','tools/replay/drafts.mjs',listing],log)
    parsed={}
    for line in log.read_text().splitlines():
        fields=line.split('\t')
        if len(fields)==3:parsed[fields[0]]=(fields[1],fields[2])
    assert len(parsed)==len(rows)==8
    return {(Path(x['map']).stem,tuple(x['order'])):parsed[str(Path(x['replay']).resolve())] for x in rows}


def trace_stats(name):
    # ab.py's raw batch records retain replay paths; inspect only our side.
    sp=R/'replays/ab'/name/'summary.json';s=json.loads(sp.read_text());out=[]
    for sub in s['suites']:
        bdir=R/sub['batch'];b=json.loads((bdir/'results.json').read_text())
        for match in b['matches']:
            side='a' if match['order'][0]==0 else 'b'
            replay=Path(match['replay'])
            if not replay.is_absolute():
                replay=R/replay if (R/replay).exists() else bdir/replay
            with zipfile.ZipFile(replay) as z:
                raw=z.read(f'team-{side}.stdout');text=raw.replace(b'\0',b'').decode(errors='replace')
            post=[];acts=[]
            for line in text.splitlines():
                fields=line.split()
                if fields[:1]==['OPPC'] and len(fields)==6:
                    post.append({'round':int(fields[1]),'unit':int(fields[2]),'fish':float(fields[3]),'mite':float(fields[4]),'other':float(fields[5])})
                if fields[:1]==['EXPACT'] and len(fields)==6:
                    acts.append({'target':fields[1],'round':int(fields[2]),'unit':int(fields[3]),'fish':float(fields[4]),'mite':float(fields[5])})
            out.append({'map':match['map'],'side':side,'replay_sha256':sha(replay),'stdout_bytes':len(raw),
                        'possibly_censored':len(raw)>=1048576,'posterior_observations':post,'activation_events':acts})
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('arm',choices=CAND);a=ap.parse_args();verify()
    (D/'smoke-maps').mkdir(exist_ok=True)
    for row in json.loads((D/'smoke-maps.json').read_text()):
        link=D/'smoke-maps'/Path(row['path']).name
        if not link.exists():link.symlink_to(row['path'])
    code="import sys;sys.path.insert(0,'research/ideas-2026-11-09/freshgate-tools');import fgate;fgate.build_seed(1004);fgate.build_body(1004,'Flp4');fgate.build_body(1004,'Mt3q')"
    pooled([sys.executable,'-c',code],D/a.arm/'body-build.log')
    body_seal(1004)
    for bot in (BASE,CAND[a.arm]):pooled(['cambc','build','--release',R/'bots'/bot],D/a.arm/'release-build.log')
    records={};traces={};trace=trace_copy(a.arm)
    for o,body in [('F','variants/spar-dvn1004-Flp4'),('M','variants/spar-dvn1004-Mt3q')]:
        base_name,bs,br=play(a.arm,BASE,body,'base-'+o)
        name,cs,cr=play(a.arm,CAND[a.arm],body,'cand-'+o)
        # Draft model is preserved; verify the sampled own ordered picks at runtime too.
        bd=drafts(a.arm,'base-'+o,br);cd=drafts(a.arm,'cand-'+o,cr);assert bd==cd, 'Ordered smoke drafts differ'
        records[o]={'base_run':base_name,'candidate_run':name,'base_summary':bs,'candidate_summary':cs,'ordered_drafts_match':True}
        tn,ts,_=play(a.arm,trace,body,'trace-'+o,debug=True)
        traces[o]=trace_stats(tn)
    ocean_name,_,_=play(a.arm,trace,BASE,'trace-Ocean',debug=True)
    traces['Ocean']=trace_stats(ocean_name)
    target='M' if a.arm=='chanM' else 'F'
    count=sum(len(g['activation_events']) for g in traces[target])
    write(D/a.arm/'smoke-proof.json',{'release':records,'trace':traces,'target':target,'target_activation_events':count,
          'note':'Small debug fixtures establish runtime activation only. Logging changes codegen/fuel; these games are not strength evidence or a classifier accuracy estimate. Each champion caps added activation stamps at32; complete gate measures both opponent effects.'})
    assert count>0,'No target activation observed; mechanism needs review before gate'
    verify()

if __name__=='__main__':main()
