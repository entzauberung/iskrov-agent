# Iskrov Agent Architecture

Iskrov Agent is a cloud controlled Agent runtime with a small local execution
surface. It is a product implementation, not the definition of the
Progressive Reasoning Protocol.

```text
iPad / Web / CLI / compatible API client
                    |
              Native HTTP API
                    |
        Cloud control and persistence
        model · planner · policy · budget
        approval · verifier · scheduler
                    |
       CLOUD execution or Bridge dispatch
                    |
       registered local tools and workspace
```

The control plane owns decisions and durable facts. A Bridge owns only an
authorized, bounded tool execution and returns a result with an idempotency
key. A device UI observes and controls the run; it is not the execution
environment.

The Native Agent API is the product contract. OpenAI Chat/Responses and
Anthropic Messages routes translate external payloads into the same native
facts; they do not create separate execution engines.

`CLOUD` runs server-owned bounded work, `BRIDGE` creates a claim/lease for a
registered local client, and `LOCAL` runs the same controller in an authorized
workspace. Location and isolation are runtime policy, independent of PRP's
decision about whether a new Progressive graph version is allowed.

Runs, attempts, events, approvals, snapshots, claims, and results are stored
durably in SQLite. Restart recovery never guesses that an interrupted call
succeeded; result submission is idempotent and all transitions remain legal.

Tools are registered, policy checked, and bounded by the workspace and
resource claims. The product does not expose arbitrary shell access, arbitrary
host paths, unlisted network access, or model-controlled privilege escalation.
