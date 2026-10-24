# Sighting-arbitration v3 first Pilgrimage cell

This single-cell diagnostic ran the v3 whole-team candidate and exact latest parent as physical A against frozen v33 as physical B on `00pilgrimage`, each with normal native drafts, Release mode, and 100,000 fuel per turn. The games ran sequentially with one job and the 10%-duty worker. Both batches completed with no failed matches.

Both games produced the same draft on both teams: Prism, Vesper Vale, Marcella, Willow, Heart of Ruin. Each ended with candidate/parent A winning round 1358 by 1030–210 gems. The candidate had zero play rollovers/errors; the exact parent also had zero. Frozen v33 had six play rollovers and zero native errors in each game: actor 5/Prism had 2, actor 8/Willow 3, and actor 9/Heart of Ruin 1. Draft/other-phase rollovers and bot errors were zero. Caught `act error` lines were zero for all four bot instances.

The candidate ZIP SHA-256 is `047361a2b4f1f1a2aaf2a4e125dd193b4084d288e8c0c97a571d455c216671bc`; its inner `replay.repl26a` SHA-256 is `ec93b629442b03f09e8915abbd373909553756365e3af55cc1f93cea5a680cd9`. The parent ZIP SHA-256 is `85dd81ebcacf6b1265c79bc8afd0605d8fa68401ff7d8a8e68b49cb4fa81d1da`; its inner replay SHA-256 is `2af22092f2e52b04c914238954937cf38d106687384be158fddf0f7fb06b4d5d`. Both inner payloads and decoded event/round records differ.

The first public event divergence is round 1183. Both Prism arms cancel the same four-tick recall stub; the parent restarts recall in place at (13,39), while the candidate moves to (12,38) before restarting recall. The candidate then follows a differing route through about round 1208. Both later carry the same 141 gems into a tribute at round 1311 and finish it at round 1326. Final score, round, draft, and submitted gems match. Replay snapshots do not expose the shared-memory writes or native priority setter, so this does not establish protocol activation or explain the behavior change.

Source, build, engine, map, native audit, replay, and compact preservation pins are in `PAIR-RESULT.json` and `PRESERVATION-MANIFEST.json`. These two diagnostic games do not establish a win-rate or a competitive benefit.
