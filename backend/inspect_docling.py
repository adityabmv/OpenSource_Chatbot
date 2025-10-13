import os
import sys
import time
import logging
import traceback
from pathlib import Path

# Prevent huggingface_hub from creating symlinks on Windows (requires admin).
# This forces the hub to copy files instead of creating symlinks.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("inspect_docling")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert a PDF with docling and save markdown output")
    parser.add_argument("pdf", nargs="?", help="Path to PDF file", default=None)
    parser.add_argument("--hf-cache", help="Path to HF cache directory (optional)", default=None)
    parser.add_argument("--out", help="Output markdown file", default="output.md")
    args = parser.parse_args()

    log.info("Starting inspect_docling.py")

    # Path to your PDF file (use absolute path). Allow override by CLI argument.
    if args.pdf:
        input_doc_path = Path(args.pdf)
    else:
        data_folder = Path(r"C:\Users\aniru\OneDrive\Documents\POP\Andra Pradesh")
        input_doc_path = data_folder / "POP- Flower crops.pdf"

    if not input_doc_path.exists():
        log.error("Input PDF not found: %s", input_doc_path)
        sys.exit(1)

    log.info("Input PDF: %s", input_doc_path)

    # If user provided a custom HF cache, set HF_HOME before importing docling
    if args.hf_cache:
        hf_cache_path = Path(args.hf_cache).expanduser().resolve()
        hf_cache_path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(hf_cache_path))
        log.info("Set HF_HOME to %s", hf_cache_path)

    # Delay imports from docling until after HF env vars are set
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except Exception as e:
        log.exception("Failed to import docling modules: %s", e)
        raise

    # --- 1. Set Tesseract OCR options for Telugu ---
    ocr_options = TesseractCliOcrOptions(lang=["tel"])

    # --- 2. Set PDF pipeline options ---
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        force_full_page_ocr=True,
        ocr_options=ocr_options,
    )

    # --- 3. Create the converter ---
    log.info("Creating DocumentConverter (this may initialize pipelines and trigger model downloads)")
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )

    # --- 4. Convert PDF and extract text ---
    try:
        log.info("Starting conversion (may download models). Time: %s", time.asctime())
        conv_res = converter.convert(input_doc_path)
        log.info("Conversion generator returned, obtaining .document")
        doc = conv_res.document
        log.info("Conversion finished successfully")

        # --- 5. Export to Markdown (optional) ---
        md = doc.export_to_markdown()
        # write to output file
        out_path = Path(args.out)
        out_path.write_text(md, encoding="utf-8")
        log.info("Wrote markdown output to %s", out_path)
        print(f"Wrote markdown output to {out_path}")

    except Exception as e:
        log.error("Conversion failed: %s", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
