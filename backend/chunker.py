from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
from nltk_processor import NLTKProcessor
import docling
# from langchain_community.vectorstores.utils import filter_complex_metadata

# Initialize NLTK processor
nltk_proc = NLTKProcessor()

def process_pdf_with_docling(pdf_path: str, lang: list = ["eng"], force_ocr: bool = True) -> str:
    """
    Process a PDF with Docling and return Markdown text.
    
    Args:
        pdf_path (str): Path to the PDF file
        lang (list): List of languages for OCR (default: English)
        force_ocr (bool): Whether to force full-page OCR
        
    Returns:
        str: Markdown text extracted from the PDF
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from pathlib import Path
    import os
    
    # Prevent huggingface_hub from creating symlinks on Windows
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    
    input_path = Path(pdf_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Set OCR options
    ocr_options = TesseractCliOcrOptions(lang=lang)
    pipeline_options = PdfPipelineOptions(
        do_ocr=True, 
        force_full_page_ocr=force_ocr, 
        ocr_options=ocr_options
    )
    
    # Create converter
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    # Convert PDF
    conv_res = converter.convert(input_path)
    doc = conv_res.document
    return doc.export_to_markdown()

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


def extract_text_from_file(file_path: str, file_type: str, ocr_lang: str = "eng") -> str:
    """
    Unified text extraction for all file types.
    
    Args:
        file_path (str): Path to the file
        file_type (str): File extension (pdf, docx, txt, pptx, etc.)
        ocr_lang (str): Language for OCR/processing
        
    Returns:
        str: Extracted text content
    """
    file_type = file_type.lower()
    
    if file_type == 'pdf':
        # Use Docling for PDFs
        lang_list = [ocr_lang] if ocr_lang != "eng" else ["eng"]
        return process_pdf_with_docling(file_path, lang=lang_list)
    
    elif file_type == 'docx':
        # Extract from Word documents
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        except ImportError:
            raise ImportError("python-docx not installed. Run: pip install python-docx")
    
    elif file_type == 'txt':
        # Plain text files
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    elif file_type == 'pptx':
        # Extract from PowerPoint
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            text_content = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_content.append(shape.text)
            return '\n'.join(text_content)
        except ImportError:
            raise ImportError("python-pptx not installed. Run: pip install python-pptx")
    
    else:
        # Fallback: try to read as text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            raise ValueError(f"Unsupported file type: {file_type}")


def translate_if_needed(text: str, ocr_lang: str) -> str:
    """
    Translate text to English if it's an Indic language.
    
    Args:
        text (str): Input text
        ocr_lang (str): Detected or configured language
        
    Returns:
        str: Translated text (or original if no translation needed)
    """
    # Indic languages that need translation
    indic_langs = ['hi', 'ta', 'te', 'bn', 'gu', 'kn', 'ml', 'mr', 'pa', 'or']
    
    if ocr_lang in indic_langs:
        try:
            # Import translation models
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            import torch
            
            # Use NLLB model (same as convert_to_json.py)
            nllb_model_name = "facebook/nllb-200-distilled-600M"
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            # Load models (cache them to avoid reloading)
            if not hasattr(translate_if_needed, '_tokenizer'):
                translate_if_needed._tokenizer = AutoTokenizer.from_pretrained(nllb_model_name)
                translate_if_needed._model = AutoModelForSeq2SeqLM.from_pretrained(nllb_model_name).to(device)
            
            tokenizer = translate_if_needed._tokenizer
            model = translate_if_needed._model
            
            # Language mapping
            lang_map = {
                "hi": "hin_Deva", "ta": "tam_Taml", "te": "tel_Telu", "bn": "ben_Beng",
                "gu": "guj_Gujr", "kn": "kan_Knda", "ml": "mal_Mlym", "mr": "mar_Deva",
                "pa": "pan_Guru", "or": "ory_Orya"
            }
            
            tgt_lang = lang_map.get(ocr_lang, "eng_Latn")
            
            # Split text into chunks if too long
            max_length = 512
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            translated_chunks = []
            
            for chunk in chunks:
                if not chunk.strip():
                    continue
                    
                inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=max_length).to(device)
                
                with torch.no_grad():
                    translated_tokens = model.generate(
                        **inputs,
                        forced_bos_token_id=tokenizer.lang_code_to_id[tgt_lang],
                        max_length=max_length * 2
                    )
                
                translated_text = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
                translated_chunks.append(translated_text)
            
            return ' '.join(translated_chunks)
            
        except Exception as e:
            print(f"Translation failed: {e}")
            return text  # Return original text if translation fails
    
    return text  # No translation needed
