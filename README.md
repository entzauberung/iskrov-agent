# Iskrov Agent

> 云端控制，本地执行。

Iskrov Agent is a single-instance Agent runtime for tasks that need model planning, controlled tool execution, approvals, evidence, budgets, and recovery. The cloud control plane decides what may happen; a registered local Bridge performs only the bounded operation it is authorized to perform.

If you need the protocol research kernel itself, use [Progressive Reasoning Protocol](https://github.com/entzauberung/prp). If you need a runnable Agent service, use this repository.

```text
 iPad / Web / CLI / compatible API client
                    |
              Native Agent API
                    |
 cloud control: model · plan · policy · approval · evidence · budget
                    |
       CLOUD execution or Bridge claim/lease
                    |
       registered tools in an authorized workspace
```

Current release identity: `0.0.2` · Python `3.12+` · AGPL-3.0-only · SQLite reference deployment.

Detailed contracts:

- [Architecture](docs/architecture.md)
- [PRP integration](docs/prp-integration.md)
- [Release preparation](RELEASE.md)
- [Changelog](CHANGELOG.md)

## What it provides

- A durable controller for `DIRECT`, `CASCADE`, `PLANNED`, and `PROGRESSIVE` strategies.
- Provider adapters for OpenAI-compatible, OpenAI Responses, and Anthropic Messages endpoints.
- Native sessions, runs, events, tool calls, approvals, cancellation, and recovery.
- A restricted tool registry for file listing, reading, search, patching, diff, status, and targeted tests.
- Owner-scoped workspaces, snapshots, changesets, merge records, budgets, and evidence.
- A model-free Bridge client with claims, leases, heartbeats, bounded local execution, and idempotent result submission.
- OpenAI Chat/Responses and Anthropic Messages compatibility routes mapped to the same native runtime.

## Boundaries

The model cannot obtain arbitrary shell access, arbitrary host paths, unregistered network access, or permission escalation. Write operations pass through policy and approval. `HOST` is a path boundary, not an operating-system sandbox; `SANDBOXED` requires a real Linux `bubblewrap` installation.

An iPad or web client is a control surface. It creates runs, watches events, reviews evidence, approves or denies writes, and cancels work. It does not receive provider credentials or become the local execution environment.

PRP supplies the semantics for evidence-gated Progressive revision. Iskrov owns the provider, scheduling, storage, workspace, Bridge, approval, and recovery extensions. The two projects can be released independently.

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

Configure a Worker profile through the documented `PRP_WORKER_PROFILE` setting. The example below uses an OpenAI-compatible endpoint; replace the placeholder values with your own deployment configuration.

```bash
export PRP_WORKER_PROFILE='{"alias":"worker","provider":"openai_compatible","model":"your-model","role":"WORKER","base_url":"https://models.example/v1","context_window_tokens":32000,"max_output_tokens":4000}'
```

Do not commit provider credentials or local configuration files. The settings layer keeps secrets out of public facts and serialized domain models.

## Run locally

The local path does not require an HTTP server:

```bash
prp local run "summarise this repository" --workspace .
```

To expose the ASGI service, bind it explicitly. The default host is loopback:

```bash
prp serve
```

Approval commands for a paused local run:

```bash
prp local approve <request_id> --workspace .
prp local deny <request_id> --workspace . --reason "not allowed"
```

The installed command names `prp` and `prp-bridge` are retained for compatibility; the package and product identity are `iskrov-agent` and Iskrov Agent.

## API surfaces

The Native Agent API is the product contract for sessions, runs, events, tool calls, approvals, Bridge clients, and cancellation. Compatibility routes accept a deliberately bounded subset of OpenAI Chat/Responses and Anthropic Messages payloads and translate them into the same controller.

The service exposes health and readiness checks at `/health` and `/ready`. See the API modules under `src/prp_runtime/api/` for the exact request and response contracts.

## Scope and status

This is a single-instance reference product. It does not provide multi-tenant billing, SSO, distributed queues, Kubernetes deployment, or a production SLA. It does not claim full compatibility with Codex, Claude Code, MCP, or A2A, and it does not make benchmark or model-quality claims.

## License

Iskrov Agent is licensed under [AGPL-3.0-only](LICENSE). Network deployment of modified versions must comply with the corresponding-source obligations of the license. See [NOTICE](NOTICE) and [TRADEMARKS.md](TRADEMARKS.md).
