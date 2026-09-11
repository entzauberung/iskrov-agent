# Release Preparation

## Identity

- Product: Iskrov Agent
- Package: `iskrov-agent`
- Current implementation version: `0.0.1`
- Distribution status: prepared locally, not published

## Scope

This repository contains the complete Iskrov Agent cloud-local implementation,
including its server controller, provider adapters, persistence, policies,
workspace handling, bridge client, and local CLI.

The Progressive Reasoning Protocol is a separate research repository at
`/home/ognev/prp`.

## Pre-publish gate

- [ ] Review the complete diff and remove local-only changes intentionally
- [ ] Run unit, integration, and conformance tests
- [ ] Run `ruff check .` and `mypy`
- [ ] Build sdist and wheel in a clean environment
- [ ] Inspect archive contents for credentials, databases, caches, and local config
- [ ] Set the final public repository URL in `pyproject.toml`
- [ ] Add a versioned changelog entry
- [ ] Obtain explicit approval before any push or package publication

No publish or push is performed by this preparation.
