"""
retriever.py
------------
The "retrieval" half of RAG: given a question, find the most relevant documents
from our knowledge base.

We use TF-IDF with cosine similarity — a classic, dependency-free way to measure
how relevant a document is to a query:

  - TF (term frequency): how often a word appears in a document.
  - IDF (inverse document frequency): rare words across the whole corpus are
    more informative than common ones, so they get more weight.
  - cosine similarity: the angle between the question's word-vector and each
    document's word-vector; closer angle = more similar = more relevant.

This is implemented in pure Python (no scikit-learn needed), so it runs anywhere
with zero install pain. The natural upgrade is semantic embeddings + a vector
database (e.g. FAISS or pgvector), which captures meaning beyond exact words.
"""

import math
import re
from collections import Counter
from typing import Dict, List, Tuple


def _tokenize(text: str) -> List[str]:
    """Lowercase and split into word tokens of length >= 2."""
    return re.findall(r"[a-z0-9]{2,}", text.lower())


class TfidfRetriever:
    def __init__(self, documents: List[Dict]):
        """documents = [{"id": ..., "text": ...}, ...]"""
        self.documents = documents
        self.doc_tokens = [_tokenize(d["text"]) for d in documents]
        self.vocab_idf = self._compute_idf()
        # Precompute each document's TF-IDF vector once.
        self.doc_vectors = [self._tfidf_vector(toks) for toks in self.doc_tokens]

    def _compute_idf(self) -> Dict[str, float]:
        """How rare each word is across all documents."""
        n_docs = len(self.documents)
        df = Counter()
        for toks in self.doc_tokens:
            for term in set(toks):
                df[term] += 1
        # idf = log(total docs / docs containing term), smoothed by +1.
        return {term: math.log((1 + n_docs) / (1 + count)) + 1.0 for term, count in df.items()}

    def _tfidf_vector(self, tokens: List[str]) -> Dict[str, float]:
        """Turn a list of tokens into a {term: tf-idf weight} vector."""
        if not tokens:
            return {}
        counts = Counter(tokens)
        length = len(tokens)
        return {
            term: (count / length) * self.vocab_idf.get(term, 0.0)
            for term, count in counts.items()
        }

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors (dicts)."""
        if not a or not b:
            return 0.0
        # dot product over shared terms
        shared = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in shared)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    def search(self, query: str, top_k: int = 2) -> List[Tuple[Dict, float]]:
        """Return the top_k most relevant documents as (document, score) pairs."""
        qvec = self._tfidf_vector(_tokenize(query))
        scored = [
            (self.documents[i], self._cosine(qvec, self.doc_vectors[i]))
            for i in range(len(self.documents))
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


def build_augmented_messages(question: str, retriever: TfidfRetriever, top_k: int = 2):
    """
    The "augmented" half of RAG: build the chat messages we send to the model,
    stuffing the retrieved facts into the prompt so the answer is grounded.
    Returns an OpenAI-style messages list ready to POST to the gateway.
    """
    hits = retriever.search(question, top_k=top_k)
    context = "\n".join(f"- {doc['text']}" for doc, _ in hits)
    system = (
        "You are a helpful support assistant. Answer ONLY using the facts below. "
        "If the facts don't contain the answer, say you don't know.\n\n"
        f"Facts:\n{context}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ], hits
