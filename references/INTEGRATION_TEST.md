# AI Bridge Integration Test Manual (curl)

This guide targets environments where server-side tools (for example, `weather`) are deployed. It uses a fixed request template and provides multiple curl cases and observation points to validate:

- streaming vs non-streaming responses
- server-tool vs client-tool branching behavior
- usage accumulation (`stream_options.include_usage`)

## 1. Preconditions

- AI Bridge service is running and listens on `http://localhost:8000`
- The server has registered the `weather` tool (executed on the backend)
- The client tool is `client_ping` (pass-through, not executed on the server)

## 2. Base Request Template

All examples extend the template below.

Save the request body as JSON, then send it with `--data @file`:

```json
{
  "stream": true,
  "stream_options": {
    "include_usage": true
  },
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "Get Beijing weather"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "client_ping",
        "parameters": {
          "type": "object",
          "properties": {
            "message": {
              "type": "string"
            }
          },
          "required": [
            "message"
          ]
        }
      }
    }
  ]
}
```

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data @request.json
```

## 3. Test Cases and Observation Points (4 Core Scenarios)

Cover four core scenarios and run each in both streaming and non-streaming mode (8 cases total):

- Server-only tools: LLM calls `weather` -> server executes -> multi-turn continues -> final reply; validate usage accumulation and no tool calls in the client response
- Client-only tools: LLM calls `client_ping` -> immediate pass-through -> stop; validate tool_calls pass-through and `[DONE]`
- Mixed tools: server + client tools -> drop server tools, pass client tools only; validate no further multi-turn
- No tools: direct generation; validate streaming behavior and usage

### 3.1 Server-Only Tools (Stream)

Scenario: request includes no client tools, relies on server-side `weather` only.

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": true,
  "stream_options": {"include_usage": true},
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Get Beijing weather"}]
}'
```

Observation points:

- The client does not see the `weather` tool-call process (server executes and continues multi-turn).
- The client ultimately sees only the LLM-generated text (for example, weather info).
- `usage` should accumulate across turns (if a tool call occurs).

### 3.2 Client-Only Tools (Stream)

Scenario: request includes only `client_ping`, server tools are not involved.

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": true,
  "stream_options": {"include_usage": true},
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Call client_ping with message=ping"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "client_ping",
        "parameters": {
          "type": "object",
          "properties": {"message": {"type": "string"}},
          "required": ["message"]
        }
      }
    }
  ]
}'
```

Observation points:

- The response contains `tool_calls` and the tool name is `client_ping`.
- The server does not execute tools; tool calls stream quickly, followed by `[DONE]`.
- `usage` appears in the stream or final usage chunk (provider behavior).

### 3.3 Server + Client Mixed (Stream)

Scenario: request includes `client_ping`, server also has `weather`.

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": true,
  "stream_options": {"include_usage": true},
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Get Beijing weather, then call client_ping with message=ping"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "client_ping",
        "parameters": {
          "type": "object",
          "properties": {"message": {"type": "string"}},
          "required": ["message"]
        }
      }
    }
  ]
}'
```

Observation points:

- If the LLM generates both `weather` and `client_ping`, the server drops `weather` and passes only `client_ping`.
- The stream should contain only `client_ping` tool calls.
- After `[DONE]`, the dialogue ends and does not continue multi-turn.

### 3.4 No Tools (Stream)

Scenario: request has no tools; validate direct generation and usage.

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": true,
  "stream_options": {"include_usage": true},
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Say a few lines"}]
}'
```

Observation points:

- Streamed content only, no tool calls.
- `usage` is returned (provider behavior).

### 3.1.1 Server-Only Tools (Non-Streaming)

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": false,
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Get Beijing weather"}]
}'
```

Observation points:

- Final LLM reply only (no `weather` tool calls).
- `usage` reflects multi-turn accumulation when tool calls occur.

### 3.2.1 Client-Only Tools (Non-Streaming)

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": false,
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Call client_ping with message=ping"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "client_ping",
        "parameters": {
          "type": "object",
          "properties": {"message": {"type": "string"}},
          "required": ["message"]
        }
      }
    }
  ]
}'
```

Observation points:

- The JSON response includes `tool_calls` and only `client_ping`.
- The server does not execute tools; tool-call info is returned directly.

### 3.3.1 Server + Client Mixed (Non-Streaming)

```sh
curl -sS --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": false,
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Get Beijing weather, and call client_ping with message=ping"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "client_ping",
        "parameters": {
          "type": "object",
          "properties": {"message": {"type": "string"}},
          "required": ["message"]
        }
      }
    }
  ]
}'
```

Observation points:

- The response contains only `client_ping` tool calls.
- The dialogue does not continue multi-turn.

### 3.4.1 No Tools (Non-Streaming)

```sh
curl --request POST \
  --url http://localhost:8000/v1/chat/completions \
  --header 'content-type: application/json' \
  --data '{
  "stream": false,
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Say a few lines"}]
}'
```

Observation points:

- Plain text response, no tool calls.
- `usage` is present.

## 4. How to validate usage

- Streaming: with `stream_options.include_usage`, check whether usage appears and accumulates across turns.
- Non-streaming: check `usage.total_tokens` is higher than a single turn (multi-turn should increase it).
- invoke (if used): `TokenUsage` is accumulated.

## 5. Troubleshooting

- No tool calls: confirm the model supports tool calls and the `tools` schema is correct.
- Missing usage in stream: provider behavior; some models only include usage in the final chunk.
- Mixed scenario shows server tool calls: incorrect behavior; mixed mode should pass through only client tools.

## 6. Response Recording (Optional)

To record provider responses in a single file, set:

```sh
export YOMO_PROVIDER_RECORD_PATH=/tmp/yomo_ai_responses.jsonl
```

Recording is JSONL (one line per request). Fields include:

- `ts` request timestamp
- `trans_id` transaction ID (if available)
- `call_index` LLM call number
- `stream` stream mode flag
- `provider` provider name
- `request` request payload
- `response` non-stream response
- `stream_chunks` raw stream chunks
