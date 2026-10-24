# Source-known candidate Prism deaths to camps

Read-only witness report from the 77 preserved 4db-vs-v33 extracted games. The event is `k=death` with `camp`, and the victim is the candidate-side Prism identified by the replay’s physical-side filename and champion metadata.

The larger scan found 27 candidate-side champion deaths to camps (six Prism); the selected three Prism events below retain the complete replay SHA256, absolute map path/hash, actual actor id/team, and nearby event context.

## gen-gen-caves-102300400-candidate-B.repl26a

- Replay SHA256: `481532d4487974341bdf6c3ccf56c71bebeb4fb0bc0cec55a1a8cec87f8ca4b3`
- Map: `gen-gen-caves-102300400-candidate-B` (`d80e0bcfb14b3892`), file `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/replays/willow-hyperion4db-vs-v33-a00fff-full1104-native-audit-v1/maps/d80e0bcfb14b3892.json`
- Candidate physical side: B; actor 4 team 1 Prism; round 114; camp id 38; death HP 4.8; carried gems 29.
- Camp metadata: {"id":38,"type":"Wolf","x":15,"y":16,"group":14,"hp":1350}
- Last three actor actions before death: [{"s":17182,"r":112,"t":6,"k":"move","a":4,"f":[17,17],"to":[17,18]},{"s":17183,"r":112,"t":6,"k":"recall_start","a":4,"gems":29,"at":[17,18]},{"s":17251,"r":113,"t":-1,"k":"recall_cancel","a":4,"gems":29,"cause":"damage","left":4}]
- Round health window: [{"round":112,"hp":320,"alive":1,"position":[17,18],"gems":29},{"round":113,"hp":4.8,"alive":1,"position":[17,18],"gems":29},{"round":114,"hp":0,"alive":0,"position":[null,null],"gems":0},{"round":115,"hp":0,"alive":0,"position":[null,null],"gems":0},{"round":116,"hp":0,"alive":0,"position":[null,null],"gems":0}]
- Incoming camp attacks in preceding/fatal rounds: [{"s":16967,"r":111,"t":-1,"k":"camp_attack","camp":38,"g":14,"tgt":4,"dmg":20},{"s":16970,"r":111,"t":-1,"k":"camp_attack","camp":40,"g":14,"tgt":4,"dmg":20},{"s":17110,"r":112,"t":-1,"k":"camp_attack","camp":38,"g":14,"tgt":4,"dmg":20},{"s":17113,"r":112,"t":-1,"k":"camp_attack","camp":40,"g":14,"tgt":4,"dmg":20},{"s":17251,"r":113,"t":-1,"k":"camp_attack","camp":38,"g":14,"tgt":4,"dmg":20},{"s":17254,"r":113,"t":-1,"k":"camp_attack","camp":40,"g":14,"tgt":4,"dmg":20},{"s":17400,"r":114,"t":-1,"k":"camp_attack","camp":38,"g":14,"tgt":4,"dmg":4.8}]
- Round-level group HP rows: []

## gen-gen-blob-102306200-candidate-A.repl26a

- Replay SHA256: `7636304ebb096090841a1c6ba71cd1ef4d944251e60f6ae49da557a7ed680c28`
- Map: `gen-gen-blob-102306200-candidate-A` (`bacb6cad2992b8f6`), file `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/replays/willow-hyperion4db-vs-v33-a00fff-full1104-native-audit-v1/maps/bacb6cad2992b8f6.json`
- Candidate physical side: A; actor 0 team 0 Prism; round 339; camp id 4; death HP 16; carried gems 32.
- Camp metadata: {"id":4,"type":"Golem","x":37,"y":28,"group":2,"hp":5000}
- Last three actor actions before death: [{"s":40767,"r":338,"t":4,"k":"recall_cancel","a":0,"gems":32,"cause":"damage","left":4},{"s":40778,"r":338,"t":5,"k":"move","a":0,"f":[39,29],"to":[40,30]},{"s":40779,"r":338,"t":5,"k":"recall_start","a":0,"gems":32,"at":[40,30]}]
- Round health window: [{"round":337,"hp":160,"alive":1,"position":[39,29],"gems":32},{"round":338,"hp":16,"alive":1,"position":[40,30],"gems":32},{"round":339,"hp":0,"alive":0,"position":[null,null],"gems":0},{"round":340,"hp":0,"alive":0,"position":[null,null],"gems":0},{"round":341,"hp":0,"alive":0,"position":[null,null],"gems":0}]
- Incoming camp attacks in preceding/fatal rounds: [{"s":40801,"r":339,"t":-1,"k":"camp_attack","camp":4,"g":2,"tgt":0,"dmg":16}]
- Round-level group HP rows: [[338,2,1,2,0,-1,1,4841.6]]

## gen-gen-cells-102306615-candidate-B.repl26a

- Replay SHA256: `ccfd37b2b7e046a5e41781e567f7b68feb63cfc9f030c882fd8db72d3a365edd`
- Map: `gen-gen-cells-102306615-candidate-B` (`7732d94dd51f60d3`), file `/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development/replays/willow-hyperion4db-vs-v33-a00fff-full1104-native-audit-v1/maps/7732d94dd51f60d3.json`
- Candidate physical side: B; actor 4 team 1 Prism; round 1860; camp id 36; death HP 2.2; carried gems 14.
- Camp metadata: {"id":36,"type":"Wolf","x":74,"y":45,"group":18,"hp":1350}
- Last three actor actions before death: [{"s":316000,"r":1858,"t":1,"k":"recall_cancel","a":4,"gems":14,"cause":"damage","left":2},{"s":316169,"r":1859,"t":1,"k":"attack","a":4,"f":[72,45],"to":[73,42],"tgt":1,"dmg":[[1,65.3]]},{"s":316170,"r":1859,"t":1,"k":"recall_start","a":4,"gems":14,"at":[72,45]}]
- Round health window: [{"round":1858,"hp":185.8,"alive":1,"position":[72,45],"gems":14},{"round":1859,"hp":2.2,"alive":1,"position":[72,45],"gems":14},{"round":1860,"hp":0,"alive":0,"position":[null,null],"gems":0},{"round":1861,"hp":0,"alive":0,"position":[null,null],"gems":0},{"round":1862,"hp":0,"alive":0,"position":[null,null],"gems":0}]
- Incoming camp attacks in preceding/fatal rounds: [{"s":315781,"r":1857,"t":-1,"k":"camp_attack","camp":36,"g":18,"tgt":4,"dmg":12.6},{"s":315950,"r":1858,"t":-1,"k":"camp_attack","camp":36,"g":18,"tgt":4,"dmg":12.6},{"s":316116,"r":1859,"t":-1,"k":"camp_attack","camp":36,"g":18,"tgt":4,"dmg":12.6},{"s":316285,"r":1860,"t":-1,"k":"camp_attack","camp":36,"g":18,"tgt":4,"dmg":2.2}]
- Round-level group HP rows: []

Per-camp HP at the death step is unavailable in the existing extraction. Map metadata gives initial individual camp HP; round data gives group HP. These are source-known nominations for bounded follow-up, not certification of the cause or of a survival-first ordering.

The earlier `camp_death` scan counted camps killed by actors, which is the opposite event and is excluded here.
