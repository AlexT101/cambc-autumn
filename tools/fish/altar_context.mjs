// Add actor-visible lock state and verify the cached pre-decision coordinates.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import {Engine,compileEngine,replayEngine} from '../replay/engine.mjs';
const [manifest,cache,out,part='0',parts='1']=process.argv.slice(2);
if(!out)throw Error('usage: altar_context.mjs MANIFEST CACHE OUT [PART PARTS]');
fs.mkdirSync(out,{recursive:true});
const engines=new Map();
const dist=(a,b)=>Math.max(Math.abs(a.x-b[0]),Math.abs(a.y-b[1]));
for(const [index,entry] of JSON.parse(fs.readFileSync(manifest)).entries()){
 if(index % +parts !== +part)continue;
 const key=entry.sha256.slice(0,16),dest=path.join(out,key+'.json');
 if(fs.existsSync(dest))continue;
 const old=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(cache,key+'.json.gz'))));
 const requests=new Map();
 for(const t of old.turns){
  if(!t.end || t.finish!=='End turn')continue;
  const a=t.actions.find(a=>a.kind==='Submit gems') ?? t.actions.findLast(a=>a.kind==='Recall');
  const s=a?.before ?? t.end,m=s.me;
  if(!m.alive || !m.gems || m.channelType || (m.roundFlags&128) || m.buffs.some(b=>b.type===1))continue;
  const altars=old.map.altars.filter(p=>dist(m,p)<=1);
  if(!altars.length)continue;
  const step=a ? a.step-1 : t.actions.at(-1)?.step ?? t.step;
  requests.set(step,{round:t.round,actor:t.id,step,me:m,altars,attempt:a?.kind==='Submit gems'});
 }
 const bytes=fs.readFileSync(entry.file),v=replayEngine(bytes);
 if(!engines.has(v))engines.set(v,await Engine.create(await compileEngine(v)));
 const g=engines.get(v).openReplay(bytes),rows=[];
 try{
  let step=-1;g.seekStart();
  do{
   step++;
   const r=requests.get(step);if(!r)continue;
   const snap=g.read({team:entry.side,champion:r.actor}),me=snap.champions().find(c=>c.id===r.actor);
   for(const k of ['x','y','gems','hp','channelType'])if(me[k]!==r.me[k])throw Error(`${key} ${step} ${k}: ${me[k]} != ${r.me[k]}`);
   const locks=[];
   for(const [x,y] of r.altars)for(const team of [0,1]){
    const e=g.e;
    if(g.x.Game_API_GetAltarLock(g.h,g.perspective({team:entry.side,champion:r.actor}),x,y,team,e.args))continue;
    locks.push({x,y,team,hits:e.dv.getUint32(e.args+20,true)});
   }
   rows.push({...r,me:undefined,items:me.items,locks});
  }while(g.next());
  if(rows.length!==requests.size)throw Error('missing requests');
  fs.writeFileSync(dest,JSON.stringify({game:key,side:entry.side,rows}));
  console.log(key,rows.length);
 }finally{g.destroy();}
}
