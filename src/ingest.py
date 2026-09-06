import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus")
INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "index")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def load_corpus():
    docs = []
    for fname in sorted(os.listdir(CORPUS_DIR)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(CORPUS_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        docs.append({"id": fname, "text": text})
    return docs


def build_index():
    os.makedirs(INDEX_DIR, exist_ok=True)
    docs = load_corpus()
    print(f"Loaded {len(docs)} documents from corpus/")

    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode([d["text"] for d in docs], show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)   # L2 = straight-line distance between vectors
    index.add(embeddings)

    faiss.write_index(index, os.path.join(INDEX_DIR, "corpus.index"))
    with open(os.path.join(INDEX_DIR, "docs.json"), "w", encoding="utf-8") as f:
        json.dump(docs, f)

    print(f"Index built with {index.ntotal} vectors -> saved to {INDEX_DIR}")


if __name__ == "__main__":
    build_index()