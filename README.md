<img width="2879" height="1650" alt="image" src="https://github.com/user-attachments/assets/58bc0d69-39d6-41d4-a3e6-b283ed5767f3" />


https://github.com/user-attachments/assets/d7c7c9d0-c2aa-40dd-8372-b842e046ade1


# Local AI Personal Assistant

A lightweight, fully local AI personal assistant with conversation memory, RAG capabilities, and performance optimizations. Runs entirely on personal machine with minimal resources.

## 🎯 Overview

**Problem**: Need a fast, private AI, safe assistant that works offline with chat history and document search.

**Solution**: Single-machine app using Vue3 frontend, SQLite+FAISS backend, and Ollama + llama3:1b for inference.

**Key Goals**:
- <5s median response time on consumer laptop
- <2GB total RAM usage  
- 100% offline, no cloud dependency

## 🚀 Features

- ✨ Real-time chat UI with streaming responses (Vue3)
- 🧠 Persistent conversation memory and title conclusion(SQLite)
- 🔍 Semantic search over your documents (FAISS + sentence-transformers)
- ⚙️ Customizable system prompts and roles
- ⚡ Performance optimized: caching, batching, context truncation
- 
## 🏗️ Architecture

┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
│ Vue3 Frontend │───▶│ Express Backend│───▶│ Ollama API │
│ (Chat UI) │ │ (SQLite+FAISS)│ │ (llama3:1b) │
└─────────────────┘ └───────────────┘ └─────────────────┘

**Flow**: Query → Retrieve context from FAISS/SQLite → Build prompt with history → Ollama → Stream response

## 📊 Performance

| Metric | Value | Hardware |
|--------|-------|----------|
| Response Time | 2.8s median | M1 Mac 16GB |
| Memory Usage | 1.6GB | Model + app |
| Context Length | 8k tokens | Auto-truncated |


