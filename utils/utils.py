from langchain_community.document_loaders import DirectoryLoader
from langchain.document_loaders import PyPDFLoader

# from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
from sentence_transformers import SentenceTransformer
import torch
from const.const import *
import logging
import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
import uuid
from typing import List, Dict, Tuple

from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger("pdf_loader")
# 🔐 Replace with your actual Qdrant Cloud values
qdrant_url = (
    "https://25bb4013-ec77-482a-8dc3-a6661306665f.europe-west3-0.gcp.cloud.qdrant.io"
)
qdrant_api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.M-pMPgmDjS5uraIbs3KsQD4WeyNIzAOon5a0Pl2KXns"

# ✅ Connect securely
client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=6000.0)

collection_name = "Medi_Ai"


loader = DirectoryLoader(
    path=PATH_TO_DOCS,  # path to your directory
    glob="**/*.pdf",  # pattern to match files
    loader_cls=PyPDFLoader,
    show_progress=True,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=300,
    separators=["\n\n", "\n", ".", " ", ""],
)

model = SentenceTransformer("BAAI/bge-base-en-v1.5")


class Load_Embedd_Qdrant:
    def __init__(self):
        self.text_splitter = text_splitter
        self.model = model

    def load_processed(self) -> List[str]:
        if os.path.exists(TRACK_FILE):
            with open(TRACK_FILE, "r") as f:
                logger.info("Loaded processed.json")
                return json.load(f)
        return []

    def save_processed(self, processed: list):
        with open(TRACK_FILE, "w") as f:
            json.dump(processed, f)

    def chunk_and_embed(self, pdf_path: str):
        """Loads a single PDF, splits it, returns both chunks and their embeddings."""
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()  # returns List[Document]
        chunks = self.text_splitter.split_documents(documents)
        chunk_texts = ["passage: " + chunk.page_content for chunk in chunks]
        embeddings = self.model.encode(chunk_texts, normalize_embeddings=True)
        embeddings = [
            emb.tolist() if hasattr(emb, "tolist") else emb for emb in embeddings
        ]
        return chunk_texts, embeddings

    def save_chunks_to_file(self, chunk_texts: List[str], output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunk_texts:
                f.write(chunk + "\n\n")

    def qdrant_upload(
        self, embeddings: List[List[float]], chunk_texts: List[str], pdf_fn: str
    ):
        vector_dim = len(embeddings[0])
        existing_collections = [
            col.name for col in client.get_collections().collections
        ]
        if collection_name not in existing_collections:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )
            logger.info(f"Collection '{collection_name}' created.")
        else:
            logger.info(f"Collection '{collection_name}' already exists.")

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={"text": chunk_texts[i], "pdf_file": pdf_fn, "chunk_index": i},
            )
            for i, embedding in enumerate(embeddings)
        ]

        def batch_upsert(
            points, batch_size=128
        ):  # You can tweak batch_size (e.g., 64–256)
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                client.upsert(collection_name=collection_name, points=batch)
                logger.info(
                    f"Uploaded batch {i // batch_size + 1} with {len(batch)} points from '{pdf_fn}'"
                )

        if points:
            batch_upsert(points, batch_size=128)
            logger.info(
                f"Uploaded {len(points)} points/chunks from '{pdf_fn}' to Qdrant Cloud."
            )
        else:
            logger.warning("No points to upsert (PDF may be empty).")


load_embedd = Load_Embedd_Qdrant()


def process_pdfs():
    logger.info("Starting process_pdfs()")
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    processed = load_embedd.load_processed()
    for file in os.listdir(PATH_TO_DOCS):
        if file.endswith(".pdf") and file not in processed:
            pdf_path = os.path.join(PATH_TO_DOCS, file)
            book_name = os.path.splitext(file)[0]
            output_path = os.path.join(CHUNKS_DIR, f"{book_name}.txt")
            logger.info(f"Processing: {file}")

            # --- MAIN PIPELINE ---
            chunk_texts, embeddings = load_embedd.chunk_and_embed(pdf_path)
            load_embedd.save_chunks_to_file(chunk_texts, output_path)
            load_embedd.qdrant_upload(embeddings, chunk_texts, file)
            processed.append(file)

    load_embedd.save_processed(processed)
    logger.info("All new PDFs processed.")
