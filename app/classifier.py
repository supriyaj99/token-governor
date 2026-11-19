"""
classifier.py  (Module 2 — the request classifier)
---------------------------------------------------
Before we call any AI model, we look at the incoming request and describe it
with a few cheap, fast "features": what kind of task is it, roughly how big,
does it contain code, how complex does it look? This costs almost nothing
(no AI call) and happens in a fraction of a millisecond.

WHY this matters: the router in Module 4 can't decide "which model is cheap
enough for THIS request" unless it knows something ABOUT the request first.
This module produces that description. Think of it as the triage nurse who
sizes up each patient before deciding who they see.

VERSION NOTE (important for interviews): this is a transparent, rules-based
classifier — deliberately simple and explainable. The planned upgrade is to
train an XGBoost model on your logged data to predict task type/complexity
from many features. Starting with rules is the right first step: it works with
zero training data, and it gives the later ML model a baseline to beat.
"""

import re
from typing import Dict, List

# Words that hint a task needs step-by-step reasoning (usually the harder,
# more expensive-to-run requests).
_REASONING_HINTS = (
    "why", "explain", "prove", "derive", "step by step", "reason",
    "analyze", "compare", "trade-off", "tradeoff", "design", "architect",
)

# Words that hint the task is a short factual lookup (usually cheap/easy).
_LOOKUP_HINTS = ("what is", "who is", "when", "define", "list", "how many")

# Words that hint summarization.
_SUMMARY_HINTS = ("summarize", "summary", "tl;dr", "condense", "shorten")

# Words that hint structured extraction.
_EXTRACT_HINTS = ("extract", "parse", "json", "table", "fields", "schema")


def _looks_like_code(text: str) -> bool:
    """
    Detect whether the text contains code. We check for a few strong signals:
    triple-backtick code fences, or common programming syntax patterns.
    """
    if "```" in text:
        return True
    code_patterns = (
        r"\bdef\s+\w+\s*\(",      # python function
        r"\bclass\s+\w+",          # class definition
        r"[{};]\s*$",              # lines ending in braces/semicolons
        r"\bimport\s+\w+",         # imports
        r"</?[a-z]+>",             # html-ish tags
        r"\bSELECT\b.*\bFROM\b",  # SQL
    )
    return any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in code_patterns)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token (same rule used elsewhere)."""
    return max(1, len(text) // 4) if text else 0


def classify(messages: List[Dict[str, str]]) -> Dict:
    """
    Look at the conversation and return a dictionary of features.

    Input: messages like [{"role": "user", "content": "..."}]
    Output (example):
        {
          "task_type": "code",
          "complexity": 0.72,       # 0.0 (trivial) .. 1.0 (very complex)
          "est_prompt_tokens": 128,
          "has_code": True,
          "turn_depth": 3,
        }
    """
    # Join all message text together for analysis. We lowercase a copy for
    # keyword matching, but keep the original for code detection.
    full_text = "\n".join(m.get("content", "") for m in messages)
    lowered = full_text.lower()

    has_code = _looks_like_code(full_text)
    est_tokens = _estimate_tokens(full_text)
    turn_depth = len(messages)

    # --- Decide the task type by checking hints in priority order ---
    if has_code:
        task_type = "code"
    elif any(h in lowered for h in _SUMMARY_HINTS):
        task_type = "summarization"
    elif any(h in lowered for h in _EXTRACT_HINTS):
        task_type = "extraction"
    elif any(h in lowered for h in _REASONING_HINTS):
        task_type = "reasoning"
    elif any(h in lowered for h in _LOOKUP_HINTS):
        task_type = "qa"
    else:
        task_type = "chat"

    # --- Estimate complexity as a blend of signals, capped at 1.0 ---
    # Each factor nudges the score up. These weights are simple on purpose and
    # easy to explain; the ML upgrade would learn them from real outcomes.
    complexity = 0.0
    complexity += min(est_tokens / 2000.0, 0.5)          # longer = harder (up to +0.5)
    complexity += 0.25 if has_code else 0.0               # code is harder
    complexity += 0.15 if any(h in lowered for h in _REASONING_HINTS) else 0.0
    complexity += min(max(turn_depth - 1, 0) * 0.05, 0.2)  # deeper threads = harder
    complexity = round(min(complexity, 1.0), 3)

    return {
        "task_type": task_type,
        "complexity": complexity,
        "est_prompt_tokens": est_tokens,
        "has_code": has_code,
        "turn_depth": turn_depth,
    }
