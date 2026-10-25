GUIDE = r"""REPLAY NARRATIVES (tools/replay/narrate.py)

Every statement is read off the replay (engine events and per-round state); destinations come from hindsight: a walk
is named after what the champion did when it stopped. Nothing here is a guess about intent.

FILES
  index.txt                one line per game: file, map, teams, winner, rounds, tributed gems
  legends/<map>-<hash>.txt map features with stable names, walking distances from each spawn, ASCII map
  games/<A>_vs_<B>__<group>-<n>-<map>.txt          timeline, one line per leg+anchor, fight, or STATE (every 100 rounds)
  games/<...>.fights.txt   per-fight transcript: every turn of every participant, from 2 rounds before to 2 after
  episodes/<kind>.txt      one line per episode across all games (grep by team, champion, map, tag)

NAMES (legend)
  Map features come in symmetric pairs, numbered by walking distance from a spawn: Elk2, Alt1, B7 (bush cluster).
  The suffix is relative to the team the line is about: .own (nearer its spawn by walking), .enemy, .mid (equidistant;
  .mid' is the mirror twin). So "Elk2.own" for team A and for team B are mirror images, and lines compare across
  sides and games on the same map. Camp groups are named after their strongest monster (Mono, Golem, Elk, Wolf; Gems
  and Gold for cluster-only groups); the legend gives each group's monsters, gems, gold and respawn.
  A tile is written "(x,y) Elk2.own+3 bush:B4.own": coordinates (origin bottom-left), the nearest camp group/altar/spawn
  and its walking distance (+N), and the bush cluster if the tile is a bush. "spawn.own" is the team's spawn region.
  d / walk dist = walking distance (8-neighbour steps; walls, holes and altars block; dashes can cross holes, so a leg
  with dashes can be shorter than its walk dist).

EVERY LINE carries "[team] Champion". In episode files the prefix is
  <map> <game> r<round> [<team>] <Champion> (<side A|B>,<W|L> vs [<opponent>])
Other champions are named relative to that team: "enemy Prism", "ally Ryth" (or just "Ryth" for an ally).
  A team's own lines:      grep -E ' r[0-9]+ \[Mite\] ' episodes/wards.txt
  Lines against a team:    grep 'vs \[Mite\])' episodes/deaths.txt
  One champion of a team:  grep -E ' r[0-9]+ \[Mite\] Vesper ' episodes/tributes.txt

TIMELINE LINES (sorted by the round each line starts; a walk+anchor line starts when the walk starts. One team's
  view of a game: grep -E '^r[0-9]+ +\[Mite\]' games/<file>.txt)
  walk rA-rB <from> -> <to> (N steps, walk dist D, direct|indirect: X% of steps closer|loop back to its start tile)
      a leg: consecutive rounds of walking/standing between two anchors. <to> is where the next anchor happened.
      direct = >= 90% of steps reduced the walking distance to the leg's end and steps <= 1.15 x distance + 1.
      [turned back rT at (x,y) after K steps away from the destination, approaching L dA->dB, saw ..., ally died ...]
      = K consecutive steps that each increased the walking distance to the leg's end; L (if any) is a landmark whose
      walking distance fell on every one of those steps. "saw" = enemies in its turn-start vision around the turn.
      "with X" = ally within 3 tiles for at least half the leg; "seen by X@rN" = enemy X saw it at X's turn start
      (first round); "via enemy half", "through bush ..." = tiles crossed.
  -> ANCHOR, one of:
    CAMP <group> rA-rB: hits on that camp group (short excursions within 5 tiles merged): who woke it, damage dealt
      (share of the group's full hp), allies hitting it, camp damage taken, who cleared it (last hit), rounds stood on
      its capture tiles, capture (shares gems/gold) or who else captured it, or "left with N hp standing".
    FIGHT Fk rA-rB: the rounds this champion was hitting or being hit in engagement Fk (gaps <= 3 rounds); damage
      dealt/taken in those rounds, kills, exit (see fights).
    TRIBUTE <altar> bag N banked N (team total T) | CANCELLED (cause); saw = enemies in its vision during the channel.
    RECALL from <tile> bag N hp X% -> home | interrupted (cause). Only real recalls: completed, or ended >= 2 rounds
      after starting. Many bots start a recall and cancel it at their next turn every turn (listed once as HABIT in
      the game header and in episodes/habits.txt); those feints are never reported, and a feint that completes because
      the champion stood still for 5 turns shows as a RECALL.
    IDLE N rounds at <tile> (no event; nearest altar/camp, bush): >= 3 rounds without moving and without an anchor.
    SHOP, DIED (killer, assists, bag, what it bought while dead, respawn round), TELEPORT.
  | WARD at <tile>, LOCK on <altar>, bumped unseen unit at (x,y) (a walk into a tile holding a hidden unit), used ...
      point actions during the line's rounds.
  FIGHT Fk rA-rB at <tile>: [team] participants vs [team] participants | present NvM (alive within 8 tiles of the first
      hit) | first hit X -> Y dmg rN (", answered same round" if the other team also dealt damage that round)
      [tags] | kills a-b | who killed whom (bag carried).
  STATE: per team tributed gems, carried gems, unspent gold, formation (groups of champions linked by <= 4 tiles; d = dead).

FIGHTS (engagements)
  Champion-on-champion damage (and stun-only hits) clustered as analysis/fights.py does: hits sharing a champion within
  3 rounds and 16 tiles, or within 1 round and 8 tiles; clusters over 25 rounds split at quiet rounds.
  closed in: the last walk/dash in the 5 rounds before the first hit (up to it) that took a champion from beyond 4
    tiles (ability range) to within 4 of an enemy it saw at its turn start. It can differ from the first hitter.
  Tags on the first hit:
    blind   the victim's latest turn-start vision (its own view and its ward, as its bot saw it) lacked the attacker.
    ambush(bush|still)  blind, and no enemy saw the attacker at their turn starts in the 3 rounds before, which it
            spent in a bush (bush) or without moving (still). It may have been hitting a camp meanwhile.
    hit from bush Bn    the attacker stood on a bush tile.
  Per-turn tags in transcripts:
    retreat  moved, dealt no damage, ended farther (Chebyshev) from every enemy it saw at its turn start.
    kite     dealt damage and ended the turn farther from its target than it started.
    chase X  moved closer to enemy X whose previous turn was a retreat.
  Exits: died rN | disengaged rN at hp X% (first of >= 2 consecutive retreat turns after its last damage dealt)
    | stayed; ", recalled (home rN)" if a recall completed within 10 rounds of the fight's end.
  Transcript header: the fight line from the first hitter's team view, each participant's hp and bag at the start and
    whole-fight damage, and the hit list (round, attacker->victim, damage; names relative to the first hitter's team).
  Transcript line: rN tK [team] Champ (x,y)->(x,y) [bush]: actions | hp after the turn, bag | sees (enemies in its
    turn-start vision) | tags. "camp <group> hits ..." lines are camp attacks on participants that round.
  tK is the champion's turn slot in the round (0 = first to act); turn order is reproduced from the rules exactly.

EPISODE FILES (episodes/)
  fights     one line per fight per team (that team's view; exits included)
  ambush     first hits that were blind, AMBUSH or BLIND-HIT, with the attacker's tile, bush, victim hp/bag, kills
  deaths     where, killer/assists or camp, bag lost, hp before the blow, what it was doing (track), the fight, what it
             saw in the last 3 rounds, allies within 4 and enemies within 8 (omniscient: the victim may not have known)
  tributes   altar, bag, channel, result, where the bag came from (captures/kills since its last bank or death), hp,
             enemies seen during the channel, enemies within 8 of the altar (omniscient), altar choice from the start
             of the walk there (chosen vs nearest by walking), locks on the altar
  recalls    real recalls with tile, walk home, bag, hp, gold, enemies seen in the last 3 rounds, what it bought after
  wards      tile (bush/open, half), placer's distance, nearest altar/camp, which altars and camp tiles the ward's
             view covers (exact shadowcast, radius 6), how long until that champion's next ward, ward-only sightings
             (enemies in the placer's turn-start vision that stood in the ward's view and outside its own view), fights
             within 8 tiles in the next 20 rounds
  shop       purchases per visit (shard names: family+stat, (E) = emblem), gold left, items held
  camps      each capture payout (team view): group, sharers, share of the group's damage dealt by the capturing team,
             last hit; STEAL (enemy half), DENIAL (enemy did most damage), contested (capture reset while contested)
  locks      lock placements (tributes cancelled, destroyed round) and tributes blocked by a lock
  lurks      >= 3 rounds in one bush cluster, >= 2 of them standing still, no attacks, unseen by every enemy; enemies
             that came within 4 (omniscient); outcome: its first hit / fight / camp in the next 3 rounds
  openings   rounds 1-150 per champion as an anchor sequence (cap = captured, clr = cleared, hit = left it standing)
  habits     per-champion repeated no-op patterns (recall feints)

NOT IN THE REPLAY (never inferred here)
  intent and targets of a bot; its beliefs about unseen enemies (bots infer them); the 8 bytes of team memory;
  rejected actions (they leave no event); fuel per turn (only out-of-fuel turns); opponents' stdout; capture progress
  as a bot sees it. Vision is per champion (own view + own ward); teammates do not share vision.
"""
