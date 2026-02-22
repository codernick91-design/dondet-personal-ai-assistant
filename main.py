import os
import time

# Set China/CST Timezone and Hugging Face Mirror
os.environ["TZ"] = "Asia/Shanghai"
try:
    time.tzset()
except AttributeError:
    pass  # Windows might not support tzset

# Set HF Mirror for faster model downloads in China
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import aiofiles
import json
from app.db import init_db, get_system_prompt, set_system_prompt, new_conversation, list_conversations, add_message, get_messages, add_document, list_documents, get_document_text, delete_document, update_document_status, delete_conversation
from app.ingest import read_txt, read_pdf, read_md, chunk_text
from app.store import VectorStore
from app.search import BM25Index
from app.retrieval import Retriever
from app.ollama_client import OllamaClient
import sqlite3

DATA_DIR = os.path.join(os.getcwd(), "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

init_db()
lm = OllamaClient()
vs = VectorStore()
bm25 = BM25Index()
retriever = Retriever(vs, bm25, lm)

def rebuild_bm25():
    docs = list_documents()
    texts = []
    metas = []
    for d in docs:
        t = get_document_text(d["id"])
        if t:
            texts.append(t)
            metas.append({"document_id": d["id"], "source": d["filename"]})
    bm25.rebuild(texts, metas)

rebuild_bm25()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

async def generate_title(conversation_id: int):
    msgs = get_messages(conversation_id)
    if not msgs:
        return
    # Use the first user message or a summary
    first_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
    if not first_msg:
        return
        
    prompt = f"Summarize the following user query into a short title (max 10 words). Return ONLY the title.\n\nQuery: {first_msg}\nTitle:"
    try:
        title = await lm.generate("You are a helpful assistant.", [{"role": "user", "content": prompt}])
        title = title["content"].strip().strip('"').strip("'")
        if title:
            conn = sqlite3.connect(os.path.join(DATA_DIR, "dondet.db"))
            conn.execute("UPDATE conversations SET title=? WHERE id=?", (title, conversation_id))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Title generation failed: {e}")

@app.get("/")
async def index():
    path = os.path.join("static", "index.html")
    return FileResponse(path)

@app.get("/api/system_prompt")
async def api_get_system_prompt():
    return {"content": get_system_prompt()}

@app.post("/api/system_prompt")
async def api_set_system_prompt(content: str = Form(...)):
    set_system_prompt(content)
    return {"ok": True}

@app.get("/api/conversations")
async def api_list_conversations():
    return list_conversations()

@app.post("/api/conversations")
async def api_new_conversation(title: str = Form("New Conversation")):
    cid = new_conversation(title)
    return {"id": cid}

@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(conversation_id: int):
    delete_conversation(conversation_id)
    return {"ok": True}

@app.get("/api/conversations/{conversation_id}")
async def api_get_conversation(conversation_id: int):
    return get_messages(conversation_id)

@app.get("/api/documents")
async def api_list_documents():
    return list_documents()

@app.get("/api/documents/{document_id}/read")
async def api_read_document(document_id: int):
    t = get_document_text(document_id)
    return {"text": t or ""}

@app.delete("/api/documents/{document_id}")
async def api_delete_document(document_id: int):
    delete_document(document_id)
    rebuild_bm25()
    return {"ok": True}

@app.post("/api/documents/upload")
async def api_upload_document(file: UploadFile = File(...)):
    fn = file.filename
    dest = os.path.join(DOCS_DIR, fn)
    async with aiofiles.open(dest, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await f.write(chunk)
    size = os.path.getsize(dest)
    if fn.lower().endswith(".pdf"):
        text, pages = read_pdf(dest)
    elif fn.lower().endswith(".md") or fn.lower().endswith(".markdown"):
        text, pages = read_md(dest)
    else:
        text, pages = read_txt(dest)
        
    
    # Store parsed text with status 'parsed'
    doc_id = add_document(fn, dest, size, text, pages)
    update_document_status(doc_id, "parsed")

    tokens = len(text.split())
    # Intelligent chunking
    chunks = chunk_text(text, 300, 600, 60)
    
    ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
    metas = [{"document_id": doc_id, "chunk_id": i, "source": fn} for i in range(len(chunks))]
    
    await vs.add(ids, chunks, metas)
    bm25.add_many([text], [{"document_id": doc_id, "source": fn}])
    
    update_document_status(doc_id, "vectorized")
    
    return {"id": doc_id, "chunks": len(chunks), "pages": pages, "status": "vectorized"}

from collections import OrderedDict

# LRU Cache for Conversation History
class ConversationCache:
    def __init__(self, capacity: int = 10):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, conv_id: int):
        if conv_id not in self.cache:
            return None
        self.cache.move_to_end(conv_id)
        return self.cache[conv_id]

    def put(self, conv_id: int, messages: list):
        if conv_id in self.cache:
            self.cache.move_to_end(conv_id)
        self.cache[conv_id] = messages
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
            
    def append(self, conv_id: int, role: str, content: str):
        if conv_id in self.cache:
            self.cache[conv_id].append({"role": role, "content": content})
            self.cache.move_to_end(conv_id)

conv_cache = ConversationCache(10)

@app.post("/query")
async def api_query(conversation_id: int = Form(...), query: str = Form(...), system_prompt: Optional[str] = Form(None), api_key: Optional[str] = Form(None)):

    async def response_stream():
        try:
            sys_p = system_prompt or get_system_prompt()
            if api_key:
                lm.set_api_key(api_key)

            # Get history from cache or DB
            history = conv_cache.get(conversation_id)
            if history is None:
                history = get_messages(conversation_id)
                conv_cache.put(conversation_id, history)
            
            # Retrieve context
            # User wants "most up to 3 related chunks", "directly combine system prompt with user query"
            # "don't compress", "don't separate user or assistant to ai model"
            
            retrieval_result = await retriever.retrieve(query, 10)
            top = retrieval_result["results"]
            logs = retrieval_result["logs"]
            
            # Take top 3 directly
            top_chunks = [t["text"] for t in top[:3]]
            
            yield json.dumps({"status": "retrieval_done", "logs": logs}) + "\n"
            yield json.dumps({"status": "reasoning_start"}) + "\n"

            # Construct LLM input: System + History + (Context + Query)
            llm_messages = []
            
            # History (Last 5 turns = 10 messages)
            recent_history = history[-4:] if history else []
            for msg in recent_history:
                llm_messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Context + Current Query
            if top_chunks:
                final_content = "Context:\n" + "\n---\n".join(top_chunks) + "\n\nQuery: " + query
            else:
                final_content = query
                
            llm_messages.append({"role": "user", "content": final_content})
            
            # Generate response
            resp_content = ""
            usage = {}
            
            # Stream generation
            # stream_generate takes (system_prompt, conversation_list)
            async for chunk in lm.stream_generate(sys_p, llm_messages): 
                 
                if "error" in chunk:
                     print(f"Stream error chunk: {chunk['error']}")
                     continue
                
                if "content" in chunk:
                    text_chunk = chunk["content"]
                    if text_chunk:
                        resp_content += text_chunk
                        yield json.dumps({"status": "chunk", "content": text_chunk}) + "\n"
                
                if "usage" in chunk:
                    usage = chunk["usage"]
               
            # Persist
            add_message(conversation_id, "user", query)
            add_message(conversation_id, "assistant", resp_content)
            
            # Update cache with raw messages
            if history is not None:
                conv_cache.append(conversation_id, "user", query)
                conv_cache.append(conversation_id, "assistant", resp_content)
            
            # Trigger title generation if this is the first few messages
            if len(history) <= 2:
                # We can't use background_tasks in StreamingResponse generator easily without passing it in
                # Just call it asynchronously without awaiting? No, 'await' is needed for async functions usually.
                # But we can create a task.
                import asyncio
                asyncio.create_task(generate_title(conversation_id))
                
            # Emit final response
            yield json.dumps({"status": "done", "response": resp_content, "cost_summary": usage}) + "\n"
        except Exception as e:
            print(f"Stream error: {e}")
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"

    return StreamingResponse(response_stream(), media_type="application/x-ndjson")
