# Viva preparation

Read and run the code yourself before submitting. This guide is an explanation, not a claim that you already understand it.

## A ten-minute demonstration

1. Show README's row for ID 233062, then run `python run.py --agent utility --seed 917` twice. The JSON must be identical.
2. Explain `Harbour.__init__`: exactly one RNG pre-generates arrivals and storms, so all policies see paired exogenous events regardless of their decisions.
3. Explain `Harbour.advance`: one tick has a defined event order; picking, dropping and moving are mutually exclusive actions for a worker. Rotation prevents the same worker always winning contested movement.
4. Explain `choose_target`: baseline never reaches it, reflex has no remembered warning, model stores warning/target, utility uses six score terms. Increasing the crowd penalty may spread workers but can increase travel or churn. Utility is not reinforcement learning.
5. Explain `move`: choose a legal reducing neighbour, otherwise BFS; `occupancy[n] < 3` is checked before each move and counters update immediately.
6. Explain `Master.turn`: build text, call/replay, parse, validate, ground final statement, execute, log, feedback; retry twice, then utility fallback. Never eval model text.
7. Open a rejected raw output in the log. Show why its ship claim or action is unsupported. Compare with the exact report from the same record.
8. Show `execute` and `test_approval_gate`. A note saying APPROVE is only text; only a separate human callback grants authority. The approval check is after validation and immediately before the sensitive mutation.
9. Reproduce one LLM seed without internet: `python run.py --agent llm --seed 11 --replay logs/llm_log.jsonl`. Explain how prompt hashes detect code/state drift.
10. Explain the conclusion using the actual CSVs: raw throughput, knock-outs, variability, invalid outputs, fallbacks and latency are different measures. Do not claim that fallback deliveries demonstrate LLM intelligence.

## Questions to be ready for

- Why is the world stochastic if a seed makes a run repeatable? The environment samples exogenous events; a seed fixes one realisation.
- What does a baseline wait of hundreds of ticks mean? Most ships never dock; their queue wait is censored at 600 rather than excluded. This underestimates eventual wait but permits a fair fixed-horizon comparison.
- Why can a ship depart before its cargo reaches the warehouse? It leaves when empty as required; workers may still carry the final units.
- Why do only onset workers get knocked out? That is the stated rule. The simulation does not silently invent continuing storm damage.
- Why is the ship at y=-1? Ships moor offshore; the playable apron is on the north edge at y=0. A worker there is adjacent to the ship and exposed at storm onset.
- Does zero crowding violate the emergence requirement? No. Lanes and queues can emerge below the hard cap; the heat map measures repeated path use, not illegal occupancy.
- Why is utility chosen although reflex has a higher cargo mean? A safety-adjusted development objective penalises knock-outs. Report both raw throughput and the safety trade-off.
- Is a statistically nonzero mean difference larger than run variation? Not necessarily. The paired mean can have a narrow CI even when it is smaller than the SD of individual paired runs.
- What does 30/30 safe attack outcomes prove? Only containment on those fixtures. Many outputs were rejected, so it is not 30/30 useful or immune behaviour. A legal but poor allocation or repeated holds can still be induced.
- How would you improve the model? Test a larger model or constrained decoding, add a true no-op if the assignment allowed it, broaden attacks and seed counts, and rerun the full frozen evaluation. Do not claim untested improvements worked.
- What is the most important limitation? This is one tiny quantised model with a deliberately strict interface; it says little about all LLMs. The student has to articulate their own judgement after reviewing results.

## Independently verify before signing

Run the tests and several hidden seeds, inspect at least one successful state transition and rejected response, understand every score term, and check that the report tables match CSVs. Record only checks you actually perform in your declaration.
