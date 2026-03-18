# Multi-Turn Dialogue and Tool-Calling Requirements

## 1. Overview

YoMo AI Bridge provides multi-turn dialogue and tool-calling capabilities, allowing the LLM to invoke external tools during a conversation to complete complex tasks.

The system supports two tool types:

- **Server-side tools**: Registered on the server. When the LLM decides to call them, the server executes the tool automatically and returns the result to the LLM. The LLM then continues generating a reply based on the result. This entire process is transparent to the client.

- **Client-side tools**: Provided by the client in the request. When the LLM decides to call them, the server forwards the tool call to the client. The client decides how to handle it.

## 2. Tool Merge

When the request includes tools and the server also has registered tools, the system merges them for LLM usage.

### 2.1 Merge Rules

The merged tool list contains request tools and server-registered tools. If both define a tool with the same name, the server-registered definition takes precedence.

### 2.2 Example

If the request provides `[A, B]` and the server registers `[B, C]`, the merged result is `[B (server version), A, C]`. Tool B uses the server definition, tool A comes from the request, and tool C comes from the server.

## 3. Tool-Call Flow

When the LLM response includes tool calls, the system selects a handling strategy based on tool source.

### 3.1 Server-Only Tool Calls

When all called tools are server-side, the server does:

1. Execute tool calls and obtain results
2. Append tool results to the dialogue history
3. Call the LLM again so it can generate the final reply from tool results
4. Return the final reply to the client

The client never sees tool calls and only receives the final content.

### 3.2 Client-Only Tool Calls

When all called tools are client-side, the server forwards tool-call information to the client. The server does not execute these tools and does not call the LLM again.

If the LLM returns a tool name not present in the merged tool list, the server treats it as a client-side tool and forwards it.

### 3.3 Mixed Tool Calls

When the LLM calls both server-side and client-side tools, the server drops server-side tool calls and forwards only client-side tool calls.

This avoids forcing the client to coordinate partial results with server execution, keeping responses simple and deterministic.

## 4. Stop Conditions

The multi-turn conversation ends when:

- The LLM response contains no tool calls
- The LLM calls only client-side tools (after forwarding, stop)
- The LLM calls both server and client tools (after forwarding client tools, stop)
- The maximum call limit is reached (default 14), to prevent infinite loops. This limit only applies when the system would continue multi-turn (server-only tool calls).

## 5. Streaming Responses

In streaming mode:

- Server-only tools: the client receives no data during tool execution. Streaming starts only after the final LLM response begins.
- Client-only tools: once the server identifies the call as client-side, it immediately streams the tool-call information to the client.
- Mixed tools: once client-side tool calls are identified, the server immediately streams those client tool calls (server tool calls are not forwarded).

## 6. Non-Streaming Responses

In non-streaming mode:

- Server-only tools: the client receives the final reply content.
- Client-only tools: the client receives a full response containing tool-call information.
- Mixed tools: the client receives a response containing only client tool calls.

## 6.1 multiTurnFunctionCalling Flow (Streaming vs Non-Streaming)

> The following describes the actual code paths and branching behavior of `multiTurnFunctionCalling`.

### 6.1.1 Overall Loop

1. Before each LLM call, if this is not the first round, clear `ToolChoice` to avoid forced tool selection.
2. Call the LLM to get a response (streaming or non-streaming based on `req.Stream`).
3. If the maximum call count is reached (default 14), write the current response and stop.
4. Check if the response contains tool calls:
   - No tool calls: return the response and stop.
   - Tool calls: determine tool source (server-only / client-only / mixed).

### 6.1.2 Non-Streaming Branch (`req.Stream=false`)

- No tool calls: write response and stop.
- Server-only tools: execute tool calls, append tool messages, then call the LLM again (continue multi-turn).
- Client-only tools: do not execute tools, forward tool calls, stop.
- Mixed tools: drop server tools, forward client tool calls, stop.

### 6.1.3 Streaming Branch (`req.Stream=true`)

- When the first chunk arrives, set stream headers and flush.
- No tool calls: stream content, then write `[DONE]` and stop.
- Server-only tools: do not forward tool calls; execute tools and continue to the next round (client receives no data during tool execution).
- Client-only tools: once client tool calls are detected, forward them, then write `[DONE]` and stop.
- Mixed tools: drop server tools, forward client tool calls, then write `[DONE]` and stop.

### 6.1.4 Summary Table

| Mode | Tool Call Type | Server Behavior | Client-Visible Output | Continue Multi-Turn |
|------|----------------|-----------------|-----------------------|---------------------|
| Stream | Server-only | Execute tools and append tool messages | No data during tool execution; final content streams in next round | Yes |
| Stream | Client-only | Do not execute; forward tool calls | Tool calls streamed immediately, then `[DONE]` | No |
| Stream | Mixed | Drop server tools; forward client tools | Client tool calls streamed immediately, then `[DONE]` | No |
| Non-streaming | Server-only | Execute tools and append tool messages | Final reply content | Yes |
| Non-streaming | Client-only | Do not execute; forward tool calls | Full response with tool calls | No |
| Non-streaming | Mixed | Drop server tools; forward client tools | Response with client tool calls | No |

## 7. Edge Cases

### 7.1 No Tools

When the request provides no tools and the server has no registered tools, the system calls the LLM normally and returns the response.

### 7.2 Call Limit Reached

When the number of consecutive LLM calls reaches the limit (14), the system stops and returns the current response even if more tool calls remain. This prevents infinite tool-call loops. The limit applies only when the system would otherwise continue multi-turn (server-only tool calls).

### 7.3 Tool Execution Failure

If a server-side tool fails, the system returns an error and terminates the dialogue.

## 8. Compatibility Notes

Before this change, when a request included tools, the server ignored all registered tools and returned the response directly to the client.

After this change, request tools and registered tools are merged, and the system decides handling based on tool source. This supports more flexible tool combinations.
