# Iskrov Agent

> Cloud reasoning. Local execution.

Iskrov Agent is an independent cloud-controlled, local-execution Agent product. It keeps model reasoning, planning, approval, evidence, budgets, and scheduling in the control plane, while reducing the local side to a lightweight, closed, authorized tool executor.

**Use this repository if you need a runnable Agent product rather than a protocol specification.** Iskrov Agent owns the executor, providers, approvals, workspace, Bridge, and recovery logic; PRP is a separate project.

```text
Cloud: models · planning · approval · evidence · scheduling
Local: bounded tools · workspace operations · result submission
```

Current release: `0.0.2` · Python `3.12+` · AGPL-3.0-only · single-instance SQLite · no Docker

## Product Position

Iskrov Agent is not a chat UI and does not require every machine to download a full Agent CLI. It is for engineering tasks where a model needs to inspect code, propose changes, run bounded verification, and leave an auditable, recoverable record.

The cloud control plane decides what should happen and whether it is allowed. The local execution plane performs only authorized operations inside the granted workspace and submits the result. The two planes connect through bounded tool calls, claims, leases, and idempotent result submission.

## The Problem

A model API solves:

```text
send a message -> receive an answer
```

An engineering Agent also needs to answer:

- Was this operation allowed?
- What evidence proves completion?
- Who approved the write?
- Should a failure be retried, cascaded, revised, or stopped?
- Can the process recover safely after a server or client restart?

Iskrov Agent is built for that complete execution chain, not just text generation.

## Architecture

### Cloud Control Plane

- Accepts tasks and selects an execution strategy
- Calls configured model providers
- Coordinates Planner, Worker, Analyzer, and Verifier roles
- Owns budgets, approvals, events, recovery, and final state
- Dispatches local tool calls through a Native Bridge when needed

### Local Execution Plane

- Does not run a model
- Does not own cloud planning or approval authority
- Executes only registered, bounded local tools
- Does not require a full Agent CLI download
- Supports claim recovery and idempotent result submission after disconnects

## Tool Boundary

The Agent can use only registered tools:

`list_files` · `read_file` · `search_text` · `apply_patch` · `run_targeted_test` · `get_diff` · `get_status`

Writes pass through Policy and Approval. Tests use pre-registered structured commands. A model cannot obtain an arbitrary shell, arbitrary host paths, unregistered network access, or self-granted permissions.

## Execution Strategies

| Strategy | Use it for | Behavior |
|---|---|---|
| `DIRECT` | Simple tasks | One WorkUnit, one Attempt, one verification |
| `CASCADE` | Model fallback | Move to the next profile only after a retryable failure |
| `PLANNED` | Dependency graphs | Planner proposes a DAG; Workers execute dependencies |
| `PROGRESSIVE` | Evidence and revision | Execute, merge, verify, reuse, and revise within limits |

`PROGRESSIVE` is one execution strategy supported by Iskrov Agent. It is not the product name or the sole theoretical identity of this repository. The independent protocol research lives in [Progressive Reasoning Protocol](https://github.com/entzauberung/prp).

## Security and Isolation

- The default local path boundary is `HOST`, not an operating-system sandbox
- Selecting `SANDBOXED` requires real Linux `bubblewrap`
- Sequential `LOCAL + HOST + DIRECT` can operate in place inside an authorized workspace
- Parallel work, `PLANNED`, and `PROGRESSIVE` use isolated Slots and ChangeSets
- The process envelope limits concurrency, attempts, tokens, slots, and copy capacity
- Resource exhaustion returns a structured error and never silently changes location, strategy, or isolation

## Quick Start

Install:

```bash
uv pip install .
```

Configure an OpenAI-compatible Worker profile:

```bash
export PRP_WORKER_PROFILE='{"alias":"worker","provider":"openai_compatible","model":"your-model","role":"WORKER","base_url":"https://models.example/v1","context_window_tokens":32000,"max_output_tokens":4000}'
```

Run a local in-process task:

```bash
prp local run "summarise this repository" --workspace .
```

Local execution does not depend on an HTTP server. If another program needs the interface, start the loopback-bound service explicitly:

```bash
prp serve
```

When a task pauses for approval:

```bash
prp local approve <request_id> --workspace .
prp local deny <request_id> --workspace . --reason "not allowed"
```

The current distribution still exposes the `prp` and `prp-bridge` command names for runtime compatibility; the product and package identity are `iskrov-agent`.

## Boundaries

Iskrov Agent is a single-instance reference product and does not promise a production SLA. It currently does not provide multi-tenant billing, SSO, distributed queues, Kubernetes, or complete Codex, Claude Code, MCP, or A2A compatibility.

It is not an arbitrary shell or a model-training platform. Model quality depends on the configured provider; the Agent places the execution process inside explicit tool, policy, evidence, and budget boundaries.

## Relationship to PRP

These are two independent products:

- **PRP** is an Apache-2.0 protocol research project defining facts, state machines, and revision laws for progressive reasoning.
- **Iskrov Agent** is an AGPL-3.0-only Agent product using those concepts for cloud control and local tool execution.

PRP can be implemented by other runtimes, and Iskrov Agent is not the only possible implementation of PRP. The two projects can evolve, release, and accept contributions independently.

Installing Iskrov Agent does not install the PRP research repository; studying or implementing PRP does not require Iskrov Agent's cloud-local runtime.

## Open Source and License

Iskrov Agent is licensed under the [GNU Affero General Public License v3.0-only](LICENSE). Network deployment of a modified version carries the corresponding source-availability obligations under AGPL-3.0-only. See [NOTICE](NOTICE) and [TRADEMARKS.md](TRADEMARKS.md).
