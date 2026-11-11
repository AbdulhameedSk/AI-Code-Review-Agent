"""
core.py — the agent loop, production edition.

Same while-loop as before, now with the thing every agent needs in prod:
OBSERVABILITY. Every API call returns usage stats — we capture input/output
tokens, accumulate cost, and hand it back so callers can trace the run.
"""
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
# USD per million tokens (Sonnet pricing — update if you change MODEL).
PRICE_IN, PRICE_OUT = 3.0, 15.0


def make_client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — put it in .env")
    return anthropic.Anthropic(api_key=key)


class RunStats:
    """Token + cost accumulator for one agent run."""
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0

    @property
    def cost_usd(self) -> float:
        return (self.input_tokens * PRICE_IN
                + self.output_tokens * PRICE_OUT) / 1_000_000


def run_agent(system: str, tools: list, dispatch, task: str,
              on_event=None, max_steps: int = 20):
    """Run one agent to completion.

    Returns (text, stats, tool_calls_log) — the caller (trace.py) persists
    the log so every run is auditable.
    """
    client = make_client()
    messages = [{"role": "user", "content": task}]
    stats = RunStats()
    tool_log = []
    final_texts = []

    def emit(kind, data=None):
        if on_event:
            on_event(kind, data)

    for _ in range(max_steps):
        kwargs = {"model": MODEL, "max_tokens": 4096,
                  "system": system, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)

        stats.api_calls += 1
        stats.input_tokens += resp.usage.input_tokens
        stats.output_tokens += resp.usage.output_tokens
        messages.append({"role": "assistant", "content": resp.content})

        tool_results = []
        for block in resp.content:
            if block.type == "text":
                final_texts.append(block.text)
                emit("text", block.text)
            elif block.type == "tool_use":
                emit("tool_call", (block.name, block.input))
                result = dispatch(block.name, block.input)
                emit("tool_result", result)
                tool_log.append({"tool": block.name,
                                 "input": block.input,
                                 "result": result[:2000]})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if resp.stop_reason == "end_turn" or not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})

    return "\n".join(final_texts), stats, tool_log
