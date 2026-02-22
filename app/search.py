from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import re

class BM25Index:
    def __init__(self):
        self.docs: List[str] = []
        self.doc_meta: List[Dict[str, Any]] = []
        self.tokenized: List[List[str]] = []
        self.bm25 = None

    def rebuild(self, texts: List[str], metas: List[Dict[str, Any]]):
        self.docs = texts
        self.doc_meta = metas
        self.tokenized = [self._tokenize(d) for d in texts]
        self.bm25 = BM25Okapi(self.tokenized) if self.tokenized else None

    def add_many(self, texts: List[str], metas: List[Dict[str, Any]]):
        self.docs.extend(texts)
        self.doc_meta.extend(metas)
        toks = [self._tokenize(d) for d in texts]
        self.tokenized.extend(toks)
        self.bm25 = BM25Okapi(self.tokenized) if self.tokenized else None

    def query(self, q: str, top_k: int) -> List[Dict[str, Any]]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(self._tokenize(q))
        pairs = [{"text": self.docs[i], "metadata": self.doc_meta[i], "score": float(scores[i])} for i in range(len(self.docs))]
        pairs.sort(key=lambda x: x["score"], reverse=True)
        return pairs[:top_k]

    def _tokenize(self, t: str) -> List[str]:
        return re.findall(r"\w+", t.lower())
