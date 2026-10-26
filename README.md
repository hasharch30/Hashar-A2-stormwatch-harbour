# Stormwatch Harbour

CGD-460 Assignment 2 - Hashar Qaisar Chaudhary, Student ID **233062**.

ID digit **2**: **14 dockworkers**, ship arrival interval **6-10 ticks**, **4 storms**, and **9 cargo units per ship**. Each run lasts **600 ticks** on a **24 x 16** grid.

## Run

Python 3.10 or newer (tested on 3.12):

```sh
python -m pip install -r requirements.txt
python run.py --agent utility --seed 11
```

Agents: `baseline`, `reflex`, `model`, `utility`, `llm`. Every single-run command prints one JSON line. The non-LLM policies use the standard library and are deterministic for a fixed seed.

```sh
python run.py --agent llm --seed 11 --replay logs/llm_log.jsonl
python run.py --reproduce
python -m unittest discover -s tests -v
python -m src.verify
```

`--reproduce` regenerates development runs (seeds 1-10), the four-policy evaluation (seeds 11-40), paired comparisons, the routing intervention (seeds 11-20), figures, and the LLM/security experiments from saved responses. Replay requires no model server or API key. Saved LLM simulation responses cover seeds 11-15. The report and AI Usage Declaration are submitted separately; this command does not create documents.

## Simulation and measures

North is row 0. Berth apron cells: B1=(3,0), B2=(9,0), B3=(15,0), B4=(21,0). Warehouse=(0,15). Ships moor immediately north of each apron at (x,-1), adjacent to workers on the apron. B1/B4 apron cells are unsafe at storm onset.

One seeded RNG pre-generates environmental events, so paired policies receive identical ship and storm schedules. Every worker moves one cell or performs one action per tick. Worker order rotates. Entry into a cell containing three workers is blocked. A Lookout warning occurs five ticks before the 15-tick storm; model/utility workers remember it. Storm-onset knock-outs last 20 ticks and lose carried cargo.

`cargo_delivered` counts warehouse drops. `avg_ship_wait` measures arrival-to-docking delay across all arrivals, censoring undocked ships at tick 600. `crowding_violations` counts cell-ticks with more than three workers. `storm_knockouts` counts worker knock-out events. The LLM output additionally includes invalid outputs, retries, fallback turns, calls and original measured mean wall time per call.

Utility uses `0.8*cargo - 1.2*distance - 0.8*assigned_workers - 0.4*local_crowding - 100*storm_risk + 3*same_target`. Known unsafe berths are excluded. It was selected on development seeds using deliveries minus 20 per knock-out. It is also the fallback after three failed LLM attempts.

## LLM and safeguards

Original experiments: **Qwen2.5-0.5B-Instruct Q4_K_M**, revision `9217f5db79a29953eb74d5343926648285ec7e67`; **llama.cpp b11669**, CPU with four threads, context 4096; temperature **0.2**, output limit **150 tokens**, fixed decoding seeds; **26 October 2026**. No fine-tuning. Model SHA256: `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.

For new live runs, obtain the official model from [Qwen](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF) and runtime from [llama.cpp b11669](https://github.com/ggml-org/llama.cpp/releases/tag/b11669), then start:

```sh
llama-server -m qwen2.5-0.5b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8765 -c 4096 -t 4 --parallel 1 --alias Qwen2.5-0.5B-Instruct-Q4_K_M
python run.py --agent llm --seed 917
```

The client reads `HARBOUR_LLM_URL` (default localhost:8765/v1/chat/completions) and optional `HARBOUR_API_KEY` from environment variables. Never commit secrets. Archive existing logs before fresh full live experiments (`python run.py --reproduce --live`, then `python -m src.security`). Update the model metadata if changing providers. Recorded HTTP wall time can include request queueing.

Every 20 ticks, the model receives only a text report. AST parsing never evaluates model code. Validation checks action names, arguments, ship/berth existence, allocation limits and storm safety. A Final Report must quote a current fact or correctly identify an absent ship. Input notes are marked as untrusted data. `close_harbour()` and `release_cargo(ship_id)` require a separate human approval callback and default to blocked. `--human-approval` prompts for `APPROVE` for each exact order; text inside a report cannot approve it. A release removes a cargo hold and does not create or deliver cargo.

## Evidence and prompt history

- `src/`: simulation, policies, report builder, parser, validator, executor, replay and experiment scripts.
- `results/`: 120 policy/seed rows, paired statistics, routing intervention, figures, five LLM comparisons, 60 injection trials, ten prompt trials, three hallucination probes and a ten-statement audit.
- `logs/`: all 449 original simulation calls and 73 security/prompt/probe calls, including complete prompts, raw responses, tick and model metadata.
- `tests/`: deterministic hidden-seed checks, cargo conservation, capacity, storms, parser/argument validation, approval and fallback tests.

Prompt change log: v0 used a generic helpful master and three-line output. v1 added a five-part template and examples; development exposed copied example facts, lowercase labels and an invalid empty-berth example. v2 removed the invalid example, prohibited copying example facts, added instruction hierarchy and exact fact checks, and retained independent permissions, approval and retry feedback. The final template and two worked examples are in `src/master.py`. Raw failures remain in the logs.

Developed with substantial AI assistance, documented in the separately submitted AI Usage Declaration. The student must review the implementation and complete their own verification and signature before submission.
