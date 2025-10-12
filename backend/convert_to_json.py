import os, fitz, json, re, unicodedata, torch
from PIL import Image
import pytesseract
from langdetect import detect, DetectorFactory
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from docx import Document
from pptx import Presentation
import io

# -------------------------------
# Device setup
# -------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DetectorFactory.seed = 0

# -------------------------------
# Load NLLB Translation Model
# -------------------------------
nllb_model_name = "facebook/nllb-200-distilled-600M"
nllb_tokenizer = AutoTokenizer.from_pretrained(nllb_model_name)
nllb_model = AutoModelForSeq2SeqLM.from_pretrained(nllb_model_name).to(device)

lang_map = {
    "hi": "hin_Deva", "ta": "tam_Taml", "te": "tel_Telu", "bn": "ben_Beng",
    "gu": "guj_Gujr", "kn": "kan_Knda", "ml": "mal_Mlym", "mr": "mar_Deva",
    "pa": "pan_Guru", "or": "ory_Orya", "en": "eng_Latn"
}

ocr_lang_map = {
    "hi": "hin", "ta": "tam", "te": "tel", "bn": "ben",
    "gu": "guj", "kn": "kan", "ml": "mal", "mr": "mar",
    "pa": "pan", "or": "ori", "en": "eng"
}

# -------------------------------
# Load BART Summarizer
# -------------------------------
bart_model_name = "facebook/bart-large-cnn"
bart_tokenizer = AutoTokenizer.from_pretrained(bart_model_name)
bart_model = AutoModelForSeq2SeqLM.from_pretrained(bart_model_name).to(device)

# -------------------------------
# Helpers
# -------------------------------
def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s\u0900-\u0D7F]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def chunk_text(text, tokenizer, max_tokens=500):
    words = text.split()
    chunks, current_chunk = [], []
    for word in words:
        current_chunk.append(word)
        tokenized = tokenizer(" ".join(current_chunk), return_tensors="pt", truncation=False)
        if tokenized["input_ids"].shape[1] >= max_tokens:
            chunks.append(" ".join(current_chunk[:-1]))
            current_chunk = [word]
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def translate_chunks(chunks, src_lang="en"):
    src_code = lang_map.get(src_lang, "eng_Latn")
    tgt_code = "eng_Latn"
    nllb_tokenizer.src_lang = src_code
    nllb_tokenizer.tgt_lang = tgt_code
    bos_id = nllb_tokenizer.convert_tokens_to_ids(tgt_code)

    translations = []
    for chunk in chunks:
        inputs = nllb_tokenizer(chunk, return_tensors="pt", truncation=True, max_length=512).to(device)
        outputs = nllb_model.generate(**inputs, forced_bos_token_id=bos_id, max_length=512, num_beams=4)
        translated = nllb_tokenizer.decode(outputs[0], skip_special_tokens=True)
        translations.append(translated)
    return " ".join(translations)

def remove_redundant_sentences(text):
    seen, result = set(), []
    for sentence in re.split(r'(?<=[.?!])\s+', text):
        s = sentence.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return " ".join(result)

def summarize_english(text):
    if not text.strip():
        return ""
    inputs = bart_tokenizer([text], max_length=1024, return_tensors="pt", truncation=True).to(device)
    summary_ids = bart_model.generate(
        inputs["input_ids"],
        max_length=150, min_length=80,
        num_beams=4, length_penalty=1.0, early_stopping=True
    )
    summary = bart_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return " ".join(summary.split()[:100])

# -------------------------------
# Main function
# -------------------------------
def convert_to_json(file_path: str, ocr_lang: str = "eng", min_words_for_text_extract: int = 50):
    """
    Process a file (PDF, DOCX, TXT, PPTX) with smart text extraction and OCR fallback.
    - First tries text extraction
    - Falls back to OCR if text has fewer than min_words_for_text_extract words
    Returns a dict with {"pages": [...]}
    """
    import traceback

    try:
        # Determine file type
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return process_pdf(file_path, ocr_lang, min_words_for_text_extract)
        elif file_ext == '.docx':
            return process_docx(file_path, ocr_lang)
        elif file_ext == '.txt':
            return process_txt(file_path, ocr_lang)
        elif file_ext == '.pptx':
            return process_pptx(file_path, ocr_lang, min_words_for_text_extract)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Supported types: .pdf, .docx, .txt, .pptx")

    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"convert_to_json failed: {str(e)}")


def process_pdf(file_path: str, ocr_lang: str = "eng", min_words: int = 50):
    """Process PDF with smart text extraction + OCR fallback"""
    # Normalize: convert Tesseract code (e.g. "tel") to internal code (e.g. "te")
    lang_code = next((k for k, v in ocr_lang_map.items() if v == ocr_lang), "en")
    print(f"[DEBUG] Received ocr_lang: {ocr_lang}")
    print(f"[DEBUG] Normalized lang_code: {lang_code}")

    doc = fitz.open(file_path)
    pdf_data = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # First, try text extraction
        extracted_text = page.get_text().strip()
        word_count = len(extracted_text.split())
        
        print(f"[DEBUG] Page {page_num + 1}: Extracted {word_count} words via text extraction")
        
        # If insufficient text, use OCR
        if word_count < min_words:
            print(f"[DEBUG] Page {page_num + 1}: Using OCR (word count {word_count} < {min_words})")
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # OCR using Tesseract-compatible code
            ocr_code = ocr_lang_map.get(lang_code, "eng")
            text = pytesseract.image_to_string(img, lang=ocr_code)
            text = clean_text(text)
        else:
            print(f"[DEBUG] Page {page_num + 1}: Using text extraction")
            text = clean_text(extracted_text)
        
        print(f"[DEBUG] Page {page_num + 1} final text (first 300 chars): {text[:300]}")

        # Auto-detect language if not provided or defaulted
        lang = lang_code
        if not ocr_lang or ocr_lang == "eng":
            try:
                if len(text.strip()) >= 20:
                    detected = detect(text)
                    print(f"[DEBUG] Detected language: {detected}")
                    if detected in lang_map:
                        lang = detected
            except Exception as e:
                print(f"[WARN] Language detection failed: {e}")
                lang = "en"

        if lang not in lang_map:
            print(f"[WARN] Language '{lang}' not supported, defaulting to 'en'")
            lang = "en"

        # Translate + summarize with robust fallbacks
        content_en, summary_en = process_text_content(text, lang, page_num + 1)

        page_dict = {
            "page_number": page_num + 1,
            "original_language": lang,
            "content_original": text,
            "content_en": content_en,
            "summary_en": summary_en
        }
        pdf_data.append(page_dict)

    return {"pages": pdf_data}


def process_docx(file_path: str, ocr_lang: str = "eng"):
    """Process Word document"""
    lang_code = next((k for k, v in ocr_lang_map.items() if v == ocr_lang), "en")
    
    doc = Document(file_path)
    docx_data = []
    
    # Combine all paragraphs as one "page"
    full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    text = clean_text(full_text)
    
    print(f"[DEBUG] DOCX: Extracted {len(text.split())} words")
    
    # Auto-detect language
    lang = lang_code
    if not ocr_lang or ocr_lang == "eng":
        try:
            if len(text.strip()) >= 20:
                detected = detect(text)
                print(f"[DEBUG] Detected language: {detected}")
                if detected in lang_map:
                    lang = detected
        except Exception as e:
            print(f"[WARN] Language detection failed: {e}")
            lang = "en"

    if lang not in lang_map:
        lang = "en"

    # Process content
    content_en, summary_en = process_text_content(text, lang, 1)

    page_dict = {
        "page_number": 1,
        "original_language": lang,
        "content_original": text,
        "content_en": content_en,
        "summary_en": summary_en
    }
    docx_data.append(page_dict)

    return {"pages": docx_data}


def process_txt(file_path: str, ocr_lang: str = "eng"):
    """Process plain text file"""
    lang_code = next((k for k, v in ocr_lang_map.items() if v == ocr_lang), "en")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        full_text = f.read()
    
    text = clean_text(full_text)
    print(f"[DEBUG] TXT: Extracted {len(text.split())} words")
    
    # Auto-detect language
    lang = lang_code
    if not ocr_lang or ocr_lang == "eng":
        try:
            if len(text.strip()) >= 20:
                detected = detect(text)
                print(f"[DEBUG] Detected language: {detected}")
                if detected in lang_map:
                    lang = detected
        except Exception as e:
            print(f"[WARN] Language detection failed: {e}")
            lang = "en"

    if lang not in lang_map:
        lang = "en"

    # Process content
    content_en, summary_en = process_text_content(text, lang, 1)

    page_dict = {
        "page_number": 1,
        "original_language": lang,
        "content_original": text,
        "content_en": content_en,
        "summary_en": summary_en
    }

    return {"pages": [page_dict]}


def process_pptx(file_path: str, ocr_lang: str = "eng", min_words: int = 50):
    """Process PowerPoint with smart text extraction + OCR fallback for slides"""
    lang_code = next((k for k, v in ocr_lang_map.items() if v == ocr_lang), "en")
    
    prs = Presentation(file_path)
    pptx_data = []
    
    for slide_num, slide in enumerate(prs.slides):
        # Extract text from shapes
        extracted_text = ""
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                extracted_text += shape.text + "\n"
        
        extracted_text = extracted_text.strip()
        word_count = len(extracted_text.split())
        
        print(f"[DEBUG] Slide {slide_num + 1}: Extracted {word_count} words via text extraction")
        
        # If insufficient text, use OCR on slide image
        if word_count < min_words:
            print(f"[DEBUG] Slide {slide_num + 1}: Using OCR (word count {word_count} < {min_words})")
            # Export slide as image and OCR
            try:
                # Get slide as image (this is a simplified approach)
                # In practice, you might need to use a library to convert slide to image
                text = extracted_text  # Fallback to extracted text for now
                print(f"[WARN] Slide {slide_num + 1}: OCR on PPTX slides requires additional setup, using extracted text")
            except Exception as e:
                print(f"[WARN] Slide {slide_num + 1}: OCR failed, using extracted text: {e}")
                text = extracted_text
        else:
            text = extracted_text
        
        text = clean_text(text)
        print(f"[DEBUG] Slide {slide_num + 1} final text (first 300 chars): {text[:300]}")
        
        # Auto-detect language
        lang = lang_code
        if not ocr_lang or ocr_lang == "eng":
            try:
                if len(text.strip()) >= 20:
                    detected = detect(text)
                    print(f"[DEBUG] Detected language: {detected}")
                    if detected in lang_map:
                        lang = detected
            except Exception as e:
                print(f"[WARN] Language detection failed: {e}")
                lang = "en"

        if lang not in lang_map:
            lang = "en"

        # Process content
        content_en, summary_en = process_text_content(text, lang, slide_num + 1)

        page_dict = {
            "page_number": slide_num + 1,
            "original_language": lang,
            "content_original": text,
            "content_en": content_en,
            "summary_en": summary_en
        }
        pptx_data.append(page_dict)

    return {"pages": pptx_data}


def process_text_content(text: str, lang: str, page_num: int):
    """Helper function to translate and summarize text"""
    try:
        chunks = chunk_text(text, nllb_tokenizer, max_tokens=500)
        try:
            content_en = translate_chunks(chunks, src_lang=lang)
        except Exception as e:
            print(f"[WARN] Translation failed on page {page_num}: {e}")
            content_en = text if lang == "en" else text

        content_en = remove_redundant_sentences(content_en)

        try:
            summary_en = summarize_english(content_en)
        except Exception as e:
            print(f"[WARN] Summarization failed on page {page_num}: {e}")
            summary_en = ""
    except Exception as e:
        print(f"[WARN] Processing (translate/summarize) failed on page {page_num}: {e}")
        content_en = text
        summary_en = ""
    
    return content_en, summary_en