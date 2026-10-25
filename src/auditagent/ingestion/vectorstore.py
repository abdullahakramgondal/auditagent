"""A throw-away vector index for ONE document. Nothing is written to disk."""

import uuid

import chromadb

from auditagent.ingestion.embedder import Embedder
from auditagent.schemas.chunk import Chunk, SearchHit


class ContractIndex:
    def __init__(self, embedder: Embedder, chunks: list[Chunk], doc_label: str = "doc"):
        if not chunks:
            raise ValueError("Cannot index zero chunks")
        self._embedder = embedder
        self._chunks = {c.chunk_id: c for c in chunks}
        self._client = chromadb.EphemeralClient()
        self._name = f"{doc_label}_{uuid.uuid4().hex[:12]}"
        self._collection = self._client.create_collection(self._name)
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embedder.embed([c.text for c in chunks]),
        )

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        k = max(1, min(k, len(self._chunks)))
        result = self._collection.query(query_embeddings=self._embedder.embed([query]), n_results=k)
        return [
            SearchHit(chunk=self._chunks[chunk_id], distance=float(dist))
            for chunk_id, dist in zip(result["ids"][0], result["distances"][0])
        ]

    def close(self) -> None:
        self._client.delete_collection(self._name)
