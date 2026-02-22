import os
from typing import List, Tuple
from pypdf import PdfReader
from markdown_it import MarkdownIt
def read_txt(path: str) -> Tuple[str, int]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return text, 1

def read_pdf(path: str) -> Tuple[str, int]:
    reader = PdfReader(path)
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages), len(reader.pages)

def read_md(path: str) -> Tuple[str, int]:
    # Initialize the parser
    md = MarkdownIt()
    
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
        tokens = md.parse(text) 
        
        # Calculate the actual length (using our token proxy)
        t_count = tokenize_len(text)
        
        return text, t_count
        
    except FileNotFoundError:
        print(f"Error: The file at {path} was not found.")
        return "", 0
def tokenize_len(text: str) -> int:
    return len(text.split())

from typing import List

def chunk_text(text: str, min_tokens: int = 300, max_tokens: int = 500, overlap: int = 50) -> List[str]:
    # MiniLM max is 512, so 500 is a safer ceiling
    sentences = text.splitlines(keepends=True)
    chunks = []
    cur_chunk = []
    cur_len = 0

    for s in sentences:
        s_len = tokenize_len(s)
        
        # If a single line is too long, we must break it or it will ruin the index
        if s_len > max_tokens:
            # Simple fix: treat it as its own chunk or sub-split it
            if cur_chunk:
                chunks.append("".join(cur_chunk))
                cur_chunk = []
                cur_len = 0
            chunks.append(s[:max_tokens * 4]) # Rough char approximation
            continue

        if cur_len + s_len > max_tokens:
            # We reached the limit, save the chunk
            full_text = "".join(cur_chunk)
            chunks.append(full_text)
            
            # Create overlap based on the end of the previous chunk
            # We take the last few sentences or a slice to maintain context
            overlap_buffer = cur_chunk[-2:] if len(cur_chunk) > 1 else cur_chunk
            cur_chunk = overlap_buffer + [s]
            cur_len = sum(tokenize_len(item) for item in cur_chunk)
        else:
            cur_chunk.append(s)
            cur_len += s_len

    if cur_chunk:
        chunks.append("".join(cur_chunk))
        
    return chunks