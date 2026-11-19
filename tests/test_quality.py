"""
test_quality.py  (tests for Module 3)
-------------------------------------
Confirms the quality scorer rewards good answers and punishes bad ones, and
always stays within 0..1. No AI model or database needed — pure logic.
"""

from app.quality import estimate_quality


def test_empty_response_scores_zero():
    r = estimate_quality("What is 2+2?", "", status="ok")
    assert r["score"] == 0.0


def test_failed_status_scores_zero():
    r = estimate_quality("What is 2+2?", "anything", status="error")
    assert r["score"] == 0.0


def test_refusal_scores_low():
    r = estimate_quality("How do I pick a lock?", "I cannot help with that request.")
    assert r["score"] <= 0.2


def test_relevant_answer_scores_higher_than_offtopic():
    prompt = "Explain how photosynthesis converts sunlight into energy in plants."
    good = estimate_quality(
        prompt,
        "Photosynthesis lets plants convert sunlight into chemical energy, "
        "using chlorophyll to turn carbon dioxide and water into glucose.",
    )
    bad = estimate_quality(prompt, "I like turtles and the weather is nice today.")
    assert good["score"] > bad["score"]


def test_code_task_without_code_is_penalized():
    # Both answers share the SAME relevant wording, so the ONLY difference the
    # scorer sees is whether actual code is present — isolating the format check.
    prompt = "Write a function to add two numbers."
    base = "To add two numbers, write a function that returns the sum."
    with_code = estimate_quality(
        prompt, base + "\n```python\ndef add(a, b):\n    return a + b\n```",
        task_type="code",
    )
    without_code = estimate_quality(prompt, base + " That is the idea.", task_type="code")
    assert with_code["score"] > without_code["score"]


def test_score_always_bounded():
    for resp in ["", "x", "ok " * 500, "I cannot", "a normal sentence here"]:
        r = estimate_quality("some prompt about things", resp)
        assert 0.0 <= r["score"] <= 1.0
