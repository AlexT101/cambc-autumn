import fs from 'node:fs';
import {Engine,compileEngine,replayEngine,STEP_KINDS} from '../../../tools/replay/engine.mjs';
const bytes=process.argv.slice(2).map(p=>fs.readFileSync(p));
const module=await compileEngine(replayEngine(bytes[0]));
const es=await Promise.all(bytes.map(()=>Engine.create(module)));
const gs=es.map((e,i)=>e.openReplay(bytes[i]));
gs.forEach(g=>g.seekStart());
let prev=[];
for(let i=0;;i++) {
 const states=gs.map(g=>{const s=g.read();return {h:s.header(),c:s.championsLite()};});
 if(JSON.stringify(states[0])!==JSON.stringify(states[1])) {console.log(JSON.stringify({i,prev,states},null,2));break;}
 prev=states;
 const next=gs.map(g=>g.next());
 if(!next.every(Boolean)) {console.log('end',i,next);break;}
}
gs.forEach(g=>g.destroy());
