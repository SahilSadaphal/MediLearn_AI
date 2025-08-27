import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import torch
from const.const import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.utils import *
from const.const import *
import logging

# Logger
import logging

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "admin.log"))
log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger("admin")
logger.setLevel(logging.INFO)

# Only add handlers if not already set (prevents duplicate logs if rerun/imported)
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


import os
import json
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


if __name__ == "__main__":
    process_pdfs()
