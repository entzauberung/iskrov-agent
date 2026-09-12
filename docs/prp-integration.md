# PRP Integration

Iskrov uses the Progressive Reasoning Protocol as a semantic rule set. It
does not require the PRP repository at runtime and does not claim to be its
only implementation.

| PRP concept | Iskrov representation |
|---|---|
| graph version | `WorkUnit.graph_version`, `ProgressiveRound.graph_version` |
| public artifact | `Artifact` |
| evidence | `Evidence` and verification reports |
| comparison | `RoundComparison` |
| revision decision | `RevisionDecision` / `decide_revision` |
| conservative reuse | `ReuseDecision` with fingerprints and hashes |
| stop reason | `RevisionStopReason` and terminal run facts |

Iskrov extends these facts with provider profiles, reservations, approvals,
workspace snapshots, changesets, merge ledgers, Bridge claims, leases,
sessions, HTTP bindings, and recovery records. Those are product details and
do not belong in PRP's identity.

## Progressive lifecycle

1. The controller creates a bounded plan and base snapshot.
2. Workers produce artifacts and changesets through registered tools.
3. The verifier records deterministic evidence.
4. The controller compares the round with its predecessor.
5. PASS, NO_GAIN, REGRESSION, exhausted budget, or missing trigger stops the
   run; a permitted trigger creates exactly one new graph version.
6. Historical work is reused only when lineage, fingerprints, dependency
   hashes, round facts, and attempt history are all proven.

`INCONCLUSIVE` remains a public result and cannot be turned into success by a
model self-report.

An iPad or other client uses the Native API to create and observe runs, approve
writes, inspect evidence, cancel work, and recover a Bridge session. The
device does not receive arbitrary host paths or provider credentials.
