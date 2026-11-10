# Tribute Safety audit on frozen502 — 2026-11-10

Decision: **no justified shipping candidate or test admission**. This bounded audit read existing code, cached aggregate results and two decoded live cases; it ran no builds, games, archive extraction or queue changes.

## Current code

Frozen source: `bots/variants/oc-501-draft10/src/`.

- `economy/bank.cc:144`, `tribute_safe`: compares recent damage and idle kill time with `min(channel time, tribute_window)`; `params.h:142` sets the window to 11.
- `economy/bank.cc:1309`, `continue_tribute`: an unsafe estimate alone does not force cancellation. With no recent damage, no home/attack opportunity, and a winning bag or no prey, it keeps the channel. A separate enemy-winning-channel interruption can also cancel.
- `model/safety.cc:3433`, `turns_to_kill_idle`: models enemies arriving at the stationary carrier.
- `model/safety.cc:2021`, `Reach::at`: immediate blows already apply target visibility, visible enemy wards and possible hidden wards where appropriate. Ground-target ways do not require target sight.
- `model/safety.cc:2676–2691`, `approach`/`walk_in`: after the immediate-hit check fails, arrival is approximated by path distance minus strike reach, with a minimum of one turn. It does not search for a future visibility-valid firing position. This is a conservative approximation, not an established erroneous cancellation.

The tribute predicates and idle-kill/approach functions match frozen494, apart from `self_acted()` cache invalidation around actions. No blanket claim that the complete494 and502 bots behave identically is implied.

## Exact existing case checked

Live Fish match `01a1c1f9-aba5-7d55-8cf3-7ab5789e826c`, our team B, Prism id7; map hash `7bcdfa41a761b506`. Decoded cache: `/home/ubuntu/tmp-offload/fishre/ana2/03f84eea5183ffd8/` (`meta.json`, `events.jsonl.gz`, `rounds.json.gz`); map in its referenced `mapFile`. Original replay: `/home/ubuntu/tmp-offload/fishre/repl_pri/01a1c1f9-aba5-7d55-8cf3-7ab5789e826c.repl26a`.

- Round675, step99657: Prism starts a 784-gem, 53-turn channel at `(2,14)`, altar `(1,15)`. Its bush cluster is exactly `(2,14),(2,15),(2,16)`.
- Round679, step100304: manually cancels with 49 turns left. At step100305 it immediately casts ground AoE at `(6,10)`, dealing 2830.3 damage to enemy Marcella id0 at `(7,9)`.
- Round681, step100618: restarts the 784-gem channel on the same tile. Prism remains at 1638 HP throughout the inspected interval. Recorded enemy turn-start views do not show Prism during the channel.

This looks like expensive cancel/restart cycling, but it is **not proven needless**: Marcella was approaching, could enter this small bush within the 11-turn safety window, and the cancellation enabled substantial damage. The replay does not record the exact internal Safety estimate or which cancellation condition fired. It is historical live evidence, not an execution of frozen502. No counterfactual outcome is claimed.

A second cached case, Mite match `01a1c218-677b-7910-b837-e9271f83815c`, `/home/ubuntu/tmp-offload/miteRE/ana/73606d1d5ce41196/`, has our Vesper id1 cancel a 200-gem bush channel at round541, attack nearby Heart of Ruin, then restart in the same turn. Heart's movement and ground dash damage likewise prevent treating bush invisibility as safety proof.

## Rules and evidence limits

Read `cambc-rules.yaml`: basic and unit-target attacks require personal visibility, but an enemy's own ward can supply it; an unseen ward cannot simply be ruled out. Ground-target AoE and Heart's dash damage can hit an unseen carrier. Enemies can walk into the bush cluster; moving, spell exclusivity and attack-reset rules must be respected in any future arrival bound. Camps ignore bush cover. Damage does not itself interrupt tribute, stun does, and an altar lock placed within 2 can cancel a channel without seeing the carrier. Our own cancellation retains the bag but discards channel progress.

`rounds.json.gz`'s `seenBy` is reconstructed from each enemy's turn-start view (`tools/replay/extract.mjs`), not continuous visibility or a proof that a future attack is illegal. Aggregate manual cancels also do not identify their internal branch. The cached safetrib metadata predates extractor schema3; this audit uses tribute events, champion positions/HP and visibility, not the corrected camp reward/mirror metadata.

Earlier C1 reduced self-cancels from 38% to 9% by cancelling only for a kill within one turn, but scored 48.8% in 20,480 doubled-fuel games and increased bags later lost at death 65%. Thus zero observed deaths during channels does not establish that their preventative cancellations were false. Existing safetrib tile-selection variants did not establish a gain either.

A visibility-aware future firing-position bound remains a hypothesis. These existing cases do not establish a safely avoidable cancellation or justify implementation, a sweep, or another gate.
