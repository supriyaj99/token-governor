"""
quality.py  (Module 3 — the quality estimator, a.k.a. "Module 0")
-----------------------------------------------------------------
This is the most important idea in the whole system.

The router's job (Module 4) is to pick the CHEAPEST model that is still GOOD
ENOUGH. But "good enough" is meaningless unless we can measure quality. The
catch: we can't afford to ask a big, expensive AI model to grade every single
response — that would cost more than the money we're trying to save.

So this module produces a CHEAP, FAST quality score (0.0 .. 1.0) for each
response using simple, explainable signals computed in plain Python — no AI
call, no API key, basically free. These are called "implicit signals":

  - Did the model actually answer, or refuse / return nothing?
  - Is the answer a sensible length (not empty, not a one-word dodge)?
  - For code/extraction tasks, does the output contain code / valid-looking JSON?
  - Is the answer ON TOPIC (does it share meaningful words with the question)?
  - Is it free of obvious broken-record repetition?

VERSION NOTE (good interview material): this heuristic scorer is v1. The planned
upgrades, in order, are: (2) train a small scorer model on a few thousand labels,
and (3) send a small SAMPLE of responses to a real LLM judge to keep the cheap
scorer honest. Cheap-scorer-for-everything + expensive-judge-for-a-sample is the
standard way production systems get a quality signal without going broke.
"""

import json
import re
from typing import Dict, List, Optional

# Phrases that usually mean the model dodged or failed to help.
_REFUSAL_HINTS = (
    "i cannot", "i can't help", "i am unable", "i'm unable",
    "as an ai", "i do not have the ability", "sorry, but i can",
)

# Very common English words we ignore when checking if the answer is on-topic.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "is", "are", "was",
    "were", "to", "of", "in", "on", "for", "with", "as", "by", "at", "it",
    "this", "that", "these", "those", "be", "can", "will", "would", "should",
    "i", "you", "he", "she", "they", "we", "what", "why", "how", "do", "does",
}


def _words(text: str) -> set:
    """Lowercase the text, keep only real words, drop stopwords."""
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _relevance(prompt_text: str, response_text: str) -> float:
    """
    How on-topic is the answer? We measure how many meaningful words from the
    prompt also appear in the response (a cheap proxy for relevance). Returns
    0.0 (nothing in common) .. 1.0 (answer covers all the prompt's key words).
    """
    p = _words(prompt_text)
    r = _words(response_text)
    if not p:
        return 1.0  # no meaningful words to match against; don't penalize
    overlap = len(p & r) / len(p)
    return round(min(overlap, 1.0), 3)


def _has_heavy_repetition(text: str) -> bool:
    """Flag broken-record output: the same 3-word phrase repeated many times."""
    words = text.lower().split()
    if len(words) < 12:
        return False
    trigrams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
    if not trigrams:
        return False
    most_common = max(trigrams.count(t) for t in set(trigrams))
    return most_common >= 4


def _looks_like_json(text: str) -> bool:
    """True if any {...} chunk in the text parses as valid JSON."""
    for match in re.findall(r"\{.*?\}", text, re.DOTALL):
        try:
            json.loads(match)
            return True
        except Exception:
            continue
    return False


def estimate_quality(
    prompt_text: str,
    response_text: str,
    task_type: Optional[str] = None,
    status: str = "ok",
) -> Dict:
    """
    Return {"score": 0..1, "reasons": [...]} describing the response's quality.

    The score starts from the relevance of the answer, then we apply penalties
    for clear problems (empty, refusal, repetition) and a small bonus/penalty
    for format correctness on code/extraction tasks. Everything is bounded to
    stay within 0..1 and every decision is recorded in "reasons" so the score
    is fully explainable — never a black box.
    """
    reasons = []

    # A failed call or an empty answer is quality 0, full stop.
    if status != "ok" or not response_text or not response_text.strip():
        return {"score": 0.0, "reasons": ["empty_or_failed_response"]}

    # Refusals are near-useless for most requests.
    lowered = response_text.lower()
    if any(h in lowered for h in _REFUSAL_HINTS):
        return {"score": 0.1, "reasons": ["looks_like_refusal"]}

    # Start from relevance (on-topic-ness).
    score = _relevance(prompt_text, response_text)
    reasons.append(f"relevance={score}")

    # Length sanity: extremely short answers are usually low quality.
    if len(response_text.strip()) < 15:
        score -= 0.3
        reasons.append("very_short_answer(-0.3)")

    # Repetition is a strong bad sign.
    if _has_heavy_repetition(response_text):
        score -= 0.3
        reasons.append("heavy_repetition(-0.3)")

    # Format checks for tasks that imply a structure.
    if task_type == "code":
        if "```" in response_text or re.search(r"[(){}=;]", response_text):
            score += 0.1
            reasons.append("contains_code(+0.1)")
        else:
            score -= 0.2
            reasons.append("code_task_no_code(-0.2)")
    elif task_type == "extraction":
        if _looks_like_json(response_text):
            score += 0.1
            reasons.append("valid_json(+0.1)")
        else:
            score -= 0.1
            reasons.append("extraction_no_json(-0.1)")

    # Clamp to the valid range.
    score = round(max(0.0, min(score, 1.0)), 3)
    return {"score": score, "reasons": reasons}
