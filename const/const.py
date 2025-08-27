import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PATH_TO_ALL_DOCS_TXT = os.path.join(BASE_DIR, "data", "all_docs.txt")
PATH_TO_DOCS = os.path.join(BASE_DIR, "docs")
CHUNKS_DIR = os.path.join(BASE_DIR, "data", "chunks")
TRACK_FILE = os.path.join(BASE_DIR, "utils", "processed.json")
