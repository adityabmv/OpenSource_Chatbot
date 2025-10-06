# embeddings.py
from langchain_huggingface import HuggingFaceEmbeddings
import torch

_embeddings_model = None  # global cache

def get_embeddings_model(model_name="sentence-transformers/all-MiniLM-L6-v2"):
    global _embeddings_model
    if _embeddings_model is None:
        preferred_device = "cuda" if torch.cuda.is_available() else "cpu"
        device_used = preferred_device
        try:
            print(f"[INFO] Using {preferred_device} for embeddings...")
            _embeddings_model = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": preferred_device}
            )
            # Trigger a tiny encode to ensure the backend is healthy
            _ = _embeddings_model.embed_query("healthcheck")
        except Exception as e:
            if preferred_device == "cuda":
                print(f"[WARN] CUDA embeddings init failed: {e}. Falling back to CPU...")
                device_used = "cpu"
                _embeddings_model = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs={"device": "cpu"}
                )
                _ = _embeddings_model.embed_query("healthcheck")
            else:
                raise
        print(f"[INFO] Embeddings initialized on {device_used}")
    return _embeddings_model