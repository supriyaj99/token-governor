"""
pricing.py
----------
Turns "tokens used" into "dollars spent".

Every model provider charges a price per 1,000 tokens, and charges a DIFFERENT
price for input (your prompt) vs output (the model's reply) — output is usually
more expensive. This file keeps a small price list and a function to do the math.

NOTE: prices change over time. Treat these as example/reference values and
update them from the provider's pricing page when you go live. Keeping pricing
in one small file (not scattered in the code) makes that easy.
"""

# price per 1,000 tokens, in USD: (input_price, output_price)
PRICE_PER_1K = {
    # OpenAI (example values)
    "gpt-4o": (0.0025, 0.010),
    "gpt-4o-mini": (0.00015, 0.0006),
    # Anthropic (example values)
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-5-haiku": (0.0008, 0.004),
    # Our free local test model costs nothing.
    "mock-echo": (0.0, 0.0),
}

# If we see a model we don't have a price for, fall back to this so the app
# never crashes — it just records 0 cost and we can add the price later.
DEFAULT_PRICE = (0.0, 0.0)


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Cost = (input tokens / 1000 * input price) + (output tokens / 1000 * output price).

    Example: gpt-4o-mini with 1000 input + 500 output tokens
        = (1000/1000 * 0.00015) + (500/1000 * 0.0006)
        = 0.00015 + 0.0003
        = 0.00045 dollars
    """
    input_price, output_price = PRICE_PER_1K.get(model, DEFAULT_PRICE)
    cost = (prompt_tokens / 1000.0) * input_price + (completion_tokens / 1000.0) * output_price
    return round(cost, 8)
