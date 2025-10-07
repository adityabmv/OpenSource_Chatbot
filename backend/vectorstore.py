# vectorstore.py
# Add this to vectorstore.py

import os
from langchain_chroma import Chroma

def load_or_create_vectorstore(embeddings, collection_name="rag_db", persist_directory="vector_db"):
    if os.path.exists(persist_directory):
        return Chroma(collection_name=collection_name, embedding_function=embeddings, persist_directory=persist_directory)
    else:
        return Chroma.from_texts([], embedding=embeddings, collection_name=collection_name, persist_directory=persist_directory)

def append_to_vectorstore(chunks, embeddings, collection_name="rag_db", persist_directory="vector_db"):
    vectorstore = load_or_create_vectorstore(embeddings, collection_name, persist_directory)
    vectorstore.add_texts(chunks)
    return vectorstore

def query_vectorstore(vectorstore, query, top_k=5):
    """
    Retrieve top_k chunks relevant to query.
    """
    results = vectorstore.similarity_search(query, k=top_k)
    return [r.page_content for r in results]
