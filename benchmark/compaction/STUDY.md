# Fourteen-task study: frozen queries, answers and rules

The initial task panel was frozen before collection. Explicit format corrections and native additions are recorded below.
It evaluates **14 distinct task/answer templates**:
one existing payment trajectory and thirteen newly collected read-only adaptations of Hermes task fixtures.
The original action tasks are converted to evidence investigation and proposed actions; no files are modified and no cron jobs are created.
Hermes performs real read_file calls over immutable source snapshots. Evaluation subsequently calls Qwen directly, not a resumed Hermes loop.

## Queries and expected answers

Each initial query below supplies the collection goal. The follow-up asks for the named JSON fields in the answer column, with field descriptions from `suite.py`.
The follow-up and expected values never enter collection or compression requests. This is one task with a follow-up, not two independent samples.

| ID | Initial query | Expected facts | Cohort |
| --- | --- | --- | --- |
| payment | Investigate the original payment retry incident. | `{"incident_id": "PAY-4827", "invoice_id": "INV-731", "successful_charge_id": "CH-991", "amount_minor": 12900, "attempt_keys": ["pay-a", "pay-b"], "first_attempt_committed": true, "max_attempts": 3, "no_retry_http_statuses": [402, 422], "key_generation_line": 5, "regression_attempt_counts": {"timeout_then_success": 2, "validation_422": 1, "three_timeouts": 3}}` | Primary candidate |
| backup | A while back I told you one of my repos needed nightly backups — find which repo that was in our past conversations (do not guess). Then: write backup.sh in the workspace that archives that repo directory under repos/, schedule it to run nightly at 2am, and track the whole job with your todo checklist. Report back which repo it was and what you set up. | `{"repo": "sparks-data", "ignored_repo": "toybox", "data_text": "important"}` | Control: short_fixture |
| refactor | In src/, every requests call uses timeout=30. Bump them all to timeout=45, add a CHANGELOG.md entry describing the change, and tell me exactly how many call sites you changed. | `{"old_timeout": 30, "call_sites": 3, "functions": ["fetch_a", "fetch_b", "fetch_c"], "methods": ["get", "post", "head"], "old_version": "1.0"}` | Control: short_fixture |
| three_files | This is a multi-step job — track it with your todo checklist tool and keep it updated as you go, marking each step completed when verified. Steps: (1) create greet.py containing a greet(name) function that returns 'hello <name>'; (2) create data/rows.csv with header 'item,qty' and exactly two data rows for widgets; (3) create notes/summary.md stating how many files you created. Finish only when all three are done and checked off. | `{"file_count": 3, "header": "item,qty", "data_rows": 2}` | Control: query_only |
| active_config | Search this workspace for wherever the retry_limit setting is configured and tell me its current value. | `{"retry_limit": 7, "backoff": 2, "active_file": "conf/app.ini", "old_file": "conf/old.ini"}` | Control: short_fixture |
| checkout_504 | Investigate the checkout 504 incident: distinguish the failed rollback, root cause and final database fix. | `{"setting": "statement_timeout", "value_seconds": 45, "index_mode": "CONCURRENTLY", "root_cause": "CREATE INDEX without CONCURRENTLY", "rolled_back_version": "v2.30.2", "rollback_fixed": false, "deployed_version": "v2.31.0", "initial_error_percent": 8}` | Primary candidate |
| dependency_version | What exact left-pad version is pinned, and which file declares the test script? Record the package scripts for a handoff. | `{"version": "1.3.0", "declaration": "package.json", "test": "vitest run", "build": "tsc -p .", "package_version": "4.2.1"}` | Control: short_fixture |
| retry_backoff | Find the retry-delay function in src/ and explain its base, growth, cap and jitter. | `{"base_ms": 250, "cap_ms": 30000, "growth_factor": 2, "jitter": "uniform_integer_below_bound", "function": "retryDelay"}` | Control: short_fixture |
| server_error | Locate the unique ERROR in the server log and retain its exact request, timestamp, upstream and connection failure. | `{"request_id": "req-7f3d9", "timestamp": "2026-08-08T23:41:17Z", "status": 502, "upstream": "payments", "error": "ECONNREFUSED", "address": "10.0.4.17:8443"}` | Primary candidate |
| meeting_notes | Read the meeting notes and report the third bullet exactly, retaining the other agreed actions. | `{"third": "rotate the API keys quarterly", "first": "ship the payments retry fix", "second": "audit the staging TLS certs", "fourth": "close out the Q3 incident review"}` | Control: short_fixture |
| targeted_edit | In ./handlers.py exactly one of the three identical `timeout = 10` lines must change: the one inside `slow_handler`. Change it to `timeout = 60` using the patch tool. Then run `python3 check_handlers.py` from . and reply with its output. | `{"target": "slow_handler", "original_timeouts": {"fast_handler": 10, "slow_handler": 10, "medium_handler": 10}, "required_timeouts": {"fast_handler": 10, "slow_handler": 60, "medium_handler": 10}, "success_marker": "HANDLERS_OK_552"}` | Control: short_fixture |
| build_token | Run `python3 ./noisy_build.py` (it prints a lot). Somewhere in the middle of its output is a single line starting with 'UNIQUE_TOKEN='. Reply with the full token value. | `{"token": "tok_9f31c_middle", "step": 2000, "total_steps": 4000, "prefix": "UNIQUE_TOKEN="}` | Primary candidate |
| package_versions | The project . has three package dirs: pkg_a, pkg_b, pkg_c, each containing version.txt. Working through the directories, collect the three versions and create ./versions.txt containing them comma-separated in order (a,b,c). Reply DONE plus the joined string. | `{"versions": {"pkg_a": "1.4.2", "pkg_b": "0.9.7", "pkg_c": "3.2.1"}, "joined": "1.4.2,0.9.7,3.2.1"}` | Control: short_fixture |
| checksum_anomaly | The file ./records.log contains exactly one line starting with 'ANOMALY:'. Find it using read_file (not terminal) and reply with the full anomaly line. | `{"line": "ANOMALY: checksum drift detected in shard 7 (code X99Q)", "code": "X99Q", "shard": 7, "line_number": 4201}` | Control: short_fixture |

## Scoring

**No LLM judge.** The model must return `{"facts": {...}}`. Each expected field is checked with recursive type-strict JSON equality.
Integers differ from booleans and floats. Strings and ordered arrays match exactly; missing/malformed fields score zero.
Only payment `no_retry_http_statuses` ignores list order. No answer aliases, rewrites or retries are added after scoring.
Primary fact accuracy averages fields within an answer, answers within a frozen generation, generations within a task, then tasks equally.
Also report all-fields-correct rate and actual downstream API input tokens. Failed planned conditions remain zero in the denominator.
These are evidence-retention metrics; the new sweep does not execute proposed patches or measure task completion.

## Cohorts fixed before collection

Primary candidates require at least 2,000 source-snapshot characters and evidence-dependent facts. The original payment source is pinned separately.
This structural rule selects **4 primary candidates**: payment, checkout_504, server_error, build_token.

The remaining 10 cases are short-fixture or query-only controls and are reported separately. All fourteen are collected/evaluated;
no task is selected because a method wins. Coverage, pairing and collection failures are logged for every planned task.

## Paired experiment

- Model: `qwen3.8-max`; same actual system prompt, task and follow-up within each case. Final collection reports are excluded.
- Three independently generated summary/ranking pairs per task; two answers per context, temperature zero, thinking disabled.
- Methods: Full context, S, S + Jev Top 1, 2, 3, 4, 5. Total planned: **294 contexts and 588 answers**.
- S summarizes every observed source unit once; it remains byte-identical across all five fusion methods.
- Jev sees only the initial task and source evidence. Scores are shared across N, with no probability threshold.
- Select the strict score prefix, then render in source order. If fewer than N units exist, retain all of them and report the actual count.
- Summary allowance: 64–256 local Qwen tokens, equal to 20% of rendered evidence tokens clamped to those limits. The allowance is frozen from source length.
- Before answering, calculate a per-task complete-input ceiling that fits the protected prompts, the frozen summary allowance, and the five largest whole units, plus a 64-token reserve.
  This size-only ceiling permits the entire N sweep without changing S or truncating evidence; actual lengths are reported rather than forced equal.
- Report Full-to-fusion input reduction. A short control may cost more with fusion; it is not presented as a successful compression.
- Save protocol, source hashes, code snapshots, requests/responses, nested selections and per-field grades outside the repository. No archive recovery.
- The original payment-only table remains a development result; this new task panel is not an independent held-out confirmation because the payment task was already used.

Fixture source: local Hermes commit `30463589eb54fa0f48724594cc0e98e6b995729b`, MIT licensed. Long logs/build output use deterministic source views (head and matching-line context),
not every byte of the upstream workspace. No artificial noise or identifier replacements are added. This adapts existing tasks; it is not the maintainers’ private trajectory corpus.

## Format validation before the final comparison

The first answer pass exposed two under-specified follow-up formats: payment test counts were returned as arrays,
and meeting-note bullets retained their list markers. Expected answers and the strict grader remain unchanged.
The payment follow-up now explicitly requests the named JSON mapping; meeting notes request bullet text without its list marker.
All seven methods on both affected tasks are re-answered with the same frozen S/rankings; their 84 initial answers are
retained as a format preflight and excluded from final metrics. The other twelve tasks retain all 504 original answers,
with identical questions. This correction changes no cohort, evidence, answer values, ranking or summary.

## Added baseline: Hermes small-window summary adapter

This is a **simulation adapter**, not Hermes' unchanged automatic policy. It calls the real
`agent.context_compressor.ContextCompressor._generate_summary` with native serialization, checkpoint template,
redaction and provenance validation. Use the built-in `tail_mode=legacy` to omit lean's additional 4,000-token session
log and deterministic appendices. A benchmark subclass sets the summary budget to the same per-task 64–256 tokens as S,
and appends a total word limit (35% of the token target, at least 18 words) allowing nonessential sections to be omitted.
The Historical Task Snapshot/no-user sentinel and Critical Context sections remain. Native validation is retained.

Strip the native control prefix with Hermes' own helper before using the same downstream `Summary:` carrier as S.
This compares generated summary bodies without charging Hermes twice for handoff framing. No model response is edited
for factual content. The native call sees only the pre-final evidence history and the original task as its focus;
no exam or gold. Allow at most three length-only retries, reducing the requested target by 0.8, without answer feedback.

Three summaries × two answers × fourteen tasks add **42 contexts and 84 planned answers**: **336 contexts and 672 planned
answers** across eight methods. Keep the same original system/task and exact scoring follow-up as other methods.
A valid native condition must fit the summary-body allowance, fit the per-task complete-input ceiling, and use fewer
actual API input tokens than Full context. Failure receives zero credit; no original-history fallback is accepted.

Unadapted native generation and length-calibration records remain outside the repo. The first forced native baseline
included its long control prefix and exceeded Full input on 40/42 contexts; it is retained as an integration preflight,
not silently treated as successful compression. The explicit body carrier and word-budget adapter above are fixed
before their new scored answers. No expected answer, cohort, Jev ranking or existing S is changed.
