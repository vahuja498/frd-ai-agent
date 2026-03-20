"""
app/services/vector_store.py
FAISS-backed local vector store for past FRD documents.
Uses SentenceTransformers for embeddings — no API key required.
"""
import os
import json
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.utils.file_loader import clean_text, chunk_text, load_all_frds


class VectorStoreService:
    """
    Manages a FAISS index of past FRD document chunks.

    Files stored in vectorstore/:
      - index.faiss  → FAISS index binary
      - metadata.pkl → list of {"text": ..., "source": ...} dicts
    """

    INDEX_FILE = "index.faiss"
    META_FILE = "metadata.pkl"

    def __init__(self) -> None:
        self._store_path = Path(settings.vectorstore_path)
        self._store_path.mkdir(parents=True, exist_ok=True)

        print(f"[VectorStore] Loading embedding model: {settings.embedding_model}")
        self._embedder = SentenceTransformer(settings.embedding_model)
        self._dim = self._embedder.get_sentence_embedding_dimension()

        self._index: faiss.IndexFlatL2 = None
        self._metadata: List[dict] = []

        self._load_or_create()

    # ── Public API ────────────────────────────────────────────────────────────

    def index_frds_from_directory(self, frds_dir: str) -> int:
        """
        Load all FRD .txt files from a directory and add them to the index.
        Returns number of chunks indexed.
        """
        frds = load_all_frds(frds_dir)
        if not frds:
            print(f"[VectorStore] No FRD files found in: {frds_dir}")
            return 0

        total = 0
        for frd in frds:
            cleaned = clean_text(frd["content"])
            chunks = chunk_text(cleaned, chunk_size=400, overlap=40)
            for chunk in chunks:
                self.add_document(chunk, source=frd["filename"])
                total += 1

        self._save()
        print(f"[VectorStore] Indexed {total} chunks from {len(frds)} FRD file(s)")
        return total

    def add_document(self, text: str, source: str = "unknown") -> None:
        """Embed and add a single text chunk."""
        embedding = self._embed([text])
        self._index.add(embedding)
        self._metadata.append({"text": text, "source": source})

    def search(self, query: str, top_k: int = None) -> List[dict]:
        """
        Search for top-K most similar chunks.
        Returns list of {"text": ..., "source": ..., "similarity_score": ...}
        """
        k = top_k or settings.top_k_results
        if self._index.ntotal == 0:
            return []

        k = min(k, self._index.ntotal)
        query_vec = self._embed([query])
        distances, indices = self._index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self._metadata[idx]
            # Convert L2 distance to a 0-1 similarity score
            similarity = float(1 / (1 + dist))
            results.append({
                "text": meta["text"],
                "source": meta["source"],
                "similarity_score": round(similarity, 4),
            })
        return results

    @property
    def total_chunks(self) -> int:
        return self._index.ntotal if self._index else 0

    # ── Private ───────────────────────────────────────────────────────────────

    def _embed(self, texts: List[str]) -> np.ndarray:
        vecs = self._embedder.encode(texts, normalize_embeddings=True)
        return np.array(vecs, dtype="float32")

    def _load_or_create(self) -> None:
        index_path = self._store_path / self.INDEX_FILE
        meta_path = self._store_path / self.META_FILE

        if index_path.exists() and meta_path.exists():
            self._index = faiss.read_index(str(index_path))
            with open(meta_path, "rb") as f:
                self._metadata = pickle.load(f)
            print(f"[VectorStore] Loaded existing index — {self._index.ntotal} chunks")
        else:
            self._index = faiss.IndexFlatL2(self._dim)
            self._metadata = []
            print(f"[VectorStore] Created new FAISS index (dim={self._dim})")

    def _save(self) -> None:
        faiss.write_index(self._index, str(self._store_path / self.INDEX_FILE))
        with open(self._store_path / self.META_FILE, "wb") as f:
            pickle.dump(self._metadata, f)
        print(f"[VectorStore] Saved — {self._index.ntotal} total chunks")
