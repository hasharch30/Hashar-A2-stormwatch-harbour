# Stormwatch Harbour

CGD-460 Assignment 2. Student: **Hashar Qaisar Chaudhary, 233062**.
Last ID digit **2**: **14 workers**, arrival interval **6-10 ticks**, **4 storms**, **9 units per ship**. Runs last 600 ticks on a 24 x 16 grid.

## Run

Python 3.10+ (tested with 3.12). From this folder:

```sh
python -m pip install -r requirements.txt
python run.py --agent utility --seed 11
```

The single-run command prints exactly one JSON line with `cargo_delivered`, `avg_ship_wait`, `crowding_violations`, and `storm_knockouts`. The baseline, reflex, model and utility policies use only the standard library. The four non-LLM policies reproduce exactly on any integer seed. `--digit` supports other rows for inspection; the submitted results use 2.

```sh
python run.py --agent baseline --seed 11
python run.py --agent reflex --seed 11
python run.py --agent model --seed 11
python run.py --agent utility --seed 917
python run.py --agent llm --seed 11 --replay logs/llm_log.jsonl
```

The LLM JSON additionally reports invalid outputs, retries, fallback turns, calls and mean original wall seconds per call. **Replay makes no model calls**, and preserves original measured timing. It checks the full system/user prompt hash at each tick and attempt and fails rather than silently accepting different state. Replay is available for evaluation seeds 11-15 only; unseen LLM seeds require a live server.

## Reproduce the complete report and experiments

```sh
python run.py --reproduce
```

This single command regenerates all 120 rule-policy runs (seeds 11-40), development runs (1-10), paired comparisons, the ten-seed routing intervention, figures, five LLM runs from saved responses, 73 security/prompt/probe responses from saved text, the ten-statement audit, the report and declaration. No account, model download or API key is required for replay. PDF creation requires the optional report libraries listed in requirements; the ordinary simulation does not.

```sh
python -m unittest discover -s tests -v
```

Tests cover deterministic unseen seeds, conservation of picked cargo, all-tick capacity, storms, parser/argument guards, default-deny and explicitly approved paths, retry limits and utility fallback. `tests/` uses generated scratch files only in its own `work/` folder.

## World conventions

North is row 0. Berth aprons: B1=(3,0), B2=(9,0), B3=(15,0), B4=(21,0). The warehouse is (0,15). A ship is moored offshore immediately north of its apron, at (x,-1); the apron worker is adjacent to the ship. The apron is the unsafe berth cell at storm onset. Four-neighbour movement never leaves the 24 x 16 worker grid.

Every tick: arrivals, FIFO docking, 20-tick public berth bulletin, Lookout warning or storm onset, optional Master turn, one action per worker with rotating priority, empty-ship departure, metrics. Picks and drops each consume a tick. Workers knocked out at onset lose carried cargo and cannot act for 20 ticks. New entrants during the storm are not knocked out: the brief specifies onset only. Remembering workers nevertheless avoid unsafe aprons throughout the warning/storm window. The single seeded RNG generates all arrival and storm events before policies act, ensuring paired schedules.

The Lookout sends a one-tick warning five ticks before onset. Reflex workers see only the current warning; remembering policies retain it until the storm ends. A public Quartermaster bulletin reports berth cargo every 20 ticks, supplemented by local observations within Manhattan distance four. Reflex uses a current occupied-berth signal without memory. Model stores target and warning state; utility scores cargo, distance, assigned workers, local crowding, risk and a target-retention bonus. No policy learns during evaluation.

`avg_ship_wait` is the mean arrival-to-docking queue wait across all arrivals, with still-undocked ships right-censored at 600. This is a restricted mean, not eventual total wait. `crowding_violations` counts cell-ticks with >3 workers, including after every worker has acted; entry capacity is enforced on each move as well. `storm_knockouts` counts worker-onset events, including repeated events for the same worker. Delivered cargo counts only warehouse drops; neither carried nor lost cargo receives credit.

## Local LLM setup for new live runs

The evidence uses Qwen2.5-0.5B-Instruct Q4_K_M, official weights revision `9217f5db79a29953eb74d5343926648285ec7e67`, SHA256 `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`. Runtime: llama.cpp **b11669**, CPU, four inference threads, context 4096, one server slot; temperature **0.2**, maximum **150** output tokens, fixed request decoding seed. Date of original use: **26 October 2026**. No fine-tuning. Weights/runtime are deliberately excluded from Git.

Download official binaries and model from:

- https://github.com/ggml-org/llama.cpp/releases/tag/b11669
- https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67

```sh
llama-server -m qwen2.5-0.5b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8765 -c 4096 -t 4 --parallel 1 --alias Qwen2.5-0.5B-Instruct-Q4_K_M
python run.py --agent llm --seed 917
```

For a hosted OpenAI-compatible endpoint, set `HARBOUR_LLM_URL` and optionally `HARBOUR_API_KEY` as environment variables. The submitted model identity is fixed in `src/master.py`; update it and rerun/report new experiments if switching models. Never put keys in source or logs. The bundled client uses standard-library HTTP; no provider library is needed.

Before a fresh full live evaluation, **move the existing logs to a backup folder**. Then `python run.py --reproduce --live` and `python -m src.security` collect new original evidence. Existing logs are never silently overwritten. Independent server requests may queue, so the recorded HTTP wall time includes any queueing rather than only generation time.

## Safety and actions

The model sees a text report, never simulation objects. Its output is parsed into literal calls without eval, validated against state and permissions, and executed only on acceptance. Unknown/unsafe/impossible arguments are rejected. At most three actions are allowed per turn. After two retries (three attempts total), worker control reverts to the utility policy chosen on development seeds using deliveries minus 20 per storm knock-out. The LLM is not credited for fallback work.

Supported actions: assign workers, hold a ship for 20 ticks, broadcast a supported storm warning, close the harbour to new docking, and release a ship's cargo hold. Release removes an administrative hold and never creates or delivers cargo. No-op is absent from the specified allowlist, so an empty initial state may legitimately require fallback rather than an invented order.

`close_harbour()` and `release_cargo(ship_id)` always default to blocked. To authorise an exact live order, a person must use `--human-approval` and type `APPROVE` at that order's prompt. A manifest or model response cannot grant approval. Evaluation never enables approval. The approved branch is exercised by a test callback only.

Player-facing Final Reports must quote a current FACTS line exactly, or state an actually absent ship ID. Raw Thought summaries remain diagnostic log data. This guards published facts but does not prove the raw generator never hallucinates. Input text is JSON-escaped and marked untrusted; the hierarchy is a prompt defence, independent code permissions and the approval gate are enforcement. Before-defence injection trials score proposals only and execute nothing.

## Files and evidence

- `run.py`, `src/simulation.py`: CLI, world, policies and event order.
- `src/master.py`: report builder, prompts, parser, grounding, validator, approval executor, feedback and replay.
- `src/evaluate.py`, `src/security.py`: paired evaluation, routing intervention, attack/prompt/probe experiments and audit.
- `src/report.py`: source for the ten-page report and one-page declaration.
- `results/evaluation_30_seeds.csv`: all 120 policy/seed rows; `summary.csv`, `paired_comparisons.csv` and two figures.
- `results/emergence_10_seeds.csv`: fixed versus spread routes on seeds 11-20; two seed-11 traces.
- `results/llm_comparison.csv`: five paired LLM/utility seeds with failure/call/timing metrics.
- `results/injection_tests.csv`: all ten inputs, expected behaviour and before/after outcomes for three runs each.
- `results/prompt_comparison.csv`, `hallucination_probes.csv`, `hallucination_audit.csv`: prompt and grounding evidence.
- `logs/llm_log.jsonl`, `logs/security_log.jsonl`: complete original prompts and raw outputs.
- `VIVA_GUIDE.md`, `PROMPT_CHANGELOG.md`: explanation and prompt history.

## Submission and authorship

The included declaration accurately discloses substantial AI assistance. The student must independently review the code/results, complete the personal verification field and sign the declaration. The assistant has not signed for the student or claimed independent student work. See `SUBMISSION_CHECKLIST.md` for the remaining portal and instructor-access steps.
