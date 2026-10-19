"""
Embedding backend for the Lonely Planet semantic search app.

Two interchangeable engines produce vectors for `sentence-transformers/all-MiniLM-L6-v2`
(384 dimensions, mean pooling, L2-normalised):

1. OnnxEmbedder  - onnxruntime + tokenizers, no PyTorch. Default, lightweight
                   enough for free hosting tiers (~90 MB model, no torch wheel).
2. STEmbedder    - sentence-transformers fallback for local development.

Use `get_embedder()`; it picks ONNX when the local model directory exists and
falls back to sentence-transformers otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import numpy as np

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models" / "all-MiniLM-L6-v2"
MAX_SEQ_LENGTH = 256


def _mean_pool_normalise(last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    """Mean-pool token vectors using the attention mask, then L2-normalise."""
    mask = attention_mask[..., None].astype(np.float32)
    summed = (last_hidden_state * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), 1e-9, None)
    pooled = summed / counts
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    return pooled / np.clip(norms, 1e-12, None)


class OnnxEmbedder:
    """MiniLM inference through onnxruntime (CPU, no torch dependency)."""

    name = "onnxruntime"

    def __init__(self, model_dir: Path = MODEL_DIR):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        onnx_path = model_dir / "model.onnx"
        tokenizer_path = model_dir / "tokenizer.json"
        if not onnx_path.exists() or not tokenizer_path.exists():
            raise FileNotFoundError(f"ONNX model files not found in {model_dir}")

        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

        options = ort.SessionOptions()
        # Full graph optimisation on a 90 MB model is slow on constrained hosts;
        # disabling it keeps cold start short (query encoding is still ~ms).
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        options.intra_op_num_threads = 2
        options.log_severity_level = 3

        self.session = ort.InferenceSession(
            str(onnx_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.input_names = {i.name for i in self.session.get_inputs()}

    def encode(self, texts: List[str]) -> np.ndarray:
        encodings = self.tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)

        feeds = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)

        outputs = self.session.run(None, feeds)
        # Model returns (last_hidden_state, pooler_output); hidden state is index 0.
        hidden = outputs[0]
        return _mean_pool_normalise(hidden, attention_mask).astype(np.float32)


class STEmbedder:
    """sentence-transformers fallback (requires torch)."""

    name = "sentence-transformers"

    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_id)

    def encode(self, texts: List[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32
            ),
            dtype=np.float32,
        )


_EMBEDDER: Optional[object] = None


def get_embedder(prefer: str = "auto"):
    """Return a singleton embedder, cached for the process lifetime."""
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER

    if prefer in ("auto", "onnx"):
        try:
            _EMBEDDER = OnnxEmbedder()
            return _EMBEDDER
        except Exception:
            if prefer == "onnx":
                raise

    _EMBEDDER = STEmbedder()
    return _EMBEDDER


def loaded_engine_name() -> str:
    """Name of the engine if it is already loaded, otherwise 'not loaded yet'."""
    return getattr(_EMBEDDER, "name", "not loaded yet")


def embed_query(text: str, embedder=None) -> np.ndarray:
    """Embed a single query string into a normalised (384,) vector."""
    engine = embedder or get_embedder()
    vec = engine.encode([text])[0]
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec
