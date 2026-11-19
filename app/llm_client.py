"""
llm_client.py
-------------
This is the piece that actually talks to an AI model — or pretends to, when
we're in mock mode.

Why a separate file? Because the rest of the gateway shouldn't care WHICH
provider we call. It just says "call this model with these messages" and gets
back {reply, prompt_tokens, completion_tokens}. Today we support a free mock
model and (via the LiteLLM library) real providers like OpenAI and Anthropic.
LiteLLM gives one uniform way to call 100+ models, so we don't write separate
code per provider.
"""

from typing import Dict, List

from app.config import MOCK_MODE


def _estimate_tokens(text: str) -> int:
    """
    A rough token count for mock mode (no API, no exact tokenizer needed).

    A common rule of thumb: ~4 characters of English ≈ 1 token. We use that to
    produce a believable number so the cost/logging pipeline has real data to
    record during testing. Real calls (below) use the provider's EXACT counts.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def call_model(model: str, messages: List[Dict[str, str]]) -> Dict:
    """
    Send `messages` to `model` and return a normalized result dict:
        {"content": <reply text>, "prompt_tokens": int, "completion_tokens": int}

    In MOCK_MODE we skip the network entirely and echo a canned reply. This lets
    you run and test the ENTIRE system for free, with no API key.
    """
    if MOCK_MODE:
        # Combine all incoming message text to estimate the prompt size.
        prompt_text = " ".join(m.get("content", "") for m in messages)
        reply = (
            "[MOCK RESPONSE] This is a fake reply used for local testing. "
            "No real AI model was called and nothing was charged."
        )
        return {
            "content": reply,
            "prompt_tokens": _estimate_tokens(prompt_text),
            "completion_tokens": _estimate_tokens(reply),
        }

    # --- Real call path (only runs when MOCK_MODE is off) ---
    # We import litellm here, lazily, so that mock-mode users don't even need
    # the library installed to get started.
    import litellm

    response = litellm.completion(model=model, messages=messages)

    # LiteLLM returns an object shaped like OpenAI's response. We pull out the
    # reply text and the EXACT token counts the provider reported.
    content = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {}) or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))

    return {
        "content": content,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
