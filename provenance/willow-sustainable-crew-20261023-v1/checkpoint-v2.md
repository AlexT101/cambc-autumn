# Sustainable crew candidate v2

Exclusive variant: `bots/variants/willow-sustainable-crew-work`.
Parent and unchanged canonical source hash: `a67dc0a32d4b9d001a8c514dc86aa1d9f4aa9d91bc380f2df2ce59b649ce6d21`.
Candidate source hash: `69010aea272d211599594c5a9f12b71f54b52ea83ec9f39cbe010541291a7d70`.
Hash convention: run `shasum -a 256 src/* | shasum -a 256` inside the bot directory.

V2 applies Astra's two bounded static-review corrections to v1:

- The new early passing restrictions explicitly require ordinary farm (`decision == 'F'`) and a ranged actor. Nonordinary farm contexts retain their original incumbent and allied-engagement behavior.
- Lazy help certification runs immediately before the existing final stale check. That check therefore covers a cold grouped forecast or centre-to-altar lookup before any claim mutation or follow-on gameplay action. No SDK query or fuel gate was added.

All v1 gameplay changes and bounds otherwise remain: grouped help must fit the current spare-health and deadline budgets; shared forecasts preserve arrival/remaining-work arithmetic and are retained when already computed; unaffordable nonclaimed work retains the risky fallback; harmless DPS, free melee passing, existing partner claims, and spell kiting remain available.

Pre-build preserved artifacts:

- `candidate-src-v2/`: full source snapshot, verified byte-identical to working candidate.
- `candidate-v2-files.sha256`: full per-file manifest.
- `candidate-v2-vs-parent.patch`: exact complete source patch against frozen a67 parent.
- All parent/v1 snapshots, manifests, patch, and checkpoint remain untouched.

Static checks: canonical hash still a67; snapshot matches candidate; diff whitespace check emitted no diagnostics. Astra independently verified the v2 aggregate hash and returned source PASS with no remaining blocker. No build or runtime performed.

Fuel remains a runtime question. There is no new explicit allocation or group scan in the patch, but existing helpers reached by the single lazy certificate may do cold field work or allocate transitively, particularly `centre_to_altar`. V1's allocation statement must not be read as excluding that existing helper work. Heavy-worker validation must measure the actual cost.
