# Iskrov Agent

> Cloud control, local execution.

Iskrov Agent is a single-instance Agent runtime. Model planning, policy, approvals, budgets, evidence, scheduling, and recovery live in the control plane; the local machine exposes only registered, bounded, authorized tools.

Use [Progressive Reasoning Protocol](https://github.com/entzauberung/prp) when you need the protocol research kernel. Use this repository when you need a runnable Agent service that connects models, workspaces, and local devices.

```text
iPad / Web / CLI / compatible API
              |
        Native Agent API
              |
cloud: model · plan · policy · approval · evidence · budget · scheduler
              |
      CLOUD execution or Bridge claim/lease
              |
      registered tools in an authorized workspace
```

Current release: `0.0.2` · Python `3.12+` · AGPL-3.0-only · SQLite single-instance reference deployment.

## Product model

An iPad or other client is a remote control surface. It creates runs, watches events, inspects evidence, handles approvals, and cancels work. It does not run the full Agent, receive provider credentials, or receive arbitrary host paths.

When a local workspace is needed, the server selects a registered Bridge for a concrete tool call. The Bridge claims the call, performs only the bounded operation, and submits an idempotent result.

## Capabilities

- `DIRECT`, `CASCADE`, `PLANNED`, and `PROGRESSIVE` execution strategies.
- OpenAI-compatible, OpenAI Responses, and Anthropic Messages provider adapters.
- Native sessions, runs, events, tool calls, approvals, cancellation, and recovery.
- Registered tools for files, search, patches, diffs, status, and targeted tests.
- Owner-scoped workspaces, snapshots, changesets, merges, budgets, and evidence.
- A model-free Bridge with claims, leases, heartbeats, offline recovery, and idempotent submission.
- Bounded OpenAI Chat/Responses and Anthropic Messages compatibility routes.

## Control and execution planes

The cloud controller selects the model, strategy, execution location, and approval path; coordinates Planner, Worker, Analyzer, and Verifier; and owns durable facts. The local plane does not plan or approve. It executes registered tools inside an authorized workspace and returns bounded results.

The model cannot obtain arbitrary shell access, arbitrary host paths, unregistered network access, or privilege escalation. Writes pass through policy and approval. `HOST` is a path boundary, not an OS sandbox; `SANDBOXED` requires real Linux `bubblewrap`.

## Relationship to PRP

PRP defines evidence-gated Progressive revision: whether the next execution-graph version is allowed. Iskrov implements that semantic and adds provider, scheduling, approval, SQLite, workspace, merge, Bridge, and recovery systems. The two projects can be released independently.

## Install

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
mypy
```

Python 3.12 or newer is required.

## Configure a provider

The example below configures an OpenAI-compatible Worker profile. Replace the placeholders with your own deployment values and never commit credentials or local configuration files.

```bash
export PRP_WORKER_PROFILE='{"alias":"worker","provider":"openai_compatible","model":"your-model","role":"WORKER","base_url":"https://models.example/v1","context_window_tokens":32000,"max_output_tokens":4000}'
```

## Run locally

```bash
prp local run "summarise this repository" --workspace .
prp serve
```

For an approval-paused local run:

```bash
prp local approve <request_id> --workspace .
prp local deny <request_id> --workspace . --reason "not allowed"
```

The installed `prp` and `prp-bridge` command names are retained for compatibility; the package identity is `iskrov-agent`.

## API

The Native Agent API is the product contract for sessions, runs, events, tool calls, approvals, Bridge clients, and cancellation. OpenAI Chat/Responses and Anthropic Messages routes accept bounded compatibility subsets and map them to the same controller. Health and readiness are exposed at `/health` and `/ready`.

See [README.md](README.md) for the Chinese project description and [docs/architecture.md](docs/architecture.md) for the detailed architecture.

## Status and limits

Version `0.0.2` is a single-instance reference product. It does not claim full Codex, Claude Code, MCP, or A2A compatibility, benchmark superiority, model-quality superiority, distributed queues, SSO, billing, Kubernetes deployment, or a production SLA.

## License

Iskrov Agent is licensed under [AGPL-3.0-only](LICENSE). Network deployment of modified versions must comply with the corresponding-source obligations. See [NOTICE](NOTICE) and [TRADEMARKS.md](TRADEMARKS.md).
