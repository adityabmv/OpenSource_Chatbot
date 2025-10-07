# vectorstore.py
# Updated to support multiple bots with independent vectorstores

import os
from typing import Optional
from langchain_chroma import Chroma
from bot_manager import BotManager

def load_or_create_vectorstore(embeddings, collection_name="rag_db", persist_directory="vector_db"):
    """Load or create a vectorstore for a specific bot"""
    if os.path.exists(persist_directory):
        return Chroma(collection_name=collection_name, embedding_function=embeddings, persist_directory=persist_directory)
    else:
        # For new vectorstores, create with empty documents but use persist_directory
        # This avoids the empty embeddings issue
        import chromadb
        client = chromadb.PersistentClient(path=persist_directory)
        collection = client.get_or_create_collection(name=collection_name)
        return Chroma(client=client, collection_name=collection_name, embedding_function=embeddings)

def append_to_vectorstore(chunks, embeddings, collection_name="rag_db", persist_directory="vector_db"):
    """Append chunks to a bot's vectorstore"""
    vectorstore = load_or_create_vectorstore(embeddings, collection_name, persist_directory)
    vectorstore.add_texts(chunks)
    return vectorstore

def query_vectorstore(vectorstore, query, top_k=5):
    """
    Retrieve top_k chunks relevant to query from a specific vectorstore.
    """
    results = vectorstore.similarity_search(query, k=top_k)
    return [r.page_content for r in results]

def get_bot_vectorstore(bot_config, embeddings_model) -> Optional[Chroma]:
    """Get or create a vectorstore for a specific bot"""
    if not bot_config or not bot_config.vectorstore_path:
        return None

    try:
        return load_or_create_vectorstore(
            embeddings_model,
            collection_name="rag_db",
            persist_directory=bot_config.vectorstore_path
        )
    except Exception as e:
        print(f"Error loading bot vectorstore: {e}")
        return None

def delete_bot_vectorstore(bot_config) -> bool:
    """Delete a bot's vectorstore directory"""
    if not bot_config or not bot_config.vectorstore_path:
        return False

    try:
        if os.path.exists(bot_config.vectorstore_path):
            import shutil
            shutil.rmtree(bot_config.vectorstore_path)
        return True
    except Exception as e:
        print(f"Error deleting bot vectorstore: {e}")
        return False
