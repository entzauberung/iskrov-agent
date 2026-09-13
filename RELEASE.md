# Release Preparation

## 0.1.0 (2026-09-12)

- Added the architecture and PRP integration contracts.
- Added `iskrov` and `iskrov-bridge` as the official CLI entry points while retaining the historical `prp` aliases.
- Clarified the Native Agent API, Bridge, device, and control-plane boundaries.
- Refreshed the product documentation and release metadata.

## Identity

- Product: Iskrov Agent
- Package: `iskrov-agent`
- Version: `0.1.0`
- License: AGPL-3.0-only
- Distribution status: prepared locally; not published

## Scope

This release is a single-instance reference Agent runtime. It includes the
cloud controller, provider adapters, policy and approval flow, SQLite
persistence, workspace and merge handling, restricted tools, Bridge client,
local CLI, recovery, and compatibility API bindings.

The Progressive Reasoning Protocol is a separate Apache-2.0 project. Iskrov
implements its Progressive semantics and adds product-specific runtime facts.

## Pre-publish gate

- [ ] Review the complete diff and remove local-only changes.
- [ ] Run unit, integration, conformance, and package identity tests.
- [ ] Run `ruff check .` and `mypy`.
- [ ] Build sdist and wheel in a clean environment.
- [ ] Inspect archive contents for credentials, databases, caches, and local configuration.
- [ ] Confirm the version, license, repository URLs, README, NOTICE, and changelog agree.
- [ ] Obtain explicit approval before any push or package publication.

No publish, push, or package mutation is performed by this preparation.
