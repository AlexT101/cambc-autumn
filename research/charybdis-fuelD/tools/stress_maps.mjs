// Camp groups beyond the normal suites' 49-member maximum, for conditional fuel tests.
import fs from 'node:fs';
import {createEngine} from '../../../tools/mapgen/wasm.mjs';
const engine=await createEngine();
const dir='maps/suites/fuelD/largegroups';
fs.mkdirSync(dir,{recursive:true});
for(const mixed of [false,true])for(const size of [40,64,100])for(const picks of [3,5]) {
 const camps=[];
 for(let y=6;y<size-6;++y)for(let x=size/2-2;x<size/2;++x)
  camps.push({type:mixed && (y===6 || y===size/2 || y===size-7)?'wolf':y%5===0?'gem_cluster':'gold_cluster',x,y});
 for(const [x,y] of [[8,8],[8,size-9],[size/4,12],[size/4,size-13]])
  for(let dx=0;dx<3;++dx)camps.push({type:dx===1?'gem_cluster':'gold_cluster',x:x+dx,y});
 const map={width:size,height:size,symmetry:'horizontal',picks,spawn:{minX:2,maxX:5,minY:size/2-2,maxY:size/2+2},camps,
  walls:[],holes:[],bushes:[],altars:[[10,size/2-4],[size/2-5,3]]};
 const bytes=engine.encode(map);
 engine.load(bytes);
 fs.writeFileSync(`${dir}/${mixed?'mixed':'clusters'}-${size}-${picks}.map26a`,bytes);
 console.log(`${size}x${size}, ${picks} picks: central group ${4*(size-12)} members`);
}
