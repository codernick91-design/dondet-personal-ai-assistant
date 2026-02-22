import os
import pickle
import numpy as np
import faiss
import asyncio
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

# Storage paths
DATA_DIR = os.path.join(os.getcwd(), "data")
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss_index.bin")
CHUNKS_DATA_PATH = os.path.join(DATA_DIR, "chunks_data.pkl")

class VectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Load local embedding model
        print(f"Loading embedding model: {model_name}...")
        self.encoder = SentenceTransformer(model_name)
        
        # Load or initialize FAISS index
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(CHUNKS_DATA_PATH):
            print("Loading FAISS index and data...")
            self.index = faiss.read_index(FAISS_INDEX_PATH)
            with open(CHUNKS_DATA_PATH, "rb") as f:
                self.chunks_data = pickle.load(f)
        else:
            print("Initializing new FAISS index...")
            # Dimension of all-MiniLM-L6-v2 is 384
            self.dimension = 384
            self.index = faiss.IndexFlatIP(self.dimension) # Inner Product (Cosine Similarity if normalized)
            self.chunks_data = [] # List of {"id": str, "text": str, "metadata": dict}

    async def add(self, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]]):
        # Compute embeddings in a thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None, 
            lambda: self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        )
        
        # Add to FAISS (faiss operations are usually fast enough for CPU index, but adding can be wrapped if needed)
        self.index.add(embeddings)
        
        # Store metadata
        # The index in chunks_data corresponds to the FAISS ID
        for i, text in enumerate(texts):
            self.chunks_data.append({
                "id": ids[i],
                "text": text,
                "metadata": metadatas[i]
            })
            
        # Persist to disk
        self._save()

    async def query(self, query_texts: List[str], top_k: int) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
            
        # Encode query in thread pool
        loop = asyncio.get_running_loop()
        query_embeddings = await loop.run_in_executor(
            None,
            lambda: self.encoder.encode(query_texts, convert_to_numpy=True, normalize_embeddings=True)
        )
        
        # Search
        # D: distances, I: indices
        D, I = self.index.search(query_embeddings, top_k)
        
        out = []
        # We only handle the first query in the list as per current usage
        indices = I[0]
        distances = D[0]
        
        for i, idx in enumerate(indices):
            if idx == -1: continue # No result found
            
            chunk = self.chunks_data[idx]
            out.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "distance": float(distances[i])
            })
            
        return out

    def _save(self):
        faiss.write_index(self.index, FAISS_INDEX_PATH)
        with open(CHUNKS_DATA_PATH, "wb") as f:
            pickle.dump(self.chunks_data, f)
