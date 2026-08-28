import time

print("Testing MiniLM model...")
try:
    from sentence_transformers import SentenceTransformer
    import torch
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode("Bonjour docteur")
    print(f"Model loaded and functioning successfully! Embedding shape: {embeddings.shape}")
except Exception as e:
    print(f"Error loading model: {e}")
