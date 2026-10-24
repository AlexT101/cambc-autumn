# Stable generalist Willow binding: source checkpoint

2026-10-24. Cambridge Battlecode rules and full `research/willow-v47-generalist-support-binding-design-20261024-v1.md` read; design SHA256 `9055f84850ff81601e0e784d7509d72f0d42c46b2ffe2fd5958facfa16481e1c`. Root authorized the independent f475 support arm and exact Stellar/Cassi draft compositions. No build, runtime, test/helper/script implementation, SDK/tool edits, canonical edit, EXPERIMENTS change, release or submission.

Frozen f475 source `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7` rehashed unchanged: `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`. Frozen Stellar/Cassi draft parents also verified: `0c166e820c493aaa222d5fd065fb56d9caff766c3f8caf8795d1898d4397a82d` / `3eed096b658e5db51630d44c346a9cf3a07c6624885d80e4a5a2eed442641938`.

| Child under bots/variants | Purpose / roster | 29-file source aggregate |
| --- | --- | --- |
| willow-v47-generalist-support-work | Independent support change; same P/V/M/W/HoR draft, also the Prism code-cost control | `98470a7454a14a8aac2c501cdd702c5fc06b27862ba9948a3ed27d7bff1115c1` |
| willow-v47-stellar-five-support-work | Exact support + frozen S/V/M/W/HoR substitution | `f5daacb599a2d2e248f9cef82126e6ec4761647995c9b454a5d3c21b8b5ed86a` |
| willow-v47-cassi-five-support-work | Exact support + frozen C&I/V/M/W/HoR substitution | `ace0519e41ba5261d52955c2f17316de1099ad3ecc88d5c73f0a74b24b047421` |

Manifests are `research/willow-v47-generalist-support-source-v1-manifest.sha256` and `research/willow-v47-{stellar,cassi}-five-support-source-v1-manifest.sha256`. Each has29 entries and its SHA256 is the aggregate above. Src only; no `.cambc`, backups/rejects or whitespace diagnostics.

The common delta is `research/willow-v47-generalist-support-source-v1.patch`, SHA256 `c76a30c4e7106685ced623e25dc58bf100a3088d27ed5b45e9b9117dec5a4ff6`: bot.cpp/comms.cpp/world.h only,39 insertions/41 deletions. The shared inline support_pair function caches two indices once from the complete actual allied roster, choosing Prism before Stellar before Cassi and pairing it with Willow. It never selects by health, alive/visible state, cooldown, channel or proximity. A missing client or healer returns no dedicated pair. Roster indices persist across death/respawn/invisibility; existing endpoint validity checks reset current mailbox state and recovery as before.

Comms and both local_support/decide entry use this same selector. All former local recovery-role tests now use support_client identity. The wire parity/payload/epochs and the legacy support_mailbox::prism name for role0 remain unchanged; exactly the bound client requests on even rounds and Willow offers on odd rounds. Issac cannot publish as client and receives only ordinary heal targeting. A dead/hidden selected client does not promote another body. No new packet fields or native reads are introduced by binding.

Actual Prism gem retention, capture-holder preference, item/shopping economics and tactics outside formation are untouched. Abilities.cpp remains f475, so the independent Prism-only approach-cast asymmetry is not silently changed. Existing visibility/readiness, safe station, useful heal, protected capture/contest/bank/shop, duration/no-progress closure, reentry, all-ally heal selection and ordinary Willow fallback are retained. The alternate clients use their actual HP/output/heal gain in the original recovery arithmetic; no multiplier or promised future heal is added.

Full-file exact-union verification: each composed draft.cpp matches its frozen role parent; every other28 file matches generalist-support-work. The normalized support delta against either role parent exactly matches the common patch hunk/context bodies. Base and role parents remain unchanged. Neither compositions include hop/escape/mixed-cast/recall/v48 overlays.

Additional deltas and hashes:

- Stellar versus f475: `research/willow-v47-stellar-five-support-source-v1.patch`, `497defa2a09a10ae4f59589e82694c67a6ca8ca1dd75590a25fea46de63193b3`.
- Stellar versus frozen Stellar role: `research/willow-v47-stellar-five-support-vs-role-source-v1.patch`, `a6a365e07e061392885339257447b07d15a79d73d4d170c6f6733d298f481a60`.
- Cassi versus f475: `research/willow-v47-cassi-five-support-source-v1.patch`, `c5bb41f69905fff8155bf4a3fa1579748a74fec2684a34da7cd5e11dcdaa0a5f`.
- Cassi versus frozen Cassi role: `research/willow-v47-cassi-five-support-vs-role-source-v1.patch`, `5a37f01b6d5d0228f07509c44bda979090b216d332d320daa69fb57c5efb37f0`.

Cost is one roster scan on first use, cached index lookups thereafter, replacing the private comms selector and repeated local type scans. New service admission can intentionally perform work previously absent for Stellar/Cassi; existing fuel cutoffs/code generation can also change Prism-control actions, so byte-identical behavior is not claimed. No new fuel gate, field, camp search or scheduler exists. Independent source review and runtime controls remain required: priority when multiple client types exist, dead/hidden/channelling client without switching, missing client/Willow, Issac nonwriter, protected work, more urgent nonclient heal and recovery completion. Cassi healing does not certify a distant Issac safe or coordinate both bodies' retreats.
