import os
import logging

logger = logging.getLogger("RAG")


def get_chroma_client():
    try:
        import chromadb
    except Exception as e:
        logger.error("chromadb library not available: %s", e)
        return None

    host = os.getenv("CHROMA_SERVER_HOST", "localhost")
    port = os.getenv("CHROMA_SERVER_HTTP_PORT", "8000")
    try:
        client = chromadb.HttpClient(host=host, port=int(port))
        return client
    except Exception as e:
        logger.exception("Failed to connect to Chroma server: %s", e)
        return None


def upsert_documents(
    collection_name: str, documents: list, metadatas: list = None, ids: list = None
):
    client = get_chroma_client()
    if client is None:
        raise RuntimeError("Chroma client not available")
    col = client.get_or_create_collection(collection_name)
    return col.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query(collection_name: str, query_text: str, n_results: int = 5):
    client = get_chroma_client()
    if client is None:
        raise RuntimeError("Chroma client not available")
    col = client.get_or_create_collection(collection_name)
    res = col.query(query_texts=[query_text], n_results=n_results)
    return res
