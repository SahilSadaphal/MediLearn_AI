from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from const.const import *


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


def save_txt(PATH_TO_ALL_DOCS_TXT: str, documents) -> str:
    try:
        with open(PATH_TO_ALL_DOCS_TXT, "w", encoding="utf-8") as f:
            for doc in documents:
                f.write(doc.page_content + "\n\n\n")
        return f"Succesfully stored at {PATH_TO_ALL_DOCS_TXT}"
    except:
        return f"Error while storing at {PATH_TO_ALL_DOCS_TXT}"
