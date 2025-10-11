from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
from nltk_processor import NLTKProcessor
# from langchain_community.vectorstores.utils import filter_complex_metadata

# Initialize NLTK processor
nltk_proc = NLTKProcessor()

def make_simple_metadata(metadata):
    simple = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            simple[k] = v
        elif isinstance(v, list):
            simple[k] = ", ".join(map(str, v))
        # skip other types
    return simple

def chunk_text(text, chunk_size=300, chunk_overlap=30, metadata=None):
    """
    Splits text into chunks with specified size and overlap.
    Uses NLTK for preprocessing and RecursiveCharacterTextSplitter for chunking.
    
    Args:
        text (str): The text to split into chunks
        chunk_size (int): Size of each chunk (default: 300 for more granular chunks)
        chunk_overlap (int): Amount of overlap between chunks (default: 30)
        metadata (dict): Additional metadata to store with each chunk
        
    Returns:
        list: List of dictionaries containing chunk text and metadata
    """
    if metadata is None:
        metadata = {}
    elif isinstance(metadata, str):
        metadata = {"text": metadata}
    elif isinstance(metadata, dict):
        for key, value in metadata.items():
            if isinstance(value, list):
                metadata[key] = ", ".join(value)
    
    # Advanced semantic chunking
    from nltk.tokenize import sent_tokenize
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    import numpy as np

    # Tokenize text into sentences
    sentences = sent_tokenize(text)
    if len(sentences) == 0:
        return []

    # Embed sentences
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(sentences)

    # Determine number of clusters (chunks)
    n_chunks = max(1, len(sentences) // (chunk_size // 10))  # Roughly chunk_size words per chunk
    kmeans = KMeans(n_clusters=n_chunks, random_state=42, n_init=5)
    labels = kmeans.fit_predict(embeddings)

    # Group sentences by cluster label
    clustered = {}
    for label, sentence in zip(labels, sentences):
        clustered.setdefault(label, []).append(sentence)

    # Build chunks
    chunks = [" ".join(clustered[label]) for label in sorted(clustered.keys())]

    # Extract key phrases for each chunk
    chunk_phrases = []
    for chunk in chunks:
        phrases = nltk_proc.extract_key_phrases(chunk)
        print("Extracted phrases:", phrases)
        chunk_phrases.append(phrases)

    # Simplify metadata for vectorstore
    simple_metadata = make_simple_metadata(metadata)

    return [{"text": chunk, "metadata": simple_metadata} for chunk in chunks]
