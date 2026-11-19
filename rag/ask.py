"""
ask.py  — ask one RAG question through the governed gateway
-----------------------------------------------------------
Run (with the gateway server running) from the project root:
    python -m rag.ask "What is Acme's return policy?"

It retrieves the most relevant facts, builds a grounded prompt, sends it to the
gateway with model "auto" (so the router picks the model), and prints the answer
plus which tier was used and what it cost. Uses only Python's standard library.
"""

import json
import sys
import urllib.request

from rag.corpus import DOCUMENTS
from rag.retriever import TfidfRetriever, build_augmented_messages

GATEWAY_URL = "http://localhost:8000/v1/chat/completions"


def ask(question: str, identity: str = "support-team") -> dict:
    retriever = TfidfRetriever(DOCUMENTS)
    messages, hits = build_augmented_messages(question, retriever, top_k=2)

    payload = json.dumps({
        "model": "auto",          # let the router choose the model
        "identity": identity,
        "messages": messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        GATEWAY_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    print(f"Q: {question}")
    print(f"Retrieved facts from: {[doc['id'] for doc, _ in hits]}")
    print(f"Router chose model: {result['model']}  (quality={result['quality']}, "
          f"cost=${result['cost_usd']:.6f})")
    print(f"A: {result['content']}")
    return result


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What is Acme's return policy?"
    ask(q)
