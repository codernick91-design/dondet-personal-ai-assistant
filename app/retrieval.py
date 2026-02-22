from typing import List, Dict, Any
import asyncio
import time
from app.store import VectorStore
from app.search import BM25Index
from app.ollama_client import OllamaClient
from sentence_transformers import CrossEncoder

def rrf_merge(a: List[Dict[str, Any]], b: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    ranks = {}
    def add(list_items):
        for idx, item in enumerate(list_items):
            key = item["text"]
            ranks[key] = ranks.get(key, 0) + 1.0 / (60 + idx + 1)
    add(a)
    add(b)
    merged = []
    for t, s in ranks.items():
        merged.append({"text": t, "score": s})
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:k]

class Retriever:
    def __init__(self, store: VectorStore, bm25: BM25Index, lm: OllamaClient):
        self.store = store
        self.bm25 = bm25
        self.lm = lm
        # Load local small cross-encoder model
        try:
            self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        except:
            print("Failed to load local cross-encoder, using fallback")
            self.cross_encoder = None

    async def retrieve(self, query: str, top_k: int = 50) -> Dict[str, Any]:
        t0 = time.time()
        vs = await self.store.query([query], top_k)
        t1 = time.time()
        ks = self.bm25.query(query, top_k)
        t2 = time.time()
        
        # Merge results using Reciprocal Rank Fusion
        merged = rrf_merge(vs, ks, top_k)
        
        # Extract passages
        all_passages = [m["text"] for m in merged]
        
        rerank_candidates = all_passages[:20]
        
        # scored_pairs = []
        # if self.cross_encoder:
        #     # Use local cross-encoder
        #     pairs = [[query, p] for p in rerank_candidates]
        #     # predict is blocking, but fast enough for 20 pairs
        #     scores = self.cross_encoder.predict(pairs)
        #     scored_pairs = [{"text": rerank_candidates[i], "score": float(scores[i])} for i in range(len(rerank_candidates))]
        # else:
        #     # Fallback to LM Studio scoring (slower)
        #     scores = await self.lm.score_pairs(query, rerank_candidates)
        #     scored_pairs = [{"text": rerank_candidates[i], "score": scores[i]} for i in range(len(rerank_candidates))]
            
        # # Sort by relevance score
        # scored_pairs.sort(key=lambda x: x["score"], reverse=True)
        
        # # Filter by relevance threshold (> -2.0 for ms-marco-MiniLM-L-6-v2)
        # filtered = [p for p in scored_pairs if p["score"] > -2.0]
        
        t3 = time.time()
        
        # Return results in the expected format
        # results should be a list of dicts with "text"
        final_results = [{"text": t} for t in rerank_candidates[:5]]
        
        logs = {
            "vector_count": len(vs),
            "vector_time": t1 - t0,
            "bm25_count": len(ks),
            "bm25_time": t2 - t1,
            "rerank_count": len(rerank_candidates),
            "rerank_time": t3 - t2,
            "final_count": len(final_results),
            "top_scores": [m["score"] for m in merged[:5]] if merged else []
        }
        
        return {
            "results": final_results,
            "logs": logs
        }

    # make no sense because chunks small enough 
    async def compress(self, query: str, passages: List[str], max_bytes: int = 10_000_000) -> List[str]:
        # We calculate total size roughly
        total_text = "\n".join(passages)
        if len(total_text.encode('utf-8')) < max_bytes:
            return passages
            
        # If huge, we do compression (simple selection for now or re-scoring)
        # Since we already ranked them, we just take top N that fit
        out = []
        current_bytes = 0
        for p in passages:
            pb = len(p.encode('utf-8'))
            if current_bytes + pb < max_bytes:
                out.append(p)
                current_bytes += pb
            else:
                break
        return out
