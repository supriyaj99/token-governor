"""
seed_traffic.py  — fill the gateway with realistic demo traffic
---------------------------------------------------------------
Run (with the gateway server running) from the project root:
    python -m rag.seed_traffic 300

This sends a few hundred mixed requests through the gateway from several
different identities (teams). After running it, the /stats, /logs, /governance
endpoints and the dashboard will have real data to show — including the router
learning and the value-weighted fairness layer having something to act on.

Three identities with deliberately different behavior so Module 6 has a story:
  - support-team : lots of easy RAG questions (cheap, high quality)
  - data-science : harder reasoning requests (needs bigger models)
  - noisy-bot    : vague/low-value requests (burns budget for weak results)

Standard library only.
"""

import json
import random
import sys
import urllib.request

from rag.corpus import DOCUMENTS
from rag.retriever import TfidfRetriever, build_augmented_messages

GATEWAY_URL = "http://localhost:8000/v1/chat/completions"

SUPPORT_QUESTIONS = [
    "What is Acme's return policy?",
    "How long does standard shipping take?",
    "Does the warranty cover water damage?",
    "How much is a Pro account?",
    "What payment methods do you accept?",
    "When is customer support available?",
]

HARD_PROMPTS = [
    "Explain step by step how to design a fault-tolerant payment pipeline.",
    "Compare the trade-offs of microservices vs a monolith for our scale.",
    "Derive why our shipping costs grow non-linearly with order volume.",
]

NOISY_PROMPTS = ["hmm", "do the thing", "idk help", "???", "make it better"]


def _post(messages, identity):
    payload = json.dumps({"model": "auto", "identity": identity, "messages": messages}).encode()
    req = urllib.request.Request(GATEWAY_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main(n=300):
    retriever = TfidfRetriever(DOCUMENTS)
    rng = random.Random(0)
    sent = 0
    for _ in range(n):
        r = rng.random()
        if r < 0.5:
            q = rng.choice(SUPPORT_QUESTIONS)
            messages, _ = build_augmented_messages(q, retriever)
            _post(messages, "support-team")
        elif r < 0.8:
            messages = [{"role": "user", "content": rng.choice(HARD_PROMPTS)}]
            _post(messages, "data-science")
        else:
            messages = [{"role": "user", "content": rng.choice(NOISY_PROMPTS)}]
            _post(messages, "noisy-bot")
        sent += 1
        if sent % 50 == 0:
            print(f"  sent {sent}/{n} ...")
    print(f"Done. Sent {sent} requests. Now open /stats, /governance, or the dashboard.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
