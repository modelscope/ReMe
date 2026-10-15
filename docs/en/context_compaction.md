# Context compaction with decision models

Long tasks accumulate source reads, stale searches, repeated diagnostics, and completed side tasks.
`compact_context` uses the **next action** to judge whether an old tool call still matters and whether its full result
must remain verbatim. It returns a proposed message snapshot and per-call decisions. The host decides whether to apply it.

The workflow calls the provider-independent `as_decision_model` interface. The current `agentscope` adapter uses
AgentScope's TypeSafe/Jev implementation; jobs keep the same interface when another backend is registered.

![Decision-model context compaction: guards, bounded observation, two probabilities, and host application](../figure/decision-context-compaction.svg)

## How one pass works

1. **The host archives the original history.** Supply an AgentScope 2.x JSON message snapshot, current `goal`, eligible
   tool names, and protection lists. ReMe neither archives history nor updates a running Agent's state. Apply proposals
   only when the original record remains recoverable.
2. **Deterministic guards select candidates.** Match `tool_call` and `tool_result` by ID. Calls must be `finished`, results
   must be `success`, tools must be explicitly allowlisted, and outputs must be entirely text. Duplicate IDs, missing or
   reversed pairs, and invalid JSON inputs are ineligible.
3. **Build a bounded observation.** Send the goal, conversation text, tool names, shortened inputs, and result character
   counts. Tool-result bodies and thinking are omitted. When necessary, shorten inputs and old text, omit old text-only
   messages, or merge old call records in this view. These changes do not rewrite conversation text in the returned snapshot.
4. **Ask two binary questions per candidate.** `call_<id>` asks whether the call and its input still matter for the next
   action. `result_<id>` asks whether the full output must remain verbatim and later retrieval would be insufficient.
   Keep each question pair together; batches repeat the same observation and run under concurrency and timeout limits.
5. **Rebuild only after every batch succeeds.** Validate answer types and probabilities before applying decisions to a
   deep copy. Missing answers, invalid probabilities, failed batches, or timeout fail the call without a partial proposal.
   The host should continue using its saved original snapshot.

## From probabilities to actions

With retention threshold `t` (default `0.5`), check the result probability first:

| Condition | Action | Proposed snapshot |
| --- | --- | --- |
| `p_result >= t` | `keep` | Keep the call and its complete result, even if `p_call` is lower |
| `p_result < t` and `p_call >= t` | `drop_result` | Keep the call; shorten long text output to a prefix plus an omission marker |
| Both probabilities `< t` | `drop_call` | Remove both tool blocks; remove a message only if this makes it empty |

The default prefix is 300 characters. The marker points back to archived history. Replacement occurs only if it makes
output shorter, so `drop_result` can leave a short output unchanged. User text, assistant text, thinking, and untouched
block fields remain intact.

Deterministic protection takes precedence over probabilities:

- The first message, the most recent `preserve_recent_messages` messages, and `protected_message_ids` are protected.
  Protection of either endpoint protects the complete pair.
- `protected_call_ids` and tools outside `eligible_tool_names` are protected. The default allowlist is empty, so no tools
  are compacted unless the caller explicitly opts them in.
- Unfinished or failed calls, non-text outputs, and mismatched tool names remain intact. Duplicate or missing IDs are
  also retained, but may have no entry in `decisions`.

The host must choose read-only tools for the allowlist; ReMe cannot infer tool side effects from their names.
Explicitly protect indispensable audit records, change receipts, and evidence; semantic probabilities are insufficient
as the sole protection mechanism.

## Configure and call the service

Install dependencies and configure credentials:

```bash
pip install "reme-ai[core,decision]"
export DECISION_MODEL_API_KEY=your-typesafe-api-key
export DECISION_MODEL_BACKEND=agentscope
# Optional: DECISION_MODEL_NAME and DECISION_MODEL_BASE_URL
```

The CLI also loads these `DECISION_MODEL_*` variables from `.env`. The backend name is `agentscope`; see
[decision model configuration](./configuration.md#decision-model-configuration) for the complete settings.
Omitting the model name or setting it to `null` uses the adapter's SDK default.

Start the service in one terminal:

```bash
reme start config=decision_compaction
```

Call it from a second terminal. This short example illustrates the request format; the integration scenarios below
provide longer histories:

```bash
reme compact_context \
  goal='Fix payment retries; the completed icon search is irrelevant' \
  eligible_tool_names='["search_code"]' \
  options='{"preserve_recent_messages":1}' \
  messages='[{"id":"m0","role":"user","content":[{"type":"text","text":"Preserve payment source; clean old icon searches"}]},{"id":"m1","role":"assistant","content":[{"type":"tool_call","id":"c1","name":"search_code","input":"{\"pattern\":\"logo\",\"path\":\"web/icons\"}","state":"finished"},{"type":"tool_result","id":"c1","name":"search_code","output":"Icon paths from a completed task","state":"success"}]},{"id":"m2","role":"user","content":[{"type":"text","text":"Now focus on payment retries"}]}]'
```

`decision_compaction` inherits the default service configuration and other jobs, including normal background workflows.
For embedding in a host process, assemble only the compaction job and its decision component as the integration tests do.

The standard Response's `answer` contains:

- `schema_version` and `messages`: version and proposed snapshot; `changed` and `reason`: whether it changed, with
  `compacted`, `no_change`, or `no_candidates`.
- `decisions`: internal pair ID, original `call_id`, action, reason, and `keep_call` / `keep_result` probabilities for
  pairs evaluated by the model.
- `stats`: message and character counts before and after, candidate/protected counts, estimated observation tokens and
  fitting stage, request count, provider usage, and elapsed time. The same statistics appear in `response.metadata.compaction`.

Check `success`, recalculate the final input budget with the host model's tokenizer, and apply, repeat, or reject the
proposal. Compaction does not automatically summarize, write long-term memory, or execute historical tool calls.

## Budgets, concurrency, and timeout

| `options` field | Default | Purpose |
| --- | --- | --- |
| `keep_threshold` | `0.5` | Shared retention threshold for both questions |
| `preserve_recent_messages` | `6` | Messages protected verbatim, counted as messages rather than turns |
| `max_state_tokens` | `25000` | Estimated observation token limit |
| `max_request_tokens` | `30000` | Per-batch estimated observation/question budget, including a 256-token overhead reserve |
| `truncate_head_chars` | `300` | Text prefix retained by `drop_result` |
| `max_concurrency` | `4` | Concurrent decision requests, from 1 to 32 |
| `total_timeout_seconds` | `30` | Overall deadline for decision requests and their queueing |

Component `timeout`, `max_retries`, and `retry_delay` control individual provider requests and retries. The compaction
preset uses 10 seconds, one retry, and 0.5 seconds of initial backoff. Local token estimates differ from provider billing
and from the host model tokenizer. If the observation cannot fit, or a single question pair cannot fit a request, the
call fails and the host retains its original snapshot.

## Two live-model integration scenarios

The [integration tests](https://github.com/agentscope-ai/ReMe/blob/main/tests/integration/test_decision_compaction.py)
provide two synthetic long-task histories. Historical deploys, rollbacks, and database queries are fixture data and are
never executed; only the decision requests call the real TypeSafe/Jev API.

| Scenario | Current task and important candidates | Distractors and protection boundaries |
| --- | --- | --- |
| Payment retry patch | Produce an exact patch from previously read source and regression-test lines; keep those candidate results intact | Completed theme CSS, icon searches, and obsolete inventory include removable calls; preserve billing evidence, approval receipts, failed/pending work, duplicate IDs, and recent messages |
| Replication incident | Quote exact incident logs and WAL offsets in a root-cause report; keep the verbatim evidence intact | Mix in completed marketing reports, holiday weather, and retired-system load tests; preserve audit approval, rollback receipts, non-text charts, failed queries, and recent messages |

Both cases check real batched inference, removal of at least one irrelevant call, full retention of critical candidates,
protected history and conversation text, unchanged original input and temporary archive, and a reduction in output
characters. Semantic assertions can expose model/configuration changes; the tests do not fabricate probabilities to pass.

A live run on 2026-10-15 against the locally configured TypeSafe/Jev endpoint passed both cases. These are JSON
character counts, not token savings:

| Scenario | Characters before | Characters after | Reduction | Irrelevant calls removed | Decision requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| Payment retry patch | 39,438 | 12,738 | 67.7% | 3 | 2 |
| Replication incident | 51,485 | 12,828 | 75.1% | 4 | 2 |

Explicitly opt in to live API calls:

```bash
REME_RUN_DECISION_INTEGRATION=1 \
  pytest tests/integration/test_decision_compaction.py -v -s
```

Tests read the environment or repository-root `.env`, with existing environment variables taking precedence. They skip
without opt-in or without an API key. Output contains only synthetic-scenario actions, probabilities, character counts,
and usage. Workspaces and original snapshots use pytest temporary directories. Savings depend on history, goal, and
model decisions; these two scenarios do not establish a general performance guarantee.

## Boundaries

The decision model sees a limited observation and cannot inspect omitted tool-result contents. Incomplete goals or
insufficient tool descriptions can hide relevant evidence. The host must supply a clear next-action goal, explicitly
protect indispensable information, and retain recoverable original history after applying a proposal.
This strategy reduces old tool traces; it does not provide automatic triggering, a final token-budget guarantee,
summary generation, or archival storage.

Contracts and implementation: [compaction schema](https://github.com/agentscope-ai/ReMe/blob/main/reme/schema/compaction.py),
[pairing and rebuilding](https://github.com/agentscope-ai/ReMe/blob/main/reme/steps/compaction/messages.py),
[observation and batching](https://github.com/agentscope-ai/ReMe/blob/main/reme/steps/compaction/state.py), and
[job step](https://github.com/agentscope-ai/ReMe/blob/main/reme/steps/compaction/compact_context.py).
