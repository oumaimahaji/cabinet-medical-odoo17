from sentence_transformers import SentenceTransformer, util
import torch

print("Loading model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

sentence1 = "Le patient est allergique à la pénicilline"
sentence2 = "Prescription d'Augmentin"

print(f"Sentence 1: {sentence1}")
print(f"Sentence 2: {sentence2}")

print("Calculating embeddings...")
with torch.no_grad():
    embedding1 = model.encode([sentence1], convert_to_tensor=True)
    embedding2 = model.encode([sentence2], convert_to_tensor=True)
    
    cosine_score = util.cos_sim(embedding1, embedding2).item()

print(f"Cosine Similarity Score: {cosine_score:.4f}")
