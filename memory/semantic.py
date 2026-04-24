"""Semantic memory: ChromaDB vector store for factual knowledge.

Uses OpenAI embeddings for semantic search. Seeded from a JSON file of
documents on first run; documents can be added dynamically at runtime too.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


class SemanticMemory:
    def __init__(
        self,
        persist_path: str | None = None,
        collection_name: str = "knowledge",
        seed_path: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.persist_path = persist_path or os.getenv("CHROMA_PATH", "./data/chroma")
        Path(self.persist_path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_path)

        self._embed_fn = OpenAIEmbeddingFunction(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model_name=model or os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embed_fn,
        )

        seed = seed_path or os.getenv("KNOWLEDGE_SEED_PATH", "./data/knowledge_seed.json")
        if Path(seed).exists() and self.collection.count() == 0:
            self._seed_from_file(seed)

    def _seed_from_file(self, seed_path: str) -> None:
        docs = json.loads(Path(seed_path).read_text(encoding="utf-8"))
        if not docs:
            return
        ids = [d["id"] for d in docs]
        texts = [d["text"] for d in docs]
        metadatas = [{"topic": d.get("topic", "general")} for d in docs]
        self.collection.add(ids=ids, documents=texts, metadatas=metadatas)

    def save(self, doc_id: str, text: str, topic: str = "general") -> None:
        self.collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[{"topic": topic}],
        )

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(query_texts=[query], n_results=min(k, self.collection.count()))
        hits: list[dict] = []
        docs = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for i, doc in enumerate(docs):
            hits.append(
                {
                    "id": ids[i],
                    "text": doc,
                    "distance": distances[i] if i < len(distances) else None,
                    "topic": metadatas[i].get("topic") if i < len(metadatas) else None,
                }
            )
        return hits

    def count(self) -> int:
        return self.collection.count()

    def delete(self, doc_id: str) -> None:
        self.collection.delete(ids=[doc_id])
