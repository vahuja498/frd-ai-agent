"""
app/utils/file_loader.py
Utility helpers for loading and reading text files from disk.
"""
import re
from pathlib import Path
from typing import List


def load_text_file(file_path: str) -> str:
    """Read a .txt file and return its content."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text(encoding="utf-8", errors="ignore")


def load_all_frds(frds_directory: str) -> List[dict]:
    """
    Load all .txt files from the FRDs directory.
    Returns list of {"filename": ..., "content": ...}
    """
    frds_path = Path(frds_directory)
    if not frds_path.exists():
        return []

    results = []
    for file in frds_path.glob("*.txt"):
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                results.append({"filename": file.name, "content": content})
        except Exception:
            pass
    return results


def clean_text(text: str) -> str:
    """
    Remove noise from raw text:
    - Timestamps [00:01:23]
    - Filler words
    - Excessive whitespace
    """
    # Remove timestamps
    text = re.sub(r"\[?\d{1,2}:\d{2}(:\d{2})?\]?", "", text)
    # Remove common filler words
    filler = r"\b(um+|uh+|er+|hmm+|you know|like|basically|literally)\b"
    text = re.sub(filler, "", text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping word-level chunks for embedding.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
