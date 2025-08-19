from langchain_groq import ChatGroq
import yaml
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


def load_config(path="D:\MediLearn_AI\config.yaml"):
    with open(path, "r") as file:
        config = yaml.safe_load_all(file)
    return config


config = load_config()

llm = ChatGroq(
    model=config[0]["llm"]["model"],
    temperature=config[0]["llm"]["temperature"],
    api_key=config[0]["llm"]["api_key_env"],
)
model = SentenceTransformer("BAAI/bge-base-en-v1.5")

qdrant_url = (
    "https://25bb4013-ec77-482a-8dc3-a6661306665f.europe-west3-0.gcp.cloud.qdrant.io"
)
qdrant_api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.M-pMPgmDjS5uraIbs3KsQD4WeyNIzAOon5a0Pl2KXns"

# ✅ Connect securely
client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=6000.0)

collection_name = "Medi_Ai"
