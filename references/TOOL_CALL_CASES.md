# AI Bridge Tool-Call Scenario Analysis

## M x N Combinations for Tool Merge and Calls

### M: Merged Tool List State
1. M1: No tools
2. M2: Server-only tools
3. M3: Client-only tools
4. M4: Mixed tools (server + client)

### N: LLM Call Behavior
1. N1: No tool calls
2. N2: Calls server-side tools only
3. N3: Calls client-side tools only
4. N4: Mixed calls (server + client tools)

### Combination Details

#### M1: No tools
- **N1: No tool calls**
  - Scenario: no tools after merge, LLM makes no calls
  - Handling: return LLM response directly
  - End condition: yes; multi-turn ends

- **N2: Server-only calls**
  - Scenario: no tools after merge, LLM attempts server tool calls
  - Handling: tool name not in merged list; treat as client tool and pass through
  - End condition: yes; multi-turn ends

- **N3: Client-only calls**
  - Scenario: no tools after merge, LLM attempts client tool calls
  - Handling: tool name not in merged list; treat as client tool and pass through
  - End condition: yes; multi-turn ends

- **N4: Mixed calls**
  - Scenario: no tools after merge, LLM attempts mixed tool calls
  - Handling: tool name not in merged list; treat as client tool and pass through
  - End condition: yes; multi-turn ends

#### M2: Server-only tools
- **N1: No tool calls**
  - Scenario: server-only tools after merge, LLM makes no calls
  - Handling: return LLM response directly
  - End condition: yes; multi-turn ends

- **N2: Server-only calls**
  - Scenario: server-only tools after merge, LLM calls server tools only
  - Handling: execute tool calls, append results to dialogue history, call LLM again
  - End condition: no; continue multi-turn

- **N3: Client-only calls**
  - Scenario: server-only tools after merge, LLM attempts client tool calls
  - Handling: tool name not in merged list; treat as client tool and pass through
  - End condition: yes; multi-turn ends

- **N4: Mixed calls**
  - Scenario: server-only tools after merge, LLM attempts mixed calls
  - Handling: drop server tool calls; pass through client tool calls only
  - End condition: yes; multi-turn ends

#### M3: Client-only tools
- **N1: No tool calls**
  - Scenario: client-only tools after merge, LLM makes no calls
  - Handling: return LLM response directly
  - End condition: yes; multi-turn ends

- **N2: Server-only calls**
  - Scenario: client-only tools after merge, LLM attempts server tool calls
  - Handling: tool name not in merged list; treat as client tool and pass through
  - End condition: yes; multi-turn ends

- **N3: Client-only calls**
  - Scenario: client-only tools after merge, LLM calls client tools only
  - Handling: pass tool-call information to the client
  - End condition: yes; multi-turn ends

- **N4: Mixed calls**
  - Scenario: client-only tools after merge, LLM attempts mixed calls
  - Handling: known client tools pass through; unknown tools treated as client tools and passed through
  - End condition: yes, multi-turn ends

#### M4: Mixed tools (server + client)
- **N1: No tool calls**
  - Scenario: mixed tools after merge, LLM makes no calls
  - Handling: return LLM response directly
  - End condition: yes, multi-turn ends

- **N2: Server-only calls**
  - Scenario: mixed tools after merge, LLM calls server tools only
  - Handling: execute tool calls, append results to dialogue history, call LLM again
  - End condition: no; continue multi-turn

- **N3: Client-only calls**
  - Scenario: mixed tools after merge, LLM calls client tools only
  - Handling: pass tool-call information to the client
  - End condition: yes; multi-turn ends

- **N4: Mixed calls**
  - Scenario: mixed tools after merge, LLM calls both server and client tools
  - Handling: drop server tool calls; pass through client tool calls only
  - End condition: yes; multi-turn ends

## Special Cases

### Maximum Call Limit Reached
- **Scenario**: consecutive LLM calls reach the limit (default 14) while continuing in the server-only tool branch
- **Handling**: force termination and return the current response
- **End condition**: yes; multi-turn ends

### Tool Execution Failure
- **Scenario**: server-side tool execution fails
- **Handling**: return an error and terminate the dialogue
- **End condition**: yes; multi-turn ends
