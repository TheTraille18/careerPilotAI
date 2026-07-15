import config  # noqa: F401 — load .env

from langchain_chroma import Chroma

from config import get_chroma_collection_name, get_chroma_persist_dir
from llm.rag.embedding import create_embeddings
from llm.rag.extract_documents import extract_documents
from llm.rag.load_knowledge import load_knowledge_files

embedding = create_embeddings()

knowledge = load_knowledge_files()

documents = extract_documents(knowledge)

print(f"Total documents: {len(documents)}")

vector_store = Chroma.from_texts(
    texts=documents,
    embedding=embedding,
    collection_name=get_chroma_collection_name(),
    persist_directory=get_chroma_persist_dir(),
)


results = vector_store.similarity_search("Describe Justin's Go experience.", k=3)


for results in results:
    print(results.page_content)


