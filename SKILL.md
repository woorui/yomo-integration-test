---
name: yomo-integration-test
description: Generate curl integration test cases for YoMo AI Bridge, call the user-run HTTP server, compare provider recordings (JSONL) with actual responses, and output a Markdown report. Use this for verifying tool-call routing, streaming vs non-streaming behavior, usage accumulation correctness, and client/server tool filtering.
---

# YoMo Integration Test Skill

## 1. Purpose

This skill drives an end-to-end integration test flow: generate reproducible curl cases, execute requests against the running AI Bridge server, compare provider recordings with actual responses, and emit a Markdown report.

## 2. Preconditions

- The user knows how to start the server and server-side tools and can supply startup commands.
- Provider recording is enabled through `YOMO_PROVIDER_RECORD_PATH`.

## 3. Workflow

### 3.1 Initialize a run directory

Each run writes artifacts into a dedicated directory:

```
python ~/.agents/skills/yomo-integration-test/scripts/run_commands.py init
```

This creates `./.it-runs/YYYY-MM-DD_HHMM/` in the current directory and copies `commands.json`.

Run init and then to ask the user to fill in the `commands.json` file.

Use the generated `commands.json` in that run directory. There maybe no pre-existing `commands.json` in the repo root.

The init output prints the required request/response file names. Save JSON bodies and responses using these names.

### 3.2 Fill commands.json

Complete the run directory `commands.json`:

- `server.command`: server start command
- `server.port`: server listening port (used for shutdown)
- `server.workdir`: working directory (optional; default is the current directory)
- `server.env`: environment variables (the script injects `YOMO_PROVIDER_RECORD_PATH` into the run directory; do not set it manually)
- `request.headers`: HTTP headers for curl requests (for example `content-type: application/json`)
- `tools[]`: each server-side tool start command, workdir, env

Continue only after the file is filled.

### 3.3 Start server and tools

```
python ~/.agents/skills/yomo-integration-test/scripts/run_commands.py start --run-dir ./.it-runs/YYYY-MM-DD_HHMM --wait 10
```

Server stdout/stderr is written to `./.it-runs/YYYY-MM-DD_HHMM/server.log`.

Each tool writes stdout/stderr to `./.it-runs/YYYY-MM-DD_HHMM/<tool-name>.log`.

Start only server or tools when needed:

```
python ~/.agents/skills/yomo-integration-test/scripts/run_commands.py start --run-dir ./.it-runs/YYYY-MM-DD_HHMM --only server --wait 10
python ~/.agents/skills/yomo-integration-test/scripts/run_commands.py start --run-dir ./.it-runs/YYYY-MM-DD_HHMM --only tools --wait 10
```

### 3.4 Generate and run curl cases

Run four core scenarios in both streaming and non-streaming modes (8 cases total):

- server-only tools
- client-only tools
- mixed tools (server + client)
- no tools

Reference details:

- `references/INTEGRATION_TEST.md`
- `references/CHAT_LOGIC.md`
- `references/TOOL_CALL_CASES.md`

Store requests and responses as follows (requests are JSON bodies sent with `--data @requests/*.json`, use `-sS` to suppress progress output):

- `./.it-runs/YYYY-MM-DD_HHMM/requests/`
- `./.it-runs/YYYY-MM-DD_HHMM/responses/`

### 3.5 Read recordings and compare

- Read JSONL from `YOMO_PROVIDER_RECORD_PATH`
- Compare actual responses vs recordings:
  - tool_calls presence and filtering
  - streaming vs non-streaming termination
  - usage expectations (multi-turn accumulation must be correct)
  - content completeness (no truncation)

If the recording file is not already in the run directory, copy it to:

```
./.it-runs/YYYY-MM-DD_HHMM/record.jsonl
```

### 3.6 Write the Markdown report

Write the report to:

```
./.it-runs/YYYY-MM-DD_HHMM/report.md
```

The report includes:

- Summary (pass/fail counts)
- Case details (request, expected, actual, diff)
- Conclusions

Case numbering matches the template (run cases without server tools first):

- Case 1: no tools (streaming)
- Case 2: no tools (non-streaming)
- Case 3: client-only tools (streaming)
- Case 4: client-only tools (non-streaming)
- Case 5: server-only tools (streaming)
- Case 6: server-only tools (non-streaming)
- Case 7: mixed tools (streaming)
- Case 8: mixed tools (non-streaming)

> All test cases require the server to be started, while cases involving server-side tools also require those tools to be running.

Execution order:

1) Start server (do not start server-side tools), wait 10 seconds
2) Run Case 1–4
3) Start server-side tools, wait 10 seconds
4) Run Case 5–8
5) Stop server-side tools and server
6) Summarize results and write the report

Request/response file names match the template:

- `requests/no_tools_streaming.json` / `responses/no_tools_streaming.txt`
- `requests/no_tools_non_streaming.json` / `responses/no_tools_non_streaming.txt`
- `requests/client_tool_streaming.json` / `responses/client_tool_streaming.txt`
- `requests/client_tool_non_streaming.json` / `responses/client_tool_non_streaming.txt`
- `requests/server_tool_streaming.json` / `responses/server_tool_streaming.txt`
- `requests/server_tool_non_streaming.json` / `responses/server_tool_non_streaming.txt`
- `requests/mixed_streaming.json` / `responses/mixed_streaming.txt`
- `requests/mixed_non_streaming.json` / `responses/mixed_non_streaming.txt`

## 4. Stop server and tools

Stop by force-killing all processes started by the script:

```
python ~/.agents/skills/yomo-integration-test/scripts/run_commands.py stop --run-dir ./.it-runs/YYYY-MM-DD_HHMM
```

The script kills by PID and by command line match to ensure cleanup.

## 5. When to read references

- Generate cases and branch expectations: `references/INTEGRATION_TEST.md`, `references/CHAT_LOGIC.md`
- Validate tool-call matrices: `references/TOOL_CALL_CASES.md`
