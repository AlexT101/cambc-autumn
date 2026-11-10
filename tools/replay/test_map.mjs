import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildMap } from './map.mjs';

function fixture(symmetry = 'horizontal') {
  const vertical = symmetry === 'vertical';
  const xy = (x, y) => vertical ? [y, x] : [x, y];
  const point = (type, x, y, group) => ({ type, x: xy(x,y)[0], y: xy(x,y)[1], group, maxHp: 120 });
  const canonical = [point(2,4,2), point(3,2,4), point(0,1,6)];
  const camps = [point(2,4,2,0),point(3,2,4,1),point(3,6,4,2),point(0,1,6,3),point(0,7,6,4)];
  return { map: { width:9,height:9,symmetry,champsPerTeam:3,spawnA:{minX:0,minY:0,maxX:2,maxY:2},walls:[],holes:[],bushes:[],altars:[],camps:canonical,
    groups:[{camps:[0],gems:7,gold:0,respawn:50},{camps:[1],gems:0,gold:20,respawn:50},{camps:[2],gems:4,gold:40,respawn:40}] }, camps };
}
for (const symmetry of ['horizontal','vertical']) test(`${symmetry}: self-mirrored camp does not shift later rewards or mirrors`, () => {
  const {map,camps}=fixture(symmetry),out=buildMap(map,camps);
  assert.deepEqual(out.groups.map(g=>[g.gems,g.gold,g.respawn,g.mirror]),[[7,0,50,0],[0,20,50,2],[0,20,50,1],[4,40,40,4],[4,40,40,3]]);
});
test('runtime order does not define canonical camp identity', () => {
  const {map,camps}=fixture(), out=buildMap(map,[camps[4],camps[1],camps[0],camps[3],camps[2]]);
  assert.deepEqual(out.groups.map(g=>[g.gold,g.mirror]),[[0,0],[20,2],[20,1],[40,4],[40,3]]);
});
test('rotational ordinary pairs retain engine-provided group rewards',()=>{
  const {map}=fixture();map.symmetry='rotational';map.camps=[{type:0,x:1,y:2}];map.groups=[{camps:[0],gems:4,gold:40,respawn:40}];
  const out=buildMap(map,[{type:0,x:7,y:6,group:1},{type:0,x:1,y:2,group:0}]);
  assert.deepEqual(out.groups.map(g=>[g.gems,g.gold,g.respawn,g.mirror]),[[4,40,40,1],[4,40,40,0]]);
});
test('missing coordinate correspondence fails extraction instead of writing a wrong map',()=>{
  const {map,camps}=fixture();assert.throws(()=>buildMap(map,camps.slice(0,-1)),/cannot match/);
});
