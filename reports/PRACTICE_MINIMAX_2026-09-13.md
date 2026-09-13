# Minimax practice run — 2026-09-13

The local practice runner completed nine self-play matches across Standard 11×11, Royale 11×11, and Royale 19×19.

| Ruleset | Board | Seeds | Result |
|---|---:|---:|---|
| Standard | 11×11 | 101, 202, 303 | 2 wins, 1 loss |
| Royale | 11×11 | 101, 202, 303 | 1 win, 2 losses |
| Royale | 19×19 | 101, 202, 303 | 3 wins |

The Standard loss ended as a self-collision after the bot entered a progressively constrained region; the final turns had a trap penalty and then no hard-safe candidate. One Royale 11×11 loss ended at the shrinking hazard ring after health fell to 10, with hazard and starvation gates active and no viable search result. The other Royale 11×11 loss was a late head collision in a two-snake position; this remains the most actionable tactical risk for future replay analysis.

No constants were changed from this batch. The hazard loss looked forced once the ring closed, and changing hazard avoidance without a counterexample could make survivable routes worse. The next tuning batch should target the late two-snake head contest and earlier escape preservation in Standard.

Raw replay files are generated under `reports/practice-minimax-*` and ignored by Git. Re-run with:

```bash
.venv/bin/python scripts/practice.py --self-play \
  --seeds 101 202 303 \
  --output reports/practice-minimax-next
```
