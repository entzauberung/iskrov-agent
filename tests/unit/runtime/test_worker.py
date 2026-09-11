"""Targeted resume tests: remote wait, unknown writes, no auto-reassignment."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio

from prp_runtime.domain.enums import (
    AttemptStatus,
    ExecutionLocation,
    ModelRole,
    ToolCallStatus,
    ToolEffect,
)
from prp_runtime.domain.models import (
    AgentHistoryRecord,
    AgentRequestOptions,
    AgentToolCall,
    AgentTurn,
    ExecutionScope,
    WorkspaceGrant,
)
from prp_runtime.domain.values import new_principal_id, new_session_id
from prp_runtime.providers.base import ModelProfile, ProviderRequest, ProviderResponse
from prp_runtime.runtime.agent_executor import AgentToolExecutor
from prp_runtime.runtime.worker import ResumeAction, Worker
from prp_runtime.storage.sqlite import SqliteStore
from prp_runtime.tools.models import ToolCall
from tests.unit.storage.test_store import (
    T0,
    make_attempt,
    make_manifest,
    make_run,
    make_snapshot,
    make_work_unit,
    make_workspace,
)

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "worker-resume.db"


@pytest_asyncio.fixture
async def store(database_path: Path) -> AsyncIterator[SqliteStore]:
    async with SqliteStore(database_path) as opened:
        yield opened


class _UnusedAdapter:
    @property
    def name(self) -> str:
        return "unused"

    async def aclose(self) -> None:
        return None

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        del request
        raise AssertionError("remote wait must not call the provider or reassign")


def _profile() -> ModelProfile:
    return ModelProfile(
        alias="worker",
        provider="fake",
        model="worker-model",
        role=ModelRole.WORKER,
        base_url="https://models.invalid/v1",
        supports_structured_output=True,
        context_window_tokens=8_000,
        max_output_tokens=1_000,
    )


async def _seed_running_bridge_call(store: SqliteStore, *, status: ToolCallStatus = ToolCallStatus.RUNNING):
    principal_id = new_principal_id()
    run = make_run()
    await store.create_run(run)
    unit = make_work_unit(run.run_id)
    await store.create_work_unit(unit)
    workspace = make_workspace(owner_id=principal_id)
    await store.create_workspace(workspace)
    snapshot = make_snapshot(workspace.workspace_id)
    await store.create_snapshot(snapshot, make_manifest(), owner_id=principal_id)
    attempt = make_attempt(
        run.run_id,
        unit.work_unit_id,
        status=AttemptStatus.SUCCEEDED,
        started_at=T0,
        completed_at=T0,
    )
    await store.create_attempt(attempt)
    public = AgentToolCall(
        call_id="provider-call/1",
        tool_name="apply_patch",
        arguments={"path": "src/main.py"},
    )
    internal_id = AgentToolExecutor._internal_call_id(
        run_id=run.run_id,
        work_unit_id=unit.work_unit_id,
        snapshot_id=snapshot.snapshot_id,
        provider_call_id=public.call_id,
        tool_name=public.tool_name,
    )
    persisted = ToolCall(
        call_id=internal_id,
        run_id=run.run_id,
        work_unit_id=unit.work_unit_id,
        tool_name="apply_patch",
        effect=ToolEffect.WRITE,
        arguments={"path": "src/main.py"},
        snapshot_id=snapshot.snapshot_id,
        requested_at=T0,
    )
    await store.create_tool_call(
        persisted, workspace_id=workspace.workspace_id, idempotency_key=internal_id
    )
    await store.start_tool_call(internal_id, started_at=T0)
    if status is ToolCallStatus.UNKNOWN:
        await store.mark_tool_call_unknown(internal_id, completed_at=NOW)
    await store.append_agent_history(
        AgentHistoryRecord(
            run_id=run.run_id,
            work_unit_id=unit.work_unit_id,
            attempt_id=attempt.attempt_id,
            sequence=1,
            idempotency_key=f"{attempt.attempt_id}:1",
            item=AgentTurn(tool_calls=(public,)),
            created_at=T0,
        )
    )
    scope = ExecutionScope(
        run_id=run.run_id,
        session_id=new_session_id(),
        principal_id=principal_id,
        workspace_id=workspace.workspace_id,
        grant=WorkspaceGrant(
            principal_id=principal_id,
            workspace_id=workspace.workspace_id,
        ),
        agent_options=AgentRequestOptions(execution_location=ExecutionLocation.BRIDGE),
    )
    return attempt, public, internal_id, scope


@pytest.mark.asyncio
async def test_running_bridge_write_resumes_as_wait_remote_without_reassignment(
    store: SqliteStore,
) -> None:
    attempt, public, internal_id, scope = await _seed_running_bridge_call(store)
    worker = Worker(store, _UnusedAdapter(), _profile(), execution_scope=scope)
    waiting = await worker.load_resume_state(attempt.attempt_id)
    assert waiting.action is ResumeAction.WAIT_REMOTE
    assert waiting.approval_request is None
    assert waiting.pending_call is not None
    assert waiting.pending_call.call_id == internal_id
    assert waiting.pending_call.status is ToolCallStatus.RUNNING
    assert waiting.pending_public_call == public

    result = await worker.resume(
        run=await store.get_run(attempt.run_id),
        work_unit=await store.get_work_unit(attempt.work_unit_id),
        context=None,  # type: ignore[arg-type]
        state=waiting,
    )
    assert result.paused is True
    assert result.awaiting_remote_result is True
    assert result.pending_call_ids == (public.call_id,)
    assert (await store.list_tool_calls_for_attempt(attempt.attempt_id))[0].call_id == internal_id


@pytest.mark.asyncio
async def test_unknown_bridge_write_blocks_resume_and_does_not_rerun(
    store: SqliteStore,
) -> None:
    attempt, _, _, scope = await _seed_running_bridge_call(
        store, status=ToolCallStatus.UNKNOWN
    )
    worker = Worker(store, _UnusedAdapter(), _profile(), execution_scope=scope)
    blocked = await worker.load_resume_state(attempt.attempt_id)
    assert blocked.action is ResumeAction.BLOCK
    assert blocked.reason == "tool_outcome_unknown"
    with pytest.raises(ValueError, match="tool_outcome_unknown"):
        await worker.resume(
            run=await store.get_run(attempt.run_id),
            work_unit=await store.get_work_unit(attempt.work_unit_id),
            context=None,  # type: ignore[arg-type]
            state=blocked,
        )
