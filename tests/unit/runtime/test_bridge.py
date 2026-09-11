"""Durable Bridge assignment coordinator tests. No live network."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from prp_runtime.domain.enums import BridgeClientLiveness, ToolEffect
from prp_runtime.domain.errors import StateError
from prp_runtime.domain.events import EventType
from prp_runtime.domain.models import (
    BridgeClientStatus,
    ClientCapabilityDescriptor,
    RegisteredBridgeClient,
    fingerprint_client_capabilities,
    new_client_id,
)
from prp_runtime.domain.values import new_run_id, new_snapshot_id, new_tool_call_id, new_work_unit_id
from prp_runtime.runtime.bridge import BridgeAssignmentCoordinator
from prp_runtime.storage.sqlite import DuplicateEntityError
from prp_runtime.tools.models import BridgeClaim, ToolCall
from prp_runtime.workspace.models import Snapshot, SnapshotStatus

NOW = datetime(2026, 9, 2, 18, 0, tzinfo=UTC)


class FakeLiveness:
    def __init__(self, live: set[str] | None = None) -> None:
        self.live = set(live or ())
        self.wakes: list[str] = []

    def bridge_client_liveness(
        self,
        client_id: str,
        *,
        fingerprint: str | None = None,
        now: object | None = None,
    ) -> BridgeClientLiveness:
        del fingerprint, now
        if client_id in self.live:
            return BridgeClientLiveness.LIVE
        return BridgeClientLiveness.OFFLINE

    async def enqueue(self, run_id: str) -> None:
        self.wakes.append(run_id)


class FakeStore:
    def __init__(
        self,
        clients: tuple[RegisteredBridgeClient, ...] = (),
        *,
        counts: dict[str, int] | None = None,
        claimed: tuple[str, ...] = (),
        snapshots: tuple[Snapshot, ...] = (),
    ) -> None:
        self.clients = clients
        self.counts = counts or {}
        self.claimed = claimed
        self.snapshots = snapshots
        self.list_calls: list[tuple[str, str | None]] = []
        self.events: list[tuple[str, EventType, dict[str, object]]] = []
        self.assignments: list[tuple[str, str, str]] = []
        self.bound_snapshots: dict[str, str] = {}
        self._claimed_ids: set[str] = set(claimed)
        self._claims_by_key: dict[str, BridgeClaim] = {}

    async def list_bridge_clients(
        self, *, principal_id: str, workspace_id: str | None = None
    ) -> tuple[RegisteredBridgeClient, ...]:
        self.list_calls.append((principal_id, workspace_id))
        if workspace_id is None:
            raise AssertionError("coordinator must not union principal-wide clients")
        return tuple(item for item in self.clients if item.workspace_id == workspace_id)

    async def list_active_bridge_claim_counts(
        self, *, principal_id: str, workspace_id: str
    ) -> dict[str, int]:
        del principal_id, workspace_id
        return dict(self.counts)

    async def list_active_bridge_call_ids(
        self, *, principal_id: str, workspace_id: str
    ) -> tuple[str, ...]:
        del principal_id, workspace_id
        return tuple(self._claimed_ids)

    async def get_active_bridge_claim(
        self,
        call_id: str,
        *,
        principal_id: str,
        workspace_id: str,
    ) -> BridgeClaim | None:
        del principal_id, workspace_id
        for claim in self._claims_by_key.values():
            if claim.call_id == call_id:
                return claim
        return None

    async def list_snapshots(self, workspace_id: str, *, owner_id: str) -> tuple[Snapshot, ...]:
        del owner_id
        return tuple(item for item in self.snapshots if item.workspace_id == workspace_id)

    async def bind_bridge_call_snapshot(
        self,
        call_id: str,
        *,
        snapshot_id: str,
        principal_id: str,
    ) -> None:
        del principal_id
        self.bound_snapshots[call_id] = snapshot_id

    async def append_event(
        self,
        run_id: str,
        event_type: EventType,
        payload: dict[str, object] | None = None,
        *,
        timestamp: object | None = None,
    ) -> None:
        del timestamp
        self.events.append((run_id, event_type, dict(payload or {})))

    async def claim_tool_call(
        self,
        session_id: str,
        run_id: str,
        call_id: str,
        *,
        principal_id: str,
        client_id: str,
        idempotency_key: str,
        claimed_at: datetime | None = None,
        expires_at: datetime | None = None,
        fingerprint: str | None = None,
    ) -> BridgeClaim:
        del expires_at, fingerprint
        existing = self._claims_by_key.get(idempotency_key)
        if existing is not None:
            if existing.call_id != call_id or existing.client_id != client_id:
                raise DuplicateEntityError("Idempotency-Key already belongs to a different Bridge claim")
            return existing
        if call_id in self._claimed_ids:
            owned = next(
                (item for item in self._claims_by_key.values() if item.call_id == call_id),
                None,
            )
            if owned is not None and owned.client_id == client_id:
                return owned
            raise DuplicateEntityError("tool call already has an active Bridge claim")
        claimed_at = claimed_at or NOW
        snapshot_id = self.bound_snapshots.get(call_id)
        if snapshot_id is None:
            snapshot_id = self.snapshots[0].snapshot_id if self.snapshots else new_snapshot_id()
        claim = BridgeClaim(
            call_id=call_id,
            run_id=run_id,
            session_id=session_id,
            workspace_id="ws_project",
            snapshot_id=snapshot_id,
            owner_id=principal_id,
            client_id=client_id,
            idempotency_key=idempotency_key,
            fingerprint="a" * 64,
            claimed_at=claimed_at,
            expires_at=claimed_at + timedelta(seconds=30),
        )
        self._claimed_ids.add(call_id)
        self._claims_by_key[idempotency_key] = claim
        self.assignments.append((call_id, client_id, idempotency_key))
        return claim


def _capabilities(*tools: str, effects: tuple[ToolEffect, ...] = (ToolEffect.READ,)) -> ClientCapabilityDescriptor:
    return ClientCapabilityDescriptor(tools=tuple(sorted(tools)), effects=effects)


def _client(
    *,
    workspace_id: str = "ws_project",
    tools: tuple[str, ...] = ("read_file",),
    effects: tuple[ToolEffect, ...] = (ToolEffect.READ,),
    status: BridgeClientStatus = BridgeClientStatus.ACTIVE,
    snapshot_id: str | None = None,
) -> RegisteredBridgeClient:
    capabilities = _capabilities(*tools, effects=effects)
    return RegisteredBridgeClient(
        client_id=new_client_id(),
        principal_id="prn_operator",
        workspace_id=workspace_id,
        capabilities=capabilities,
        capability_fingerprint=fingerprint_client_capabilities(capabilities),
        status=status,
        created_at=NOW,
        disabled_at=NOW if status is BridgeClientStatus.DISABLED else None,
        current_snapshot_id=snapshot_id,
    )


def _snapshot(workspace_id: str = "ws_project") -> Snapshot:
    return Snapshot(
        snapshot_id=new_snapshot_id(),
        workspace_id=workspace_id,
        status=SnapshotStatus.READY,
        created_at=NOW,
        completed_at=NOW,
    )


def _call(*, snapshot_id: str, tool_name: str = "read_file", effect: ToolEffect = ToolEffect.READ) -> ToolCall:
    return ToolCall(
        call_id=new_tool_call_id(),
        run_id=new_run_id(),
        work_unit_id=new_work_unit_id(),
        tool_name=tool_name,
        effect=effect,
        arguments={"path": "README.md"},
        snapshot_id=snapshot_id,
        requested_at=NOW,
    )


@pytest.mark.asyncio
async def test_coordinator_selects_exact_durable_client_without_capability_union() -> None:
    snapshot = _snapshot()
    lister = _client(tools=("list_files",), snapshot_id=snapshot.snapshot_id)
    reader = _client(tools=("read_file",), snapshot_id=snapshot.snapshot_id)
    foreign = _client(workspace_id="ws_other", tools=("read_file",), snapshot_id=snapshot.snapshot_id)
    store = FakeStore(
        (lister, reader, foreign),
        snapshots=(snapshot,),
    )
    coordinator = BridgeAssignmentCoordinator(store, FakeLiveness({lister.client_id, reader.client_id, foreign.client_id}))
    chosen = await coordinator.select_for_call(
        _call(snapshot_id=snapshot.snapshot_id),
        principal_id="prn_operator",
        workspace_id="ws_project",
    )
    assert chosen.selected is not None
    assert chosen.selected.client_id == reader.client_id
    assert chosen.selected.workspace_id == "ws_project"
    assert chosen.selected.snapshot_id == snapshot.snapshot_id
    assert chosen.selected.fingerprint == reader.capability_fingerprint
    assert "list_files" not in chosen.selected.tools
    assert store.list_calls == [("prn_operator", "ws_project")]
    reasons = dict(chosen.skipped)
    assert reasons[lister.client_id] == "tool capability mismatch"
    assert foreign.client_id not in reasons


@pytest.mark.asyncio
async def test_coordinator_skips_offline_disabled_full_and_stale_snapshot() -> None:
    snapshot = _snapshot()
    live_full = _client(snapshot_id=snapshot.snapshot_id)
    disabled = _client(status=BridgeClientStatus.DISABLED)
    offline = _client()
    store = FakeStore(
        (live_full, disabled, offline),
        counts={live_full.client_id: 1},
        snapshots=(snapshot,),
    )
    coordinator = BridgeAssignmentCoordinator(store, FakeLiveness({live_full.client_id, disabled.client_id}))
    skipped = await coordinator.select_for_call(
        _call(snapshot_id=snapshot.snapshot_id),
        principal_id="prn_operator",
        workspace_id="ws_project",
    )
    reasons = dict(skipped.skipped)
    assert skipped.selected is None
    assert reasons[live_full.client_id] == "lease capacity exhausted"
    assert reasons[disabled.client_id] == "client is disabled"
    assert reasons[offline.client_id] == "client is not live"

    unpublished = _client()
    unpublished_store = FakeStore((unpublished,), snapshots=(snapshot,))
    unpublished_choice = await BridgeAssignmentCoordinator(
        unpublished_store, FakeLiveness({unpublished.client_id})
    ).select_for_call(
        _call(snapshot_id=snapshot.snapshot_id),
        principal_id="prn_operator",
        workspace_id="ws_project",
    )
    assert unpublished_choice.selected is not None
    assert unpublished_choice.selected.client_id == unpublished.client_id
    assert unpublished_choice.selected.snapshot_id is None

    first = _snapshot()
    second = _snapshot()
    client_a = _client(snapshot_id=first.snapshot_id)
    client_b = _client(snapshot_id=second.snapshot_id)
    split = await BridgeAssignmentCoordinator(
        FakeStore((client_a, client_b), snapshots=(first, second)),
        FakeLiveness({client_a.client_id, client_b.client_id}),
    ).select_for_call(
        _call(snapshot_id=first.snapshot_id),
        principal_id="prn_operator",
        workspace_id="ws_project",
    )
    assert split.selected is not None
    expected = min(client_a.client_id, client_b.client_id)
    assert split.selected.client_id == expected
    assert split.selected.snapshot_id == (
        first.snapshot_id if expected == client_a.client_id else second.snapshot_id
    )


@pytest.mark.asyncio
async def test_select_uses_store_liveness_over_supervisor_memory() -> None:
    snapshot = _snapshot()
    reader = _client(snapshot_id=snapshot.snapshot_id)

    class DurableStore(FakeStore):
        def bridge_client_liveness(
            self,
            client_id: str,
            *,
            now: datetime,
            principal_id: str | None = None,
            fingerprint: str | None = None,
        ) -> BridgeClientLiveness:
            del client_id, now, principal_id, fingerprint
            return BridgeClientLiveness.EXPIRED

    store = DurableStore((reader,), snapshots=(snapshot,))
    chosen = await BridgeAssignmentCoordinator(
        store, FakeLiveness({reader.client_id})
    ).select_for_call(
        _call(snapshot_id=snapshot.snapshot_id),
        principal_id="prn_operator",
        workspace_id="ws_project",
    )
    assert chosen.selected is None
    assert dict(chosen.skipped)[reader.client_id] == "client is not live"

@pytest.mark.asyncio
async def test_assign_for_call_persists_one_assignment_and_skip_events() -> None:
    snapshot = _snapshot()
    lister = _client(tools=("list_files",), snapshot_id=snapshot.snapshot_id)
    reader = _client(tools=("read_file",), snapshot_id=snapshot.snapshot_id)
    store = FakeStore((lister, reader), snapshots=(snapshot,))
    liveness = FakeLiveness({lister.client_id, reader.client_id})
    coordinator = BridgeAssignmentCoordinator(store, liveness)
    call = _call(snapshot_id=snapshot.snapshot_id)
    assignment = await coordinator.assign_for_call(
        call,
        principal_id="prn_operator",
        workspace_id="ws_project",
        session_id="ses_bridge",
        idempotency_key="assign-1",
        caller_client_id=reader.client_id,
        claimed_at=NOW,
    )
    assert assignment.claim is not None
    assert assignment.claim.client_id == reader.client_id
    assert assignment.claim.call_id == call.call_id
    assert store.assignments == [(call.call_id, reader.client_id, "assign-1")]
    skip_events = [item for item in store.events if item[1] is EventType.BRIDGE_CLIENT_SKIPPED]
    assert skip_events == [
        (
            call.run_id,
            EventType.BRIDGE_CLIENT_SKIPPED,
            {"call_id": call.call_id, "client_id": lister.client_id, "reason": "tool capability mismatch"},
        )
    ]
    replay = await coordinator.assign_for_call(
        call,
        principal_id="prn_operator",
        workspace_id="ws_project",
        session_id="ses_bridge",
        idempotency_key="assign-1",
        caller_client_id=reader.client_id,
        claimed_at=NOW,
    )
    assert replay.claim == assignment.claim
    assert store.events == skip_events
    rebound = await coordinator.assign_for_call(
        call,
        principal_id="prn_operator",
        workspace_id="ws_project",
        session_id="ses_bridge",
        idempotency_key="assign-2",
        caller_client_id=reader.client_id,
        claimed_at=NOW,
    )
    assert rebound.claim == assignment.claim
    with pytest.raises(StateError, match="server-selected"):
        await coordinator.assign_for_call(
            call,
            principal_id="prn_operator",
            workspace_id="ws_project",
            session_id="ses_bridge",
            idempotency_key="assign-other",
            caller_client_id=lister.client_id,
            claimed_at=NOW,
        )
    with pytest.raises(StateError, match="server-selected"):
        await coordinator.assign_for_call(
            _call(snapshot_id=snapshot.snapshot_id),
            principal_id="prn_operator",
            workspace_id="ws_project",
            session_id="ses_bridge",
            idempotency_key="assign-other-new",
            caller_client_id=lister.client_id,
            claimed_at=NOW,
        )


@pytest.mark.asyncio
async def test_assign_rebinds_call_to_selected_client_current() -> None:
    worker_snapshot = _snapshot()
    selected_snapshot = _snapshot()
    other_snapshot = _snapshot()
    reader = _client(tools=("read_file",), snapshot_id=selected_snapshot.snapshot_id)
    lister = _client(tools=("list_files",), snapshot_id=other_snapshot.snapshot_id)
    store = FakeStore(
        (reader, lister),
        snapshots=(worker_snapshot, selected_snapshot, other_snapshot),
    )
    coordinator = BridgeAssignmentCoordinator(
        store, FakeLiveness({reader.client_id, lister.client_id})
    )
    call = _call(snapshot_id=worker_snapshot.snapshot_id)
    assignment = await coordinator.assign_for_call(
        call,
        principal_id="prn_operator",
        workspace_id="ws_project",
        session_id="ses_bridge",
        idempotency_key="assign-rebind",
        caller_client_id=reader.client_id,
        claimed_at=NOW,
    )
    assert assignment.claim is not None
    assert assignment.claim.client_id == reader.client_id
    assert store.bound_snapshots[call.call_id] == selected_snapshot.snapshot_id
    assert assignment.claim.snapshot_id == selected_snapshot.snapshot_id
    assert assignment.claim.snapshot_id != other_snapshot.snapshot_id


@pytest.mark.asyncio
async def test_result_wake_is_emitted_only_on_first_settlement() -> None:
    liveness = FakeLiveness()
    coordinator = BridgeAssignmentCoordinator(FakeStore(), liveness)
    await coordinator.wake_after_settlement("run_one", replayed=False)
    await coordinator.wake_after_settlement("run_one", replayed=True)
    assert liveness.wakes == ["run_one"]
