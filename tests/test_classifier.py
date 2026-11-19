"""
test_classifier.py  (tests for Module 2)
----------------------------------------
These checks prove the classifier labels requests sensibly and never crashes.
The classifier uses no AI model and no database, so these tests are instant and
need no setup — a good example of testing pure logic in isolation.
"""

from app.classifier import classify


def _msg(text):
    """Helper: wrap a string as a single user message."""
    return [{"role": "user", "content": text}]


def test_detects_code():
    f = classify(_msg("Fix this:\n```python\ndef add(a, b):\n    return a+b\n```"))
    assert f["has_code"] is True
    assert f["task_type"] == "code"
    # Code tasks should carry some complexity from the code signal.
    assert f["complexity"] >= 0.25


def test_detects_simple_lookup():
    f = classify(_msg("What is the capital of France?"))
    assert f["has_code"] is False
    assert f["task_type"] == "qa"
    # A short factual question should be low complexity.
    assert f["complexity"] < 0.3


def test_detects_reasoning():
    f = classify(_msg("Explain step by step why interest rates affect inflation."))
    assert f["task_type"] == "reasoning"


def test_detects_summarization():
    f = classify(_msg("Summarize the following article in three bullet points ..."))
    assert f["task_type"] == "summarization"


def test_complexity_is_bounded():
    """Complexity must always stay between 0 and 1, even for huge inputs."""
    huge = "explain why " + ("data " * 5000)
    f = classify(_msg(huge))
    assert 0.0 <= f["complexity"] <= 1.0


def test_turn_depth_counts_messages():
    convo = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "how are you"},
    ]
    f = classify(convo)
    assert f["turn_depth"] == 3
