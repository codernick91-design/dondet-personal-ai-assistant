import os
import httpx
import json
from typing import List, Dict, Any, Optional

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=120)

    def set_api_key(self, api_key: str):
        # Ollama usually doesn't need API key for local, but if behind proxy/auth, might need header
        pass

    async def embeddings(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/api/embeddings"
        embeddings = []
        for text in texts:
            payload = {"model": self.model, "prompt": text}
            try:
                r = await self._client.post(url, json=payload)
                if r.status_code != 200:
                    print(f"Embedding error {r.status_code}: {r.text}")
                    embeddings.append([0.0] * 384) # Fallback dimension, might be different for Llama/Qwen
                    continue
                data = r.json()
                embeddings.append(data.get("embedding", []))
            except Exception as e:
                print(f"Embedding exception: {e}")
                embeddings.append([0.0] * 384)
        return embeddings

    async def score_pairs(self, query: str, passages: List[str]) -> List[float]:
        # Ollama doesn't have native scoring/reranking endpoint easily accessible like this
        # We simulate with chat completion
        url = f"{self.base_url}/api/chat"
        scores = []
        for p in passages:
            try:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a relevance scorer. Return only a number between 0.0 and 1.0 indicating how relevant the passage is to the query."},
                        {"role": "user", "content": f"Query: {query}\nPassage: {p}\nScore:"}
                    ],
                    "stream": False,
                    "options": {"temperature": 0.0}
                }
                r = await self._client.post(url, json=payload)
                if r.status_code != 200:
                    scores.append(0.0)
                    continue
                content = r.json()["message"]["content"].strip()
                try:
                    # Extract float from string like "0.8" or "The score is 0.8"
                    import re
                    match = re.search(r"0\.\d+|1\.0|0|1", content)
                    if match:
                        scores.append(float(match.group()))
                    else:
                        scores.append(0.0)
                except:
                    scores.append(0.0)
            except Exception as e:
                print(f"Scoring exception: {e}")
                scores.append(0.0)
        return scores

    async def generate(self, system_prompt: str, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        messages = [{"role": "system", "content": system_prompt}] + conversation
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        try:
            r = await self._client.post(url, json=payload)
            if r.status_code != 200:
                return {"content": f"Error: {r.status_code} {r.text}", "usage": {}}
            data = r.json()
            return {
                "content": data["message"]["content"],
                "usage": {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                }
            }
        except Exception as e:
            return {"content": f"Error: {e}", "usage": {}}

    async def stream_generate(
        self, 
        system_prompt: str, 
        conversation: List[Dict[str, str]],
        **kwargs # Accept extra args but ignore them or pass selectively if needed
    ):
        url = f"{self.base_url}/api/chat"
        messages = [{"role": "system", "content": system_prompt}] + conversation
        
        # We rely on Modelfile for parameters, so we send empty options or minimal ones
        # User requested: "don't send any other pamarameters which should be fixed when created"
        # So we remove explicit options here.
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            # "options": {} # Empty options to let Modelfile defaults take over
        }
        
        # Prepare logging
        import datetime
        import time
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(os.getcwd(), "logs", "ollama")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"chat_{timestamp}.json")
        
        full_response = ""
        start_time = time.time()
        
        try:
            async with self._client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield {"error": f"Error {response.status_code}"}
                    return

                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        data = json.loads(line)
                        if data.get("done"):
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            # Final chunk stats
                            usage = {
                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                "completion_tokens": data.get("eval_count", 0),
                                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                            }
                            yield {"usage": usage}
                            
                            # Save log
                            log_entry = {
                                "timestamp": timestamp,
                                "duration_seconds": duration,
                                "model": self.model,
                                "messages": messages,
                                "response": full_response,
                                "usage": usage,
                                "raw_final_data": data
                            }
                            
                            with open(log_file, "w", encoding="utf-8") as f:
                                json.dump(log_entry, f, indent=2, ensure_ascii=False)
                                
                            break
                        
                        content = data.get("message", {}).get("content", "")
                        if content:
                            full_response += content
                            yield {"content": content}
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
             print(f"Stream generate exception: {e}")
             yield {"error": str(e)}
