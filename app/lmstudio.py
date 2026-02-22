import os
import httpx
from typing import List, Dict, Any, Optional

LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://127.0.0.1:1234")
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "liquid/lfm2-1.2b")

class LMStudioClient:
    def __init__(self, base_url: str = LMSTUDIO_URL, model: str = LMSTUDIO_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=60, headers={"Authorization": "Bearer lm-studio"})

    def set_api_key(self, api_key: str):
        self._client.headers["Authorization"] = f"Bearer {api_key}"

    async def embeddings(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/v1/embeddings"
        payload = {"model": self.model, "input": texts}
        try:
            r = await self._client.post(url, json=payload)
            if r.status_code != 200:
                print(f"Embedding error {r.status_code}: {r.text}")
                return [[0.0] * 384 for _ in texts]
            data = r.json()
            return [item["embedding"] for item in data.get("data", [])]
        except Exception as e:
            print(f"Embedding exception: {e}")
            return [[0.0] * 384 for _ in texts]

    async def score_pairs(self, query: str, passages: List[str]) -> List[float]:
        url = f"{self.base_url}/v1/chat/completions"
        scores = []
        for p in passages:
            try:
                r = await self._client.post(url, json={"model": self.model, "messages": [
                    {"role": "system", "content": "Return a single number 0-1 for relevance."},
                    {"role": "user", "content": f"Query: {query}\nPassage: {p}\nScore:"},
                ], "temperature": 0})
                if r.status_code != 200:
                    print(f"Scoring error {r.status_code}: {r.text}")
                    scores.append(0.0)
                    continue
                txt = r.json()["choices"][0]["message"]["content"].strip()
                try:
                    scores.append(float(txt.split()[0]))
                except:
                    scores.append(0.0)
            except Exception as e:
                print(f"Scoring exception: {e}")
                scores.append(0.0)
        return scores

    async def generate(self, system_prompt: str, conversation: List[Dict[str, str]]) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        messages = [{"role": "system", "content": system_prompt}] + conversation
        try:
            r = await self._client.post(url, json={"model": self.model, "messages": messages, "temperature": 0.2})
            if r.status_code != 200:
                print(f"Generate error {r.status_code}: {r.text}")
                return f"Error: {r.status_code} {r.text}"
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Generate exception: {e}")
            return f"Error: {e}"
