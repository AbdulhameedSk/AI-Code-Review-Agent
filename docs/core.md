# core.py — the agent loop

## Why it exists

An LLM can only output text. It can't read files, call APIs, or run code.
An "agent" is what happens when you give the LLM a menu of tools and loop:

1. Send the conversation + tool descriptions to Claude.
2. Claude replies with either normal text (it's done) or a request like
   `{"name": "get_diff", "input": {"filename": "app.py"}}`.
3. Your code executes that request and appends the result as a message.
4. Loop until Claude answers in plain text.

`run_agent()` is that loop, parameterized so different agents (reviewer,
future security reviewer, etc.) can share it.

## How it works, line by line

- **`RunStats`** — accumulates `input_tokens`/`output_tokens` from every API
  response (`resp.usage`). `cost_usd` multiplies by per-token pricing. Why:
  agents burn money silently; you want cost per run, always.

- **`messages` list** — the entire "memory." Each loop iteration appends the
  assistant's reply and the tool results. The whole list is resent every
  call — that's how the model "remembers" anything.

- **`kwargs` built conditionally** — `tools` is only added when non-empty.
  An agent with no tools is just a chat; the API rejects an empty tool list.

- **Content blocks** — a response is a list of blocks: `text` blocks and
  `tool_use` blocks. We emit text to the UI, execute `tool_use` via
  `dispatch()`, and collect `tool_result` blocks.

- **`stop_reason == "end_turn"`** — Claude's way of saying "I'm done, no more
  tools needed." That's the exit condition.

- **Tool results go back as a `user` message** — this is the part that
  surprises people. Results aren't returned to the model through a special
  channel; they're just appended to the conversation and resent.

- **`max_steps`** — a hard cap. If the agent loops forever (it happens),
  you stop burning tokens.

## Return value

`(text, stats, tool_log)` — the text is what the model said, `stats` is
token/cost, `tool_log` is an audit trail that `trace.py` persists.
