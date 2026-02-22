import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.getcwd(), "data", "dondet.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS system_prompt (id INTEGER PRIMARY KEY, content TEXT)")
    cur.execute("INSERT OR IGNORE INTO system_prompt(id, content) VALUES(1, 'You are a helpful assistant.')")
    cur.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER,
        role TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        source_path TEXT,
        size_bytes INTEGER,
        page_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS doc_texts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        text TEXT
    )""")
    conn.commit()
    conn.close()

def get_system_prompt() -> str:
    conn = get_conn()
    cur = conn.cursor()
    r = cur.execute("SELECT content FROM system_prompt WHERE id=1").fetchone()
    conn.close()
    return r["content"] if r else ""

def set_system_prompt(content: str):
    conn = get_conn()
    conn.execute("UPDATE system_prompt SET content=? WHERE id=1", (content,))
    conn.commit()
    conn.close()

def new_conversation(title: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations(title) VALUES(?)", (title,))
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return cid

def list_conversations() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT id, title, created_at FROM conversations ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_conversation(conversation_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
    conn.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
    conn.commit()
    conn.close()

def add_message(conversation_id: int, role: str, content: str):
    conn = get_conn()
    conn.execute("INSERT INTO messages(conversation_id, role, content) VALUES(?,?,?)", (conversation_id, role, content))
    conn.commit()
    conn.close()

def get_messages(conversation_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id ASC", (conversation_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_document(filename: str, source_path: str, size_bytes: int, text: str, page_count: int = 1) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO documents(filename, source_path, size_bytes, page_count, status) VALUES(?,?,?,?,?)", (filename, source_path, size_bytes, page_count, "pending"))
    doc_id = cur.lastrowid
    cur.execute("INSERT INTO doc_texts(document_id, text) VALUES(?,?)", (doc_id, text))
    conn.commit()
    conn.close()
    return doc_id

def get_document_text(document_id: int) -> Optional[str]:
    conn = get_conn()
    r = conn.execute("SELECT text FROM doc_texts WHERE document_id=?", (document_id,)).fetchone()
    conn.close()
    return r["text"] if r else None

def list_documents() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT id, filename, size_bytes, page_count, status, created_at FROM documents ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_document(document_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
    conn.execute("DELETE FROM doc_texts WHERE document_id=?", (document_id,))
    conn.commit()
    conn.close()

def update_document_status(doc_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE documents SET status=? WHERE id=?", (status, doc_id))
    conn.commit()
    conn.close()
