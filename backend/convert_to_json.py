import os, fitz, json, re, unicodedata, torch
from PIL import Image
import pytesseract
from langdetect import detect, DetectorFactory
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

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
def convert_to_json(file_path: str, ocr_lang: str = "eng"):
    """
    Process a PDF with OCR + translation + summarization.
    Returns a dict with {"pages": [...]}
    """
    import traceback

    try:
        # Normalize: convert Tesseract code (e.g. "tel") to internal code (e.g. "te")
        lang_code = next((k for k, v in ocr_lang_map.items() if v == ocr_lang), "en")
        print(f"[DEBUG] Received ocr_lang: {ocr_lang}")
        print(f"[DEBUG] Normalized lang_code: {lang_code}")

        doc = fitz.open(file_path)
        pdf_data = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # OCR using Tesseract-compatible code
            ocr_code = ocr_lang_map.get(lang_code, "eng")
            text = pytesseract.image_to_string(img, lang=ocr_code)
            text = clean_text(text)
            print(f"[DEBUG] Page {page_num + 1} OCR text (first 300 chars): {text[:300]}")

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

            # Translate + summarize with robust fallbacks so API doesn't 500 on model issues
            try:
                chunks = chunk_text(text, nllb_tokenizer, max_tokens=500)
                try:
                    content_en = translate_chunks(chunks, src_lang=lang)
                except Exception as e:
                    print(f"[WARN] Translation failed on page {page_num + 1}: {e}")
                    # Fallback: use OCR text directly
                    content_en = text if lang == "en" else text

                content_en = remove_redundant_sentences(content_en)

                try:
                    summary_en = summarize_english(content_en)
                except Exception as e:
                    print(f"[WARN] Summarization failed on page {page_num + 1}: {e}")
                    summary_en = ""
            except Exception as e:
                print(f"[WARN] Processing (translate/summarize) failed on page {page_num + 1}: {e}")
                content_en = text
                summary_en = ""

            page_dict = {
                "page_number": page_num + 1,
                "original_language": lang,
                "content_original": text,
                "content_en": content_en,
                "summary_en": summary_en
            }
            pdf_data.append(page_dict)

        return {"pages": pdf_data}

    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"convert_to_json failed: {str(e)}")