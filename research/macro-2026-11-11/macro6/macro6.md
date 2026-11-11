# macro6: the carry economy (ocean = macro6-carry3)

## Result
macro6-carry3 against ocean-ref-b7c87cf, at --fuel 200000 with no test draft, on fresh ladder-v2 suites:

| Suites | Win % of 10240 | 95% CI |
|---|---|---|
| s-600001..20 | 56.0 | 55.1-57.0 |
| s-600021..40 | 56.2 | 55.2-57.1 |
| s-600041..60 | 55.2 | 54.2-56.1 |
| s-600061..80 | 55.0 | 54.0-55.9 |
| s-600081..100 | 56.5 | 55.6-57.5 |
| **Pooled** | **55.77 of 51200** | **55.34-56.20** |

- **Stress maps** (`--mix varied`, v-610001..20): 53.5% of 10240 (CI 52.5-54.4).
- **Fuel:** out-of-fuel turns are level with the ref.
- **Target:** the 60% target was not reached.

## Design
- **The mechanic:** the Prism gains +1.5 Focus per carried gem, and a Focus shard (+8 Focus) costs 30 gold. A gem kept by a Prism is therefore worth 1 + per_gold × (1.5/8) × 30 gems while it keeps the bag (keeps_bag: below the win, time left to bank, healthy).
- **Where it is priced:**
  - holder_value (which holder takes a capture);
  - the Prism's takeover of allies' gem holds;
  - its joins (J);
  - its solo, kited, risky and crew farm values (S/K/C);
  - every prune bound, through keep_most.
- **Effect:** the Prism becomes the team's gem sink and fight engine. The edge comes from captures (+25 gems by round 300, +41 by round 500).
  - In games with a Prism we win 58.2%; in the 20% of games without one, 50.2%.
  - K probes (bonus × 0.5 / 2 / 4) show the scale is at its optimum.

## Every A/B (s-600001..20 unless noted, 10240 games)
| Candidate | Change | Win % | Verdict |
|---|---|---|---|
| carry | Prism gem economy | 54.1 (53.9 on s-600023..36, 7168 games) | won |
| carry2 | + Prism joins (J) priced | 55.2 (55.0 held out) | won |
| **carry3** | + S/K/C paths priced | **56.0** | **best** |
| carry4 | Focus-aware kill value | 56.0 | level |
| carry5 | audit fixes | 55.3 | level |
| k05 / k2 / k4 | bonus scale | 54.2 / 55.6 / 54.9 | scale optimal |
| posture | Lanchester posture | 48.3 | lost |
| stakes | carrier recall line | 48.8 | lost |
| pzone | Prism zone risk, linear stake | 54.5 | lost |
| pzone2 | win-probability stake | 56.1 | level |
| postup | upside-only posture on carry3 | 55.6 | level |
| h05 / h2 | rate horizon × 0.5 / × 2 | 56.0 / 54.8 | not a lever |
| follow | follow-up (end-position) value | 54.2 | lost (out-of-fuel turns doubled) |
| follow2 | same, as a post-loop re-rank | 55.0 | lost |
| close | stun-free window for long tributes | not A/B'd | local 25% vs 55% |

## Lessons
1. **Pricing a mechanic the bot left unpriced wins; risk-reduction loses.** Posture, stakes, pzone and close each lost 1-2 points, because caution costs time at work.
2. **The economy is now calibrated.**
   - The horizon, the bonus scale and earlier scalar probes are all flat around the tuned point.
   - Follow-up value adds noise. One likely reason is that a future job's worth ignores competition for it.
3. **Variance in a race.** Measured P(win | asset lead) ≈ σ(0.018 × lead). Lead-shaped caution (pzone2) is neutral, and pressing a numbers lead (postup) is neutral.
4. **Small local samples mislead.** 16-game samples showed large effects that vanished at 10k games.
5. **The edge has a ceiling.** It exists only in Prism games, and the draft (off limits) fixes the Prism's share of games. Reaching 60% overall would need about 62.5% in Prism games.
6. **Open lead: the Monolith.**
   - In 62% of Monolith-map games nobody captures it, and the first capturer wins 76%.
   - carry3 excludes the Monolith from the Focus bonus.
   - macro6-mono, which extends it, was being built at the end and was not A/B'd.

Full log: macro6-log.md. Patches: patches/. Analysis scripts: /home/ubuntu/wt/macro6-work/endg/.
