import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.utils import *
from sentence_transformers import SentenceTransformer

query = "What is the function of the heart?"
query_embedding = model.encode("passage: " + query, normalize_embeddings=True)
print(query_embedding)

results = client.search(
    collection_name=collection_name,
    query_vector=query_embedding.tolist(),
    limit=5,
    with_payload=True,  # Include metadata
    score_threshold=0.9,
)
print(results)
