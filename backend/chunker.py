from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

def chunk_text(text, chunk_size=300, chunk_overlap=30, metadata=None):
    """
    Splits text into chunks with specified size and overlap.
    Uses recursive splitting on multiple separators for more semantic chunks.
    
    Args:
        text (str): The text to split into chunks
        chunk_size (int): Size of each chunk (default: 300 for more granular chunks)
        chunk_overlap (int): Amount of overlap between chunks (default: 30)
        metadata (dict): Additional metadata to store with each chunk
        
    Returns:
        list: List of dictionaries containing chunk text and metadata
    """
    # Define separators in order of preference
    separators = [
        "\n\n",     # Double newline (paragraphs)
        "\n",       # Single newline
        ". ",       # Period followed by space
        "? ",       # Question mark followed by space
        "! ",       # Exclamation followed by space
        ";",        # Semicolon
        ",",        # Comma
        " ",        # Space (last resort)
        ""          # Character-level splitting if needed
    ]
    
    splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False
    )
    
    # Clean and normalize text
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces
    chunks = splitter.split_text(text)
    
    # Add metadata to each chunk
    metadata = metadata or {}
    chunk_documents = []
    for i, chunk in enumerate(chunks):
        chunk_metadata = {
            **metadata,
            "chunk_index": i,
            "total_chunks": len(chunks)
        }
        chunk_documents.append({
            "text": chunk.strip(),
            "metadata": chunk_metadata
        })
    
    return chunk_documents
