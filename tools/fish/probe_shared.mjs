// Read both teams' shared (8 bytes) and draft (first 64 bytes) memory along a replay.
// Replays hold no memory writes: these read zeros all game, even for bots that use comms.
import fs from 'node:fs';
import { Engine, compileEngine, replayEngine } from '../replay/engine.mjs';
const [file, every = '20000'] = process.argv.slice(2);
if (!file) throw new Error('usage: node tools/fish/probe_shared.mjs REPLAY [EVERY_STEPS]');
const bytes = fs.readFileSync(file);
const e = await Engine.create(await compileEngine(replayEngine(bytes)));
const g = e.openReplay(bytes), x = e.x, buf = x.Engine_Malloc(64);
g.seekStart();
let n = 0;
do {
  if (n++ % +every) continue;
  const round = g.read().header().round;
  for (const [name, fn, len] of [['shared', x.Game_Visualiser_GetSharedMemory, 8], ['draft', x.Game_Visualiser_GetDraftMemory, 64]])
    for (const team of [0, 1]) {
      // (game, team, offset, out, length)
      e.ck(fn(g.h, team, 0, buf, len), name);
      console.log(round, name, team, Buffer.from(new Uint8Array(x.memory.buffer, buf, len)).toString('hex'));
    }
} while (g.next());
g.destroy();
