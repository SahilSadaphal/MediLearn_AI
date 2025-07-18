import sys
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import torch


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.utils import *
from const.const import *

# Loading PDF And Saving in documents
documents = loader.load()
chunks = text_splitter.split_documents(documents)
# Recommended model (1024-dim): strong performance in benchmarks
model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# Hugging Face BGE recommends adding this prefix
chunks = ["passage: " + chunk for chunk in chunks]

embeddings = model.encode(chunks, normalize_embeddings=True)

print(embeddings.shape)  # e.g., (2, 768)
