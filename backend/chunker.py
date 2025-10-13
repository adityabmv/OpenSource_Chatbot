from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import docling
# from langchain_community.vectorstores.utils import filter_complex_metadata

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
    Uses fast character-based chunking for speed.
    
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
    
    # Fast character-based chunking for speed
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - chunk_overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        if chunk_text.strip():  # Only add non-empty chunks
            chunks.append(chunk_text)
    
    # Simple key phrase extraction
    chunk_phrases = []
    for chunk in chunks:
        # Simple heuristic: extract words longer than 4 characters
        words = chunk.lower().split()
        phrases = [word for word in words if len(word) > 4][:5]
        chunk_phrases.append(phrases)

    # Simplify metadata for vectorstore
    simple_metadata = make_simple_metadata(metadata)

    return [{"text": chunk, "metadata": simple_metadata} for chunk in chunks]


def extract_text_from_file(file_path: str, file_type: str, ocr_lang: str = "eng") -> str:
    """
    Unified text extraction for all file types.
    FORCED OCR for all PDFs (from mmt.py integration).
    """
    file_type = file_type.lower()
    
    if file_type == 'pdf':
        # FORCE OCR for all PDFs (skip PyMuPDF text extraction)
        print("📄 Forcing OCR for PDF...")
        try:
            import pytesseract
            from PIL import Image
            import io
            import fitz
            
            doc = fitz.open(file_path)
            ocr_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img, lang=ocr_lang)
                ocr_text += page_text + "\n"
            
            doc.close()
            text = ocr_text
            print(f"✅ OCR completed, extracted {len(text)} characters")
            
        except ImportError:
            print("❌ pytesseract not installed for OCR")
            raise ImportError("For PDFs, install: pip install pytesseract pillow")
        except Exception as ocr_error:
            print(f"❌ OCR failed: {ocr_error}")
            raise
        
        return text
    
    elif file_type == 'docx':
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        except ImportError:
            raise ImportError("python-docx not installed. Run: pip install python-docx")
    
    elif file_type == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    elif file_type == 'pptx':
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
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            raise ValueError(f"Unsupported file type: {file_type}")


def translate_if_needed(text: str, ocr_lang: str) -> str:
    """
    Translation using Facebook NLLB model (from mmt.py integration).
    """
    if not text.strip():
        return text
    
    # Skip translation if OCR language is English
    english_langs = ['eng', 'en', 'english']
    if ocr_lang.lower() in english_langs:
        print(f"✅ OCR language is English ({ocr_lang}), skipping translation")
        return text
    
    print(f"🌐 OCR language is {ocr_lang}, translating to English using NLLB...")
    
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        import torch
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Language mapping for NLLB
        lang_map = {
            "hi": "hin_Deva", "ta": "tam_Taml", "te": "tel_Telu", "bn": "ben_Beng",
            "gu": "guj_Gujr", "kn": "kan_Knda", "ml": "mal_Mlym", "mr": "mar_Deva",
            "pa": "pan_Guru", "or": "ory_Orya", "en": "eng_Latn", "eng": "eng_Latn"
        }
        
        src_lang = lang_map.get(ocr_lang.lower(), "eng_Latn")  # Default to English if not found
        tgt_lang = "eng_Latn"  # Target is always English
        
        print(f"🔧 Loading NLLB model on {device}...")
        
        # Cache model to avoid reloading
        if not hasattr(translate_if_needed, '_model'):
            model_name = "facebook/nllb-200-distilled-600M"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)
            translate_if_needed._tokenizer = tokenizer
            translate_if_needed._model = model
            print(f"✅ NLLB model loaded")
        
        tokenizer = translate_if_needed._tokenizer
        model = translate_if_needed._model
        
        # Split text into smaller chunks to avoid model limits
        max_length = 512
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        translated_sentences = []
        
        print(f"📝 Translating {len(sentences)} sentences...")
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
                
            try:
                # Tokenize with language codes
                inputs = tokenizer(sentence, return_tensors="pt", padding=True, truncation=True, max_length=max_length).to(device)
                inputs['forced_bos_token_id'] = tokenizer.convert_tokens_to_ids(tgt_lang)
                
                with torch.no_grad():
                    translated_tokens = model.generate(
                        **inputs,
                        max_length=max_length,
                        num_beams=1,  # Greedy decoding for speed
                        early_stopping=True
                    )
                
                translated_text = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
                translated_sentences.append(translated_text.strip())
                
                if (i + 1) % 10 == 0:
                    print(f"  ✅ Translated {i + 1}/{len(sentences)} sentences")
                
            except Exception as e:
                print(f"    ❌ Error translating sentence {i+1}: {e}")
                translated_sentences.append(sentence)  # Keep original
        
        final_translation = ' '.join(translated_sentences)
        print(f"✅ NLLB translation completed! {len(final_translation)} characters")
        return final_translation
        
    except Exception as e:
        print(f"❌ NLLB translation failed: {e}")
        print("⚠️ Keeping original text")
        return text
