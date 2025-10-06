import os
from convert_to_json import convert_to_json

# Input PDF path
pdf_path = r"C:\Users\aniru\OneDrive\Desktop\OS_chatbot\backend\POP- Flower crops.pdf"

# Run OCR + translation + summarization
result = convert_to_json(pdf_path, ocr_lang="tel")

# Prepare output directory
output_dir = r"C:\Users\aniru\OneDrive\Documents\POP\Test\output"
os.makedirs(output_dir, exist_ok=True)

# Create output filename
base_name = os.path.basename(pdf_path).replace(".pdf", ".json")
output_path = os.path.join(output_dir, base_name)

# Save result to JSON
with open(output_path, "w", encoding="utf-8") as f:
    import json
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"[✅] Saved output to: {output_path}")