from langchain_groq import ChatGroq
import yaml
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import re

def load_config(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(path, "r") as file:
        config = list(yaml.safe_load_all(file))
    return config

def substitute_env_vars(config):
    pattern = re.compile(r"\$\{(\w+)\}")
    def replace_env(match):
        var = match.group(1)
        return os.environ.get(var, "")
    if isinstance(config, dict):
        return {k: substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [substitute_env_vars(i) for i in config]
    elif isinstance(config, str):
        return pattern.sub(replace_env, config)
    else:
        return config

load_dotenv()

config = load_config()
config = substitute_env_vars(config)

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
