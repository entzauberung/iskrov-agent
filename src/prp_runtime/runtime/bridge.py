"""Server-owned Bridge assignment from durable client facts.

Selection happens only for a concrete ToolCall. Candidates are loaded from the
Store and liveness supervisor; they are never unioned across a principal and
never taken from in-memory handshake records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from prp_runtime.analysis.syntax import BoundSyntaxReport, analyze_bounded_observation, source_pair_from_observation
from prp_runtime.domain.enums import BridgeClientLiveness
from prp_runtime.domain.errors import StateError
from prp_runtime.domain.events import EventType, payload_from_bridge_client_skip
from prp_runtime.domain.models import Artifact, RegisteredBridgeClient
from prp_runtime.domain.values import utc_now
from prp_runtime.runtime.scheduler import (
    BridgeClientCandidate,
    BridgeClientSelection,
    select_bridge_client,
)
from prp_runtime.tools.models import BridgeClaim, ToolCall
from prp_runtime.workspace.models import Snapshot, SnapshotStatus

__all__ = ["BridgeAssignment", "BridgeAssignmentCoordinator", "BridgeAssignmentStore", "syntax_facts_from_bridge_artifact"]

_MAX_ACTIVE_CLAIMS = 1


@dataclass(frozen=True, slots=True)
class BridgeAssignment:
    """One server-owned assignment attempt for a concrete tool call."""

    claim: BridgeClaim | None
    skipped: tuple[tuple[str, str], ...]


class BridgeAssignmentStore(Protocol):
    async def list_bridge_clients(
        self, *, principal_id: str, workspace_id: str | None = None
    ) -> tuple[RegisteredBridgeClient, ...]:
        """Return durable clients for one principal, optionally one workspace."""

    async def list_active_bridge_claim_counts(
        self, *, principal_id: str, workspace_id: str
    ) -> dict[str, int]:
        """Return ACTIVE lease counts keyed by client_id."""

    async def list_active_bridge_call_ids(
        self, *, principal_id: str, workspace_id: str
    ) -> tuple[str, ...]:
        """Return call ids that already have an ACTIVE lease."""

    async def get_active_bridge_claim(
        self,
        call_id: str,
        *,
        principal_id: str,
        workspace_id: str,
    ) -> BridgeClaim | None:
        """Return the ACTIVE lease for one call, if the Coordinator already assigned it."""

    async def list_snapshots(self, workspace_id: str, *, owner_id: str) -> tuple[Snapshot, ...]:
        """Return owner-scoped snapshots for the call workspace."""

    async def bind_bridge_call_snapshot(
        self,
        call_id: str,
        *,
        snapshot_id: str,
        principal_id: str,
    ) -> None:
        """Rebind one persisted call to the selected client's current snapshot."""

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
        """Atomically bind one call to one client lease."""

    async def append_event(
        self,
        run_id: str,
        event_type: EventType,
        payload: dict[str, object] | None = None,
        *,
        timestamp: datetime | None = None,
    ) -> object:
        """Append one sequenced run event."""


class _SupervisorView(Protocol):
    def bridge_client_liveness(
        self,
        client_id: str,
        *,
        fingerprint: str | None = None,
        now: object | None = None,
    ) -> BridgeClientLiveness:
        """Return LIVE/OFFLINE/EXPIRED without mutating run facts."""

    async def enqueue(self, run_id: str) -> None:
        """Wake the owning run after a durable first settlement."""


class BridgeAssignmentCoordinator:
    """Build exact-capability candidates from durable facts and persist one assignment."""

    def __init__(self, store: BridgeAssignmentStore, supervisor: _SupervisorView) -> None:
        self._store = store
        self._supervisor = supervisor

    async def select_for_call(
        self,
        call: ToolCall,
        *,
        principal_id: str,
        workspace_id: str,
    ) -> BridgeClientSelection:
        """Select one client for a concrete server-approved tool call."""
        if not call.tool_name or call.snapshot_id is None:
            raise ValueError("Bridge assignment requires a concrete tool call and snapshot")
        clients = await self._store.list_bridge_clients(
            principal_id=principal_id, workspace_id=workspace_id
        )
        counts = await self._store.list_active_bridge_claim_counts(
            principal_id=principal_id, workspace_id=workspace_id
        )
        claimed_call_ids = await self._store.list_active_bridge_call_ids(
            principal_id=principal_id, workspace_id=workspace_id
        )
        candidates = tuple(
            BridgeClientCandidate(
                client_id=client.client_id,
                workspace_id=client.workspace_id,
                tools=tuple(client.capabilities.tools),
                effects=tuple(effect.value for effect in client.capabilities.effects),
                liveness=self._liveness_for(client),
                snapshot_id=client.current_snapshot_id,
                status=client.status.value,
                fingerprint=client.capability_fingerprint,
                active_claims=counts.get(client.client_id, 0),
                max_active_claims=_MAX_ACTIVE_CLAIMS,
            )
            for client in sorted(clients, key=lambda item: item.client_id)
        )
        return select_bridge_client(
            workspace_id=workspace_id,
            tool_name=call.tool_name,
            candidates=candidates,
            claimed_call_ids=claimed_call_ids,
            call_id=call.call_id,
            effect=call.effect.value,
        )

    async def assign_for_call(
        self,
        call: ToolCall,
        *,
        principal_id: str,
        workspace_id: str,
        session_id: str,
        idempotency_key: str,
        caller_client_id: str | None = None,
        claimed_at: datetime | None = None,
    ) -> BridgeAssignment:
        """Persist one call/client/lease binding and bounded skip reasons."""
        existing = await self._store.get_active_bridge_claim(
            call.call_id,
            principal_id=principal_id,
            workspace_id=workspace_id,
        )
        if existing is not None:
            if caller_client_id is not None and caller_client_id != existing.client_id:
                raise StateError("caller is not the server-selected Bridge client")
            return BridgeAssignment(claim=existing, skipped=())
        selection = await self.select_for_call(
            call, principal_id=principal_id, workspace_id=workspace_id
        )
        if selection.selected is None:
            await self._record_skips(call.run_id, call.call_id, selection.skipped)
            return BridgeAssignment(claim=None, skipped=selection.skipped)
        if caller_client_id is not None and caller_client_id != selection.selected.client_id:
            raise StateError("caller is not the server-selected Bridge client")
        await self._record_skips(call.run_id, call.call_id, selection.skipped)
        selected_snapshot_id = selection.selected.snapshot_id
        if selected_snapshot_id and selected_snapshot_id != call.snapshot_id:
            await self._store.bind_bridge_call_snapshot(
                call.call_id,
                snapshot_id=selected_snapshot_id,
                principal_id=principal_id,
            )
        claim = await self._store.claim_tool_call(
            session_id,
            call.run_id,
            call.call_id,
            principal_id=principal_id,
            client_id=selection.selected.client_id,
            idempotency_key=idempotency_key,
            claimed_at=claimed_at,
        )
        return BridgeAssignment(claim=claim, skipped=selection.skipped)

    async def wake_after_settlement(self, run_id: str, *, replayed: bool) -> None:
        """Wake the owning run exactly once after a first settlement."""
        if replayed:
            return
        await self._supervisor.enqueue(run_id)

    def _liveness_for(self, client: RegisteredBridgeClient) -> str:
        durable = getattr(self._store, "bridge_client_liveness", None)
        if callable(durable):
            try:
                return durable(
                    client.client_id,
                    now=utc_now(),
                    principal_id=client.principal_id,
                    fingerprint=client.capability_fingerprint,
                ).value
            except TypeError:
                pass
        return self._supervisor.bridge_client_liveness(
            client.client_id, fingerprint=client.capability_fingerprint
        ).value

    async def _record_skips(
        self, run_id: str, call_id: str, skipped: tuple[tuple[str, str], ...]
    ) -> None:
        for client_id, reason in skipped:
            await self._store.append_event(
                run_id,
                EventType.BRIDGE_CLIENT_SKIPPED,
                payload_from_bridge_client_skip(
                    call_id=call_id, client_id=client_id, reason=reason
                ),
            )


def syntax_facts_from_bridge_artifact(
    artifact: Artifact,
    *,
    round_id: str | None = None,
    snapshot_id: str | None = None,
) -> BoundSyntaxReport:
    """Parse only the artifact's returned text. Never scan a Bridge root."""
    payload: object = artifact.content
    if artifact.kind.value == "JSON":
        import json

        try:
            loaded = json.loads(artifact.content)
        except json.JSONDecodeError:
            loaded = None
        payload = loaded
        if snapshot_id is None and isinstance(loaded, dict):
            candidate = loaded.get("snapshot_id")
            if isinstance(candidate, str):
                snapshot_id = candidate
    before, after = source_pair_from_observation(payload if not isinstance(payload, str) else payload)
    return analyze_bounded_observation(
        artifact_id=artifact.artifact_id,
        work_unit_id=artifact.work_unit_id,
        run_id=artifact.run_id,
        before_source=before,
        after_source=after,
        round_id=round_id,
        snapshot_id=snapshot_id,
    )
